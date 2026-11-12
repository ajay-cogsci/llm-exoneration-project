"""Planning, execution against a chat-completions endpoint, parsing and export.

The API key is read from the environment and is never written to disk. Runs
are resumable: a request with a saved, parseable response is not sent again.
"""

import csv
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

from phd_resumes.io import digest, read_json, read_jsonl, write_json, write_jsonl

from .design import build_design, check_config, fill, load_applicants, messages, pilot_subset, require


class APIError(RuntimeError):
    pass


def make_plan(config, out, root=".", per_tier=None, **filters):
    out = Path(out)
    require(not out.exists(), "Choose a new plan directory; existing plans are never overwritten")
    check_config(config)
    applicants = load_applicants(config, root)
    if per_tier is not None:
        applicants = pilot_subset(applicants, per_tier, config["order_seed"])
    design = build_design(config, applicants, **filters)
    out.mkdir(parents=True)
    write_json(out / "config.json", config)
    write_jsonl(out / "design.jsonl", design)
    summary = {"config_hash": digest(config), "design_hash": digest(design), "requests_per_model": len(design), "applicants": len(applicants), "applicants_by_tier": {t: sum(a["cv_tier"] == t for a in applicants) for t in ("weak", "borderline", "strong")}, "conditions": sorted({r["condition"] for r in design}), "wordings": sorted({r["wording"] for r in design}), "tasks": sorted({r["task"] for r in design}), "formats": sorted({r["format"] for r in design}), "repeats": max(r["repeat"] for r in design), "application_hashes": {a["applicant_id"]: a["application_hash"] for a in applicants}}
    write_json(out / "plan.json", summary)
    return {k: v for k, v in summary.items() if k != "application_hashes"}


def load_plan(plan, root="."):
    plan = Path(plan)
    config, summary, design = read_json(plan / "config.json"), read_json(plan / "plan.json"), read_jsonl(plan / "design.jsonl")
    require(digest(config) == summary["config_hash"] and digest(design) == summary["design_hash"], "Plan files changed; make a new plan")
    applicants = {a["applicant_id"]: a for a in load_applicants(config, root)}
    for pid, saved in summary["application_hashes"].items():
        require(applicants[pid]["application_hash"] == saved, f"Application packet changed since planning: {pid}")
    return config, design, applicants


def extract_json(text):
    """Return the single JSON object in a reply, tolerating a code fence."""
    if not isinstance(text, str):
        return None
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    for candidate in (stripped, stripped[stripped.find("{"): stripped.rfind("}") + 1]):
        try:
            value = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def parse_reply(config, task, style, text):
    """Validate a reply against the task's stated JSON format."""
    spec, form = config["tasks"][task], config["formats"][style]
    values = config["opportunity"]["placeholders"]
    result = {"valid": False, "score": None, "decision": None, "rationale": None, "problem": None}
    data = extract_json(text)
    if data is None:
        result["problem"] = "no JSON object"
        return result
    expected = {spec["score_key"]} | ({spec["decision_key"]} if spec["decision_key"] else set()) | ({form["rationale_key"]} if form["rationale_key"] else set())
    if set(data) != expected:
        result["problem"] = f"keys {sorted(data)} differ from {sorted(expected)}"
        return result
    score = data[spec["score_key"]]
    if type(score) is float and score.is_integer():
        score = int(score)
    if type(score) is not int or not 0 <= score <= 100:
        result["problem"] = "score is not an integer from 0 to 100"
        return result
    result["score"] = score
    if spec["decision_key"]:
        words = {fill(spec["positive"], values): 1, fill(spec["negative"], values): 0}
        answer = data[spec["decision_key"]]
        if not isinstance(answer, str) or answer.strip().lower() not in words:
            result["problem"] = "decision is not one of the two allowed words"
            return result
        result["decision"] = words[answer.strip().lower()]
    if form["rationale_key"]:
        if not isinstance(data[form["rationale_key"]], str) or not data[form["rationale_key"]].strip():
            result["problem"] = "missing rationale text"
            return result
        result["rationale"] = data[form["rationale_key"]].strip()
    result["valid"] = True
    return result


class ChatCompletions:
    """Any endpoint that implements POST {base}/chat/completions."""

    def __init__(self, base_url=None):
        self.key = os.getenv("EVAL_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.key:
            raise APIError("Set EVAL_API_KEY in the environment; do not put it in project files")
        self.base = (base_url or os.getenv("EVAL_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        parsed = urlsplit(self.base)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise APIError("The base URL must be HTTPS without credentials, query or fragment")

    def create(self, body):
        request = urllib.request.Request(self.base + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key}, method="POST")
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                detail = exc.read(500).decode("utf-8", "replace")
                raise APIError(f"HTTP {exc.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError) as exc:
                raise APIError(f"Connection failed or timed out: {exc}") from None
            except (ValueError, UnicodeDecodeError):
                raise APIError("Endpoint returned invalid JSON") from None
        raise APIError("Retries exhausted")


def reply_text(response):
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(content, list):  # some providers return content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content if isinstance(content, str) else None


def safe_label(label):
    require(isinstance(label, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", label), "Model label may contain letters, digits, spaces, dots, dashes and underscores")
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label)


def execute(plan, client, label, api_model, root=".", parameters=None, limit=None, concurrency=1):
    """Send every outstanding request for one model and append the replies."""
    plan = Path(plan)
    config, design, applicants = load_plan(plan, root)
    parameters = {**config["request_parameters"], **(parameters or {})}
    require(not {"model", "messages"} & set(parameters), "model and messages are set by the runner")
    path = plan / "responses" / f"{safe_label(label)}.jsonl"
    path.parent.mkdir(exist_ok=True)
    saved = read_jsonl(path) if path.exists() else []
    for row in saved:
        require(row["api_model"] == api_model and row["request_parameters"] == parameters, "This label already has replies from a different model or settings; use a new label")
    done = {row["request_id"] for row in saved if row["valid"]}
    todo = [row for row in design if row["request_id"] not in done]
    if limit is not None:
        todo = todo[:limit]
    lock, counts = Lock(), defaultdict(int)

    def one(row):
        chat = messages(config, applicants[row["applicant_id"]], row["condition"], row["wording"], row["task"], row["format"])
        require(digest(chat) == row["prompt_hash"], "Prompt differs from the planned prompt")
        record = {**row, "model_label": label, "api_model": api_model, "request_parameters": parameters, "reply": None, "response": None, "error": None}
        try:
            response = client.create({"model": api_model, "messages": chat, **parameters})
            record.update(response=response, reply=reply_text(response))
            record.update(parse_reply(config, row["task"], row["format"], record["reply"]))
        except APIError as exc:
            record.update(error=str(exc), **parse_reply(config, row["task"], row["format"], None))
        with lock:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            counts["error" if record["error"] else "valid" if record["valid"] else "unparseable"] += 1
        return record

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(one, todo))
    return {"model_label": label, "api_model": api_model, "planned": len(design), "already_valid": len(done), "sent_now": len(todo), **counts, "remaining": len(design) - len(done) - counts["valid"], "responses": str(path)}


COLUMNS = ["model_label", "api_model", "applicant_id", "cv_tier", "pathway", "research_area", "condition", "condition_role", "wording", "task", "format", "repeat", "valid", "score", "decision", "problem", "error", "rationale", "request_id"]


def collect(plan):
    """One tidy CSV row per planned request and model, plus a descriptive summary.

    The summary is a first look, not the analysis. It reports clean-baseline
    scores by CV tier as a prompt check, and each condition's mean paired
    difference from the same applicant's clean record.
    """
    plan = Path(plan)
    rows = []
    for path in sorted((plan / "responses").glob("*.jsonl")):
        latest = {}
        for row in read_jsonl(path):
            if row["request_id"] not in latest or row["valid"] or not latest[row["request_id"]]["valid"]:
                latest[row["request_id"]] = row
        rows += list(latest.values())
    require(rows, "No responses have been saved for this plan")
    with (plan / "results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    summary = {}
    for label in sorted({r["model_label"] for r in rows}):
        mine = [r for r in rows if r["model_label"] == label]
        valid = [r for r in mine if r["valid"]]
        model = {"replies": len(mine), "valid": len(valid), "invalid_or_error": len(mine) - len(valid), "tasks": {}}
        for task in sorted({r["task"] for r in valid}):
            scores = defaultdict(list)
            for r in (r for r in valid if r["task"] == task):
                scores[(r["applicant_id"], r["wording"], r["format"], r["condition"])].append(r["score"])
            cell = {key: statistics.mean(value) for key, value in scores.items()}
            by_tier = defaultdict(list)
            tier = {r["applicant_id"]: r["cv_tier"] for r in valid}
            for (pid, _, _, condition), value in cell.items():
                if condition == "clean":
                    by_tier[tier[pid]].append(value)
            conditions = {}
            for condition in sorted({key[3] for key in cell}):
                values = [value for key, value in cell.items() if key[3] == condition]
                paired = [value - cell[key[:3] + ("clean",)] for key, value in cell.items() if key[3] == condition and key[:3] + ("clean",) in cell]
                conditions[condition] = {"cells": len(values), "mean_score": round(statistics.mean(values), 3), "mean_difference_from_clean": round(statistics.mean(paired), 3) if paired else None, "paired_cells": len(paired)}
            model["tasks"][task] = {"clean_mean_score_by_cv_tier": {t: round(statistics.mean(v), 3) for t, v in sorted(by_tier.items())}, "conditions": conditions}
        summary[label] = model
    write_json(plan / "summary.json", summary)
    return {"rows": len(rows), "results": str(plan / "results.csv"), "summary": str(plan / "summary.json")}
