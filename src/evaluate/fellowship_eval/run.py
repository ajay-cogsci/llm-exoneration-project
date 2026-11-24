"""Frozen plans and bounded, resumable requests. No implicit HTTP retries."""

import csv
import fcntl
import json
import math
import os
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from phd_eval.run import APIError, COLUMNS, collect as collect_shared, parse_reply, reply_text, safe_label
from phd_resumes.io import digest, read_json, read_jsonl, write_json, write_jsonl
from .design import ROOT, build_design, check_config, load_applicants, messages, pilot_subset, require


def implementation_hash():
    import fellowship_applicants.plan
    import phd_eval
    import phd_resumes.io
    paths = sorted(Path(__file__).parent.glob("*.py")) + sorted(Path(phd_eval.__file__).parent.glob("*.py"))
    paths += [Path(phd_resumes.io.__file__), Path(fellowship_applicants.plan.__file__)]
    return digest({str(p.relative_to(ROOT)): p.read_text() for p in paths})


def make_plan(config, out, root=ROOT, per_tier=None, **filters):
    out = Path(out)
    require(not out.exists(), "Choose a new directory; existing plans are never overwritten")
    applicants = load_applicants(config, root)
    if per_tier is not None:
        applicants = pilot_subset(applicants, per_tier, config["order_seed"])
    design = build_design(config, applicants, **filters)
    summary = {"opportunity": config["opportunity"]["id"], "config_hash": digest(config),
               "design_hash": digest(design), "implementation_hash": implementation_hash(),
               "dataset_checksums_hash": digest(read_json(Path(root) / config["dataset"] / "checksums.json")),
               "requests_per_model": len(design), "applicants": len(applicants),
               "applicants_by_tier": dict(Counter(a["cv_tier"] for a in applicants)),
               "tier_status": "Original provisional generation labels; descriptive only, not human-validated",
               **{k: sorted({r[k[:-1]] for r in design}) for k in ("conditions", "wordings", "tasks", "formats")},
               "repeats": max(r["repeat"] for r in design),
               "application_hashes": {a["applicant_id"]: a["application_hash"] for a in applicants},
               "evaluator_text_hashes": {a["applicant_id"]: a["evaluator_text_hash"] for a in applicants}}
    out.mkdir(parents=True)
    write_json(out / "config.json", config)
    write_jsonl(out / "design.jsonl", design)
    write_json(out / "plan.json", summary)
    return {k: v for k, v in summary.items() if not k.endswith("hashes")}


def load_plan(plan, root=ROOT):
    plan = Path(plan)
    config, summary, design = read_json(plan / "config.json"), read_json(plan / "plan.json"), read_jsonl(plan / "design.jsonl")
    check_config(config)
    require(digest(config) == summary["config_hash"] and digest(design) == summary["design_hash"], "Frozen plan changed")
    require(implementation_hash() == summary["implementation_hash"], "Implementation changed; use a new plan")
    require(digest(read_json(Path(root) / config["dataset"] / "checksums.json")) == summary["dataset_checksums_hash"], "Source checksum inventory changed")
    applicants = {a["applicant_id"]: a for a in load_applicants(config, root)}
    for pid, value in summary["application_hashes"].items():
        require(applicants[pid]["application_hash"] == value and applicants[pid]["evaluator_text_hash"] == summary["evaluator_text_hashes"][pid], "Frozen application changed")
    return config, design, applicants


class OpenRouter:
    """One transport attempt per recorded request; use only the current EVAL key."""
    base = "https://openrouter.ai/api/v1"

    def __init__(self):
        self.key = os.getenv("EVAL_API_KEY")
        if not self.key:
            raise APIError("Set EVAL_API_KEY in your terminal. Do not paste it into chat or a file.")
        require(os.getenv("EVAL_BASE_URL", self.base).rstrip("/") == self.base, "Expected the OpenRouter base URL")

    def create(self, body):
        request = urllib.request.Request(self.base + "/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                data = json.load(response)
                if not isinstance(data, dict):
                    raise ValueError("Expected an API response object")
                return data
        except urllib.error.HTTPError as exc:
            raise APIError(f"HTTP {exc.code}; no automatic retry") from None
        except (urllib.error.URLError, TimeoutError, ValueError, UnicodeDecodeError, OSError) as exc:
            raise APIError(f"Transport failed ({type(exc).__name__}); billing may be unresolved") from None


def append(path, row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def rows_if_exists(path):
    return read_jsonl(path) if path.exists() else []


def positive_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def execute(plan, client, label, api_model, *, budget_cap, request_cost_ceiling,
            root=ROOT, limit=None, concurrency=1, max_attempts=2, conditions=None):
    """Cap is cumulative across models in this plan. Ceiling must be a verified upper bound.

    Reserve the full worst-case request cost BEFORE dispatch, including requests
    in flight. Retain reservations for errors, missing costs and interrupted calls.
    A provider-side key limit is still required for a contractual hard spending cap.
    """
    require(positive_number(budget_cap) and positive_number(request_cost_ceiling), "Positive budget and request cost ceiling required")
    require(request_cost_ceiling <= budget_cap, "Request ceiling exceeds budget")
    require(type(concurrency) is int and concurrency > 0, "Concurrency must be positive")
    require(type(max_attempts) is int and 1 <= max_attempts <= 2, "Use one or at most two attempts per request")
    require(limit is None or (type(limit) is int and limit > 0), "Limit must be positive")
    require(isinstance(api_model, str) and api_model.strip(), "Model ID required")
    plan = Path(plan)
    config, design, applicants = load_plan(plan, root)
    if conditions is not None:
        require(conditions and set(conditions) <= {r["condition"] for r in design}, "Unknown run condition filter")
    response_dir = plan / "responses"
    response_dir.mkdir(exist_ok=True)
    # Only one runner process per plan. Threads share the reservation lock below.
    with (plan / ".run.lock").open("a") as process_lock:
        try:
            fcntl.flock(process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another runner holds this plan; do not launch parallel model processes") from None
        return _execute_locked(plan, client, label, api_model, config, design, applicants,
                               budget_cap, request_cost_ceiling, limit, concurrency, max_attempts, conditions)


def _execute_locked(plan, client, label, api_model, config, design, applicants,
                    budget_cap, ceiling, limit, concurrency, max_attempts, conditions):
    path = plan / "responses" / f"{safe_label(label)}.jsonl"
    saved = rows_if_exists(path)
    settings = {"label": label, "api_model": api_model, "request_parameters": {}, "max_attempts": max_attempts,
                "request_cost_ceiling": ceiling, "base_url": OpenRouter.base}
    settings_path = plan / f"model-{safe_label(label)}.json"
    if settings_path.exists():
        require(read_json(settings_path) == settings, "Label already has different settings; stop and review")
    else:
        write_json(settings_path, settings)
    for r in saved:
        require(r["api_model"] == api_model and r["request_parameters"] == {} and r["model_label"] == label, "Saved settings differ")
    budget_path = plan / "budget.json"
    if budget_path.exists():
        require(read_json(budget_path)["cap_usd"] == budget_cap, "Frozen budget differs; obtain approval before changing it")
    else:
        write_json(budget_path, {"cap_usd": budget_cap, "scope": "All models and attempts in this plan"})
    starts_path = plan / "attempt_starts.jsonl"
    starts = rows_if_exists(starts_path)
    completed = {r["attempt_id"]: r for p in (plan / "responses").glob("*.jsonl") for r in read_jsonl(p)}
    require(all(s["attempt_id"] in completed for s in starts), "Interrupted request has unresolved billing; reconcile it before resuming")
    require(all(completed[s["attempt_id"]].get("cost_status") == "reported" and
                completed[s["attempt_id"]]["accounted_cost_usd"] <= s["reserved_usd"] for s in starts),
            "Unresolved cost or exceeded ceiling from a prior attempt; reconcile before resuming")
    charges = {s["attempt_id"]: completed[s["attempt_id"]].get("accounted_cost_usd", s["reserved_usd"]) for s in starts}
    require(all(type(v) in (float, int) and math.isfinite(v) and v >= 0 for v in charges.values()), "Invalid cost ledger")
    done = {r["request_id"] for r in saved if r["valid"]}
    attempts = Counter(s["request_id"] for s in starts if s["model_label"] == label)
    todo = [r for r in design if r["request_id"] not in done and attempts[r["request_id"]] < max_attempts
            and (conditions is None or r["condition"] in conditions)]
    if limit is not None:
        todo = todo[:limit]
    lock, counts = Lock(), Counter()
    halt = []

    def one(row):
        chat = messages(config, applicants[row["applicant_id"]], row["condition"], row["wording"], row["task"], row["format"])
        require(digest(chat) == row["prompt_hash"], "Prompt differs from frozen plan")
        with lock:
            if halt or sum(charges.values()) + ceiling > budget_cap:
                if not halt:
                    halt.append("Budget cannot reserve another worst-case request")
                return
            aid = str(uuid.uuid4())
            start = {"attempt_id": aid, "request_id": row["request_id"], "model_label": label,
                     "reserved_usd": ceiling, "started_unix": time.time()}
            append(starts_path, start)
            charges[aid] = ceiling
        record = {**row, **start, "api_model": api_model, "request_parameters": {},
                  "concurrency": concurrency, "reply": None, "response": None, "error": None,
                  "accounted_cost_usd": ceiling, "cost_status": "reserved_unknown"}
        try:
            response = client.create({"model": api_model, "messages": chat})
            record.update(response=response, reply=reply_text(response))
            record.update(parse_reply(config, row["task"], row["format"], record["reply"]))
            cost = response.get("usage", {}).get("cost") if isinstance(response.get("usage"), dict) else None
            if type(cost) in (int, float) and math.isfinite(cost) and cost >= 0:
                record.update(accounted_cost_usd=cost, cost_status="reported")
        except APIError as exc:
            record.update(error=str(exc), **parse_reply(config, row["task"], row["format"], None))
        with lock:
            append(path, record)
            charges[aid] = record["accounted_cost_usd"]
            counts["sent_now"] += 1
            counts["error" if record["error"] else "valid" if record["valid"] else "unparseable"] += 1
            if record["cost_status"] != "reported" or charges[aid] > ceiling:
                halt.append("Unknown billing or request cost exceeded the verified ceiling; reconcile before continuing")

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(one, todo))
    # Missing costs are deliberately not reported as zero spend.
    return {"model_label": label, "planned": len(design), "already_valid": len(done), **counts,
            "remaining": len(design) - len(done) - counts["valid"],
            "exhausted_before_run": sum(n >= max_attempts and rid not in done for rid, n in attempts.items()),
            "total_reported_or_reserved_usd": sum(charges.values()), "budget_cap_usd": budget_cap,
            "stop_reasons": sorted(set(halt)), "responses": str(path)}


def collect(plan, root=ROOT):
    plan = Path(plan)
    _, design, _ = load_plan(plan, root)
    result = collect_shared(plan)
    first, counts = {}, {}
    for path in sorted((plan / "responses").glob("*.jsonl")):
        rows = read_jsonl(path)
        for row in rows:
            first.setdefault((row["model_label"], row["request_id"]), row)
        if not rows:
            continue
        label = rows[0]["model_label"]
        seen = Counter(r["request_id"] for r in rows)
        initial = [r for (model, _), r in first.items() if model == label]
        counts[label] = {"planned": len(design), "attempts": len(rows), "distinct_attempted": len(seen),
                         "missing": len(design) - len(seen), "first_attempt_valid": sum(r["valid"] for r in initial),
                         "valid_attempts": sum(r["valid"] for r in rows),
                         "unparseable_attempts": sum(not r["valid"] and not r["error"] for r in rows),
                         "error_attempts": sum(bool(r["error"]) for r in rows),
                         "reported_cost_usd": sum(r["accounted_cost_usd"] for r in rows if r["cost_status"] == "reported"),
                         "unresolved_cost_reserve_usd": sum(r["accounted_cost_usd"] for r in rows if r["cost_status"] != "reported"),
                         "unparseable_requests_retried_by_condition": dict(Counter(r["condition"] for r in initial
                             if not r["valid"] and not r["error"] and seen[r["request_id"]] > 1))}
    with (plan / "first_attempt_results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(first.values())
    write_json(plan / "attempt_summary.json", counts)
    return {**result, "first_attempt_results": str(plan / "first_attempt_results.csv"),
            "attempt_summary": str(plan / "attempt_summary.json")}
