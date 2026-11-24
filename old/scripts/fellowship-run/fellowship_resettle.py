"""Re-settle reconciled fellowship attempts at the provider-verified cost.

User-approved on 2026-11-23 ("either works", with the $100 cap). Reconciled
attempts were first charged their full worst-case reservation because no cost
was reported. OpenRouter's account usage shows what was actually billed. The
billed amount not covered by reported per-reply costs ("unexplained") is the
most those attempts can have cost. It is split equally across all reconciled
attempts, and each record keeps its earlier charge under reconciliation.history.

Run only while no runner is active on the plan (the runner lock is taken).
usage: python3 old/scripts/fellowship-run/fellowship_resettle.py --baseline-usage 100.203850047 [--plan runs/fellowship/main] [--dry-run]
"""
import argparse
import fcntl
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read_jsonl(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def provider_usage():
    req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                 headers={"Authorization": "Bearer " + os.environ["EVAL_API_KEY"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]["usage"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="runs/fellowship/main")
    ap.add_argument("--baseline-usage", type=float, required=True,
                    help="OpenRouter key usage before this plan's first request")
    ap.add_argument("--also", nargs="*", default=[],
                    help="Other plans billed under the same baseline (e.g. parallel copies). Their reported "
                         "costs and reconciled attempts are counted, but only --plan is rewritten.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    plan = ROOT / args.plan
    others = [ROOT / o for o in args.also]
    with (plan / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A runner holds this plan; stop it first")
        files = {p: read_jsonl(p) for p in sorted((plan / "responses").glob("*.jsonl"))}
        starts = read_jsonl(plan / "attempt_starts.jsonl")
        done = {r["attempt_id"] for rows in files.values() for r in rows}
        if any(s["attempt_id"] not in done for s in starts):
            raise SystemExit("Unrecorded attempts exist; reconcile them first")
        usage = provider_usage()
        def plan_rows(o):
            # A split main plan still holds pre-split copies of the split models' replies;
            # those models' current records live in their parallel copies, so skip them here.
            split = set()
            if (o / "PARALLEL_SPLIT.json").exists():
                split = {l.replace(" ", "-") for l in json.load(open(o / "PARALLEL_SPLIT.json"))["split"]}
            return [r for p in (o / "responses").glob("*.jsonl") if p.stem not in split for r in read_jsonl(p)]

        other_rows = [r for o in others for r in plan_rows(o)]
        reported = sum(r["accounted_cost_usd"] for rows in files.values() for r in rows if "reconciliation" not in r)
        reported += sum(r["accounted_cost_usd"] for r in other_rows if "reconciliation" not in r)
        recon = [(p, i) for p, rows in files.items() for i, r in enumerate(rows) if "reconciliation" in r]
        n_other_recon = sum("reconciliation" in r for r in other_rows)
        unexplained = max(0.0, usage - args.baseline_usage - reported)
        share = unexplained / (len(recon) + n_other_recon) if recon else 0.0
        held = sum(files[p][i]["accounted_cost_usd"] for p, i in recon)
        print(f"provider usage {usage:.6f}; billed since baseline {usage - args.baseline_usage:.6f}; "
              f"reported {reported:.6f}; unexplained {unexplained:.6f}; reconciled attempts {len(recon)} here + {n_other_recon} elsewhere; "
              f"held now {held:.4f}; new charge each {share:.6f}")
        if args.dry_run:
            return
        stamp = time.time()
        for p, i in recon:
            r = files[p][i]
            if share > r["reserved_usd"]:
                raise SystemExit("Share exceeds an attempt's reservation; investigate before re-settling")
            hist = r["reconciliation"].get("history", [])
            hist.append({"accounted_cost_usd": r["accounted_cost_usd"], "method": r["reconciliation"]["method"],
                         "replaced_unix": stamp})
            r["reconciliation"].update(
                method="re-settled to an equal share of provider-verified unexplained spend",
                provider_usage=usage, baseline_usage=args.baseline_usage, reported_total=reported,
                unexplained_total=unexplained, attempts_sharing=len(recon) + n_other_recon, history=hist,
                approved_resettle="user, 2026-11-23")
            r["accounted_cost_usd"] = share
        (plan / "reconcile_backups").mkdir(exist_ok=True)
        for p, rows in files.items():
            if any("reconciliation" in r for r in rows):
                shutil.copy2(p, plan / "reconcile_backups" / f"{p.name}.bak-resettle-{int(stamp)}")
                tmp = p.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    for r in rows:
                        f.write(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, p)
        print(f"re-settled {len(recon)} attempts; held amount {held:.4f} -> {share * len(recon):.6f}")


if __name__ == "__main__":
    main()
