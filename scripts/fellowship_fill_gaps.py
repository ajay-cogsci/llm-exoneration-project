"""Give exhausted fellowship requests one extra (third) attempt.

User-approved on 2026-11-23 for requests whose two allowed attempts were used up
by transport failures (mostly while the laptop slept with no network, so most of
those attempts never reached OpenRouter). Everything else matches the runner:
- the prompt is rebuilt with fellowship_eval.design.messages and must match the
  frozen prompt hash;
- no sampling parameters; same label, model ID and per-attempt cost ceiling;
- the ceiling is reserved in attempt_starts.jsonl before sending, and the
  cumulative cap in budget.json is enforced;
- every attempt is appended to the model's responses file, flagged with
  "extra_attempt".
It takes the plan's runner lock, so it cannot run alongside the driver.

usage: python3 scripts/fellowship_fill_gaps.py --label "Gemma 4 31B IT" [--plan runs/fellowship/main] [--dry-run]
"""
import argparse
import fcntl
import json
import math
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from fellowship_eval.design import messages  # noqa: E402
from fellowship_eval.run import append, load_plan  # noqa: E402
from phd_eval.run import APIError, parse_reply, reply_text, safe_label  # noqa: E402
from phd_resumes.io import digest  # noqa: E402
from fellowship_run_driver import GuardedOpenRouter, read_jsonl  # noqa: E402

NOTE = ("third attempt approved by the user on 2026-11-23; the request's two allowed "
        "attempts were exhausted by transport failures")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="runs/fellowship/main")
    ap.add_argument("--label", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    plan = ROOT / args.plan
    config, design, applicants = load_plan(plan)
    settings = json.load(open(plan / f"model-{safe_label(args.label)}.json"))
    cap = json.load(open(plan / "budget.json"))["cap_usd"]
    ceiling = settings["request_cost_ceiling"]
    path = plan / "responses" / f"{safe_label(args.label)}.jsonl"
    with (plan / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another runner holds this plan; wait for it to finish")
        rows = read_jsonl(path)
        starts = read_jsonl(plan / "attempt_starts.jsonl")
        completed = {r["attempt_id"] for p in (plan / "responses").glob("*.jsonl") for r in read_jsonl(p)}
        unresolved = any(s["attempt_id"] not in completed for s in starts)
        done = {r["request_id"] for r in rows if r["valid"]}
        attempts = Counter(s["request_id"] for s in starts if s["model_label"] == args.label)
        errored = {r["request_id"] for r in rows if r["error"]}
        todo = [r for r in design if r["request_id"] not in done and attempts[r["request_id"]] >= settings["max_attempts"]
                and r["request_id"] in errored and attempts[r["request_id"]] < settings["max_attempts"] + 1]
        print(f"{args.label}: {len(todo)} exhausted requests to retry once")
        if args.dry_run:
            return
        if unresolved:
            raise SystemExit("Unresolved attempts exist; run the driver's reconcile first")
        charges = {r["attempt_id"]: r["accounted_cost_usd"] for p in (plan / "responses").glob("*.jsonl") for r in read_jsonl(p)}
        client = GuardedOpenRouter()
        n_valid = 0
        for row in todo:
            if sum(charges.values()) + ceiling > cap:
                print("STOP: budget cannot reserve another worst-case request")
                break
            chat = messages(config, applicants[row["applicant_id"]], row["condition"], row["wording"], row["task"], row["format"])
            if digest(chat) != row["prompt_hash"]:
                raise SystemExit("Prompt differs from frozen plan")
            aid = str(uuid.uuid4())
            start = {"attempt_id": aid, "request_id": row["request_id"], "model_label": args.label,
                     "reserved_usd": ceiling, "started_unix": time.time()}
            append(plan / "attempt_starts.jsonl", start)
            charges[aid] = ceiling
            record = {**row, **start, "api_model": settings["api_model"], "request_parameters": {},
                      "concurrency": 1, "reply": None, "response": None, "error": None,
                      "accounted_cost_usd": ceiling, "cost_status": "reserved_unknown", "extra_attempt": NOTE}
            try:
                response = client.create({"model": settings["api_model"], "messages": chat})
                record.update(response=response, reply=reply_text(response))
                record.update(parse_reply(config, row["task"], row["format"], record["reply"]))
                cost = (response.get("usage") or {}).get("cost")
                if type(cost) in (int, float) and math.isfinite(cost) and cost >= 0:
                    record.update(accounted_cost_usd=cost, cost_status="reported")
            except APIError as exc:
                record.update(error=str(exc), **parse_reply(config, row["task"], row["format"], None))
            append(path, record)
            charges[aid] = record["accounted_cost_usd"]
            n_valid += bool(record["valid"])
            print(f"  {row['request_id']} valid={record['valid']} cost={record['accounted_cost_usd']} {record['cost_status']} {record['error'] or ''}")
            if record["cost_status"] != "reported":
                print("STOP: unknown billing; reconcile before continuing")
                break
        print(f"{args.label}: {n_valid} of {len(todo)} filled")


if __name__ == "__main__":
    main()
