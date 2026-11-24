"""Unattended driver for the approved fellowship run (runs/fellowship/main).

Approved by the user on 2026-11-19: five-model panel, $80 cumulative cap, and the
following two procedures, neither of which edits the frozen, hashed code in
fellowship_eval/ or phd_eval/:

1. Transport guard. fellowship_eval.run.OpenRouter catches URLError/OSError/etc. but
   not http.client.HTTPException (e.g. IncompleteRead when a chunked reply is cut
   off), so one dropped connection crashed the whole process. GuardedOpenRouter
   converts HTTPException into the adapter's own APIError, so the runner records a
   normal transport-error attempt (cost unknown) and stops dispatch cleanly.

2. Conservative reconciliation. The runner refuses to resume while any attempt has
   unknown billing. reconcile() charges each such attempt its full reserved
   worst-case ceiling, sets cost_status "reported", and adds a "reconciliation"
   field saying the cost was NOT reported by the provider. An existing record is
   updated in place (one record per attempt is kept); an attempt that has a start
   but no record (process crash) gets one appended. The file is backed up first.
   Interrupted requests still get the plan's second attempt; nothing else changes.

Per model (cheapest first): smoke test (20 requests, concurrency 1) if not yet
done -> clean-record calibration (--conditions clean, concurrency 4) with an
automatic distinguishability gate -> full design (concurrency 4). The driver stops
everything on a budget stop, a failed gate, or more than MAX_RECONCILE reconciliations.

The API key is read only from EVAL_API_KEY by the adapter; it is never handled here.
usage: python3 scripts/fellowship_run_driver.py [--plan runs/fellowship/main]
"""
import argparse
import http.client
import json
import os
import shutil
import statistics
import sys
import threading
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fellowship_eval.run import OpenRouter, execute, load_plan  # noqa: E402
from phd_eval.run import APIError, parse_reply, safe_label  # noqa: E402

CAP_USD = 90.0  # raised from 80 by the user on 2026-11-23 (see budget.json)
MAX_RECONCILE = 40  # 40 x worst-case ceilings is at most about $18 of cap headroom
MODELS = [  # (label, OpenRouter id, verified worst-case cost per attempt in USD)
    ("Gemma 4 31B IT", "google/gemma-4-31b-it", 0.243),
    ("Qwen3-32B", "qwen/qwen3-32b", 0.069),
    ("Llama 4 Maverick", "meta-llama/llama-4-maverick", 0.036),
    ("GPT-5.4 mini", "openai/gpt-5.4-mini", 1.166),
    ("Gemini 3.8 Flash", "google/gemini-3.8-flash", 0.455),
]


REQUEST_DEADLINE_S = 600  # overall wall-clock limit per attempt


class GuardedOpenRouter(OpenRouter):
    """Adds two transport guards around the unchanged adapter.

    - http.client.HTTPException (e.g. IncompleteRead) becomes the adapter's APIError.
    - An overall deadline: OpenRouter sends keep-alive bytes while a provider works,
      so the adapter's 300 s socket timeout never fires on a stuck provider (one Qwen
      request hung for over 40 minutes on 2026-11-19). After REQUEST_DEADLINE_S the
      attempt is recorded as a transport error with unknown billing, and is then
      reconciled at its full reservation. The abandoned thread is left to finish or
      fail on its own; its result is discarded.
    """

    def _guarded(self, body):
        try:
            return super().create(body)
        except http.client.HTTPException as exc:
            raise APIError(f"Transport failed ({type(exc).__name__}); billing may be unresolved") from None

    def create(self, body):
        box = {}

        def work():
            try:
                box["ok"] = self._guarded(body)
            except BaseException as exc:  # re-raised in the caller's thread
                box["err"] = exc

        t = threading.Thread(target=work, daemon=True)
        t.start()
        t.join(REQUEST_DEADLINE_S)
        if t.is_alive():
            raise APIError(f"Transport failed (no reply within {REQUEST_DEADLINE_S} s); billing may be unresolved")
        if "err" in box:
            raise box["err"]
        return box["ok"]


def log(msg, path):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(path, "a") as f:
        f.write(line + "\n")


def read_jsonl(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def provider_usage():
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                     headers={"Authorization": "Bearer " + os.environ["EVAL_API_KEY"]})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["data"]["usage"]
    except Exception as exc:  # informational only
        return f"unavailable ({type(exc).__name__})"


def wait_for_network(logf):
    """Block until OpenRouter answers, so a sleeping/offline laptop does not burn attempts.

    Added 2026-11-23: while the Mac slept, each hourly dark wake sent four requests
    that failed with URLError, and each was reconciled at the full reservation.
    """
    warned = False
    while True:
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                         headers={"Authorization": "Bearer " + os.environ["EVAL_API_KEY"]})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    if warned:
                        log("NETWORK back; resuming", logf)
                    return
        except Exception:
            pass
        if not warned:
            log("WAITING for network (OpenRouter unreachable); no requests sent until it answers", logf)
            warned = True
        time.sleep(60)


def reconcile(plan, config, design, logf):
    """Charge every attempt with unknown billing its full reservation. Returns count."""
    starts = read_jsonl(plan / "attempt_starts.jsonl")
    rows_by_id = {r["request_id"]: r for r in design}
    fixed = 0
    files = {p: read_jsonl(p) for p in (plan / "responses").glob("*.jsonl")}
    by_attempt = {r["attempt_id"]: (p, i) for p, rows in files.items() for i, r in enumerate(rows)}
    changed, appended = set(), defaultdict(list)
    for s in starts:
        note = {"method": "charged full reserved worst-case ceiling; cost NOT reported by provider",
                "reserved_usd": s["reserved_usd"], "reconciled_unix": time.time(),
                "approved": "user, 2026-11-19"}
        if s["attempt_id"] in by_attempt:
            p, i = by_attempt[s["attempt_id"]]
            r = files[p][i]
            if r.get("cost_status") == "reported":
                continue
            r.update(accounted_cost_usd=s["reserved_usd"], cost_status="reported",
                     reconciliation={**note, "original_cost_status": r.get("cost_status")})
            changed.add(p)
        else:
            row = rows_by_id[s["request_id"]]
            label = s["model_label"]
            p = plan / "responses" / f"{safe_label(label)}.jsonl"
            settings = json.load(open(plan / f"model-{safe_label(label)}.json"))
            rec = {**row, **s, "api_model": settings["api_model"], "request_parameters": {},
                   "concurrency": None, "reply": None, "response": None,
                   "error": "Process interrupted before a reply was recorded; billing unresolved",
                   "accounted_cost_usd": s["reserved_usd"], "cost_status": "reported",
                   "reconciliation": {**note, "original_cost_status": "no_record"}}
            rec.update(parse_reply(config, row["task"], row["format"], None))
            appended[p].append(rec)
        fixed += 1
        log(f"RECONCILED {s['model_label']} {s['request_id']} attempt {s['attempt_id']} charged ${s['reserved_usd']}", logf)
    for p in changed | set(appended):
        (plan / "reconcile_backups").mkdir(exist_ok=True)
        backup = plan / "reconcile_backups" / f"{p.name}.bak-{int(time.time())}"
        if p.exists():
            shutil.copy2(p, backup)
        rows = files.get(p, []) + appended.get(p, [])
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    return fixed


def calibration(plan, label):
    """Clean-cell summary and the distinguishability gate."""
    rows = [r for r in read_jsonl(plan / "responses" / f"{safe_label(label)}.jsonl")
            if r["condition"] == "clean" and r["valid"]]
    out, ok = {"valid_clean_cells": len({r["request_id"] for r in rows})}, True
    for task in ("quality", "advance", "decide"):
        rs = [r for r in rows if r["task"] == task]
        scores = [r["score"] for r in rs]
        per_app = defaultdict(list)
        for r in rs:
            per_app[(r["applicant_id"], r["cv_tier"])].append(r["score"])
        app_means = [statistics.mean(v) for v in per_app.values()]
        tiers = {t: round(statistics.mean([statistics.mean(v) for (a, tt), v in per_app.items() if tt == t]), 1)
                 for t in ("weak", "borderline", "strong") if any(tt == t for (_, tt) in per_app)}
        sd = statistics.pstdev(app_means) if len(app_means) > 1 else 0.0
        info = {"n": len(scores), "min": min(scores, default=None), "max": max(scores, default=None),
                "mean": round(statistics.mean(scores), 1) if scores else None,
                "sd_of_applicant_means": round(sd, 2), "distinct_values": len(set(scores)),
                "floor_rate_le5": round(sum(s <= 5 for s in scores) / max(len(scores), 1), 3),
                "ceiling_rate_ge95": round(sum(s >= 95 for s in scores) / max(len(scores), 1), 3),
                "mean_by_original_tier": tiers}
        if sd < 2.0 or len(set(scores)) < 5:
            ok = False
        out[task] = info
    out["gate_passed"] = ok and out["valid_clean_cells"] >= 1100
    return out


def stage(plan, label, mid, ceiling, logf, n_reconciled, **kw):
    """Run one stage to completion, reconciling and resuming as approved."""
    config, design, _ = load_plan(plan)
    for _ in range(MAX_RECONCILE + 5):
        n_reconciled += reconcile(plan, config, design, logf)
        if n_reconciled > MAX_RECONCILE:
            raise SystemExit(f"STOP: more than {MAX_RECONCILE} reconciliations; review transport problems")
        wait_for_network(logf)
        try:
            res = execute(plan, GuardedOpenRouter(), label, mid, budget_cap=CAP_USD,
                          request_cost_ceiling=ceiling, **kw)
        except Exception as exc:  # unexpected crash: record, reconcile next loop, resume
            log(f"CRASH {label} {type(exc).__name__}: {exc}", logf)
            time.sleep(30)
            continue
        brief = {k: res.get(k) for k in ("sent_now", "valid", "unparseable", "error", "remaining",
                                          "total_reported_or_reserved_usd", "stop_reasons")}
        log(f"STAGE {label} {kw} -> {brief}", logf)
        reasons = " ".join(res["stop_reasons"])
        if "Budget" in reasons:
            raise SystemExit(f"STOP: budget cannot reserve another worst-case request (${res['total_reported_or_reserved_usd']:.2f})")
        over = [r for p in (plan / "responses").glob("*.jsonl") for r in read_jsonl(p)
                if r.get("cost_status") == "reported" and r["accounted_cost_usd"] > r["reserved_usd"]]
        if over:
            raise SystemExit(f"STOP: {len(over)} attempt(s) cost more than the verified ceiling; ceiling is wrong")
        if "Unknown billing" in reasons:
            time.sleep(30)
            continue
        if res.get("sent_now", 0) == 0 or not res["stop_reasons"]:
            return res, n_reconciled
    raise SystemExit("STOP: stage did not converge")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="runs/fellowship/main")
    ap.add_argument("--smoke-only", action="store_true", help="Run only the 20-request smoke tests, for manual inspection")
    args = ap.parse_args()
    plan = (ROOT / args.plan) if not Path(args.plan).is_absolute() else Path(args.plan)
    logf = plan / "driver_log.txt"
    n_rec = 0
    log(f"DRIVER START cap ${CAP_USD} provider_usage={provider_usage()}", logf)
    for label, mid, ceiling in MODELS:
        before = provider_usage()
        log(f"MODEL START {label} ({mid}) provider_usage={before}", logf)
        if len(read_jsonl(plan / "responses" / f"{safe_label(label)}.jsonl")) < 20:
            _, n_rec = stage(plan, label, mid, ceiling, logf, n_rec, limit=20, concurrency=1, max_attempts=2)
        if args.smoke_only:
            continue
        _, n_rec = stage(plan, label, mid, ceiling, logf, n_rec, conditions=["clean"], concurrency=4, max_attempts=2)
        cal = calibration(plan, label)
        (plan / f"calibration-{safe_label(label)}.json").write_text(json.dumps(cal, indent=2))
        log(f"CALIBRATION {label} {json.dumps(cal)}", logf)
        if not cal["gate_passed"]:
            raise SystemExit(f"PAUSE: {label} clean scores fail the distinguishability gate; see calibration file")
        res, n_rec = stage(plan, label, mid, ceiling, logf, n_rec, concurrency=4, max_attempts=2)
        rows = read_jsonl(plan / "responses" / f"{safe_label(label)}.jsonl")
        cost = sum(r["accounted_cost_usd"] for r in rows)
        log(f"MODEL DONE {label} remaining={res['remaining']} model_cost=${cost:.4f} "
            f"plan_total=${res['total_reported_or_reserved_usd']:.4f} provider_usage={provider_usage()} reconciled_so_far={n_rec}", logf)
    log("ALL MODELS DONE", logf)


if __name__ == "__main__":
    main()
