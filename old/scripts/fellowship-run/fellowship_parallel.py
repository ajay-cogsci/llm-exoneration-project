"""Run fellowship models in parallel without touching the frozen harness.

User-approved on 2026-11-23 with a $100 total cap. The harness allows one
runner per plan, so each model gets its own copy of the frozen plan under
runs/fellowship/parallel/<model>/. A copy has byte-identical config.json,
design.jsonl, plan.json and model settings, so it passes the same hash
checks. Each copy also holds that model's existing replies and attempt
starts, plus a budget.json slice. The slices sum to the main plan's cap, so
the total stays exactly bounded. `merge` copies each model's replies and
starts back into runs/fellowship/main.

usage:
  python3 old/scripts/fellowship-run/fellowship_parallel.py split --slices '{"Qwen3-32B": 8.5, ...}'
  python3 old/scripts/fellowship-run/fellowship_parallel.py set-slice --label "Gemini 3.8 Flash" --cap 60
  python3 old/scripts/fellowship-run/fellowship_parallel.py merge
"""
import argparse
import fcntl
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from phd_eval.run import safe_label  # noqa: E402

MAIN = ROOT / "runs/fellowship/main"
PAR = ROOT / "runs/fellowship/parallel"
FROZEN = ("config.json", "design.jsonl", "plan.json")


def read_jsonl(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def write_jsonl(p, rows):
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    tmp.replace(p)


def lock(plan):
    handle = (plan / ".run.lock").open("a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f"A runner holds {plan}; stop it first")
    return handle


def charges(plan, label=None):
    starts = read_jsonl(plan / "attempt_starts.jsonl")
    recs = {r["attempt_id"]: r for p in (plan / "responses").glob("*.jsonl") for r in read_jsonl(p)}
    return sum(recs[s["attempt_id"]]["accounted_cost_usd"] if s["attempt_id"] in recs else s["reserved_usd"]
               for s in starts if label is None or s["model_label"] == label)


def split(slices):
    main_lock = lock(MAIN)
    cap = json.load(open(MAIN / "budget.json"))["cap_usd"]
    labels = {json.load(open(p))["label"] for p in MAIN.glob("model-*.json")}
    unsplit = sum(charges(MAIN, l) for l in labels - set(slices))
    if unsplit + sum(slices.values()) > cap + 1e-9:
        raise SystemExit(f"Slices {sum(slices.values()):.2f} + unsplit spend {unsplit:.2f} exceed cap {cap}")
    starts = read_jsonl(MAIN / "attempt_starts.jsonl")
    for label, slice_cap in slices.items():
        dst = PAR / safe_label(label)
        if dst.exists():
            raise SystemExit(f"{dst} exists; merge or remove it first")
        spent = charges(MAIN, label)
        if slice_cap <= spent:
            raise SystemExit(f"{label}: slice {slice_cap} is not above its current charges {spent:.2f}")
        (dst / "responses").mkdir(parents=True)
        for name in FROZEN + (f"model-{safe_label(label)}.json",):
            shutil.copy2(MAIN / name, dst / name)
        src = MAIN / "responses" / f"{safe_label(label)}.jsonl"
        if src.exists():
            shutil.copy2(src, dst / "responses" / src.name)
        write_jsonl(dst / "attempt_starts.jsonl", [s for s in starts if s["model_label"] == label])
        json.dump({"cap_usd": slice_cap, "scope": f"Slice of runs/fellowship/main (cap ${cap}) for {label}"},
                  open(dst / "budget.json", "w"), indent=2)
        print(f"split {label}: slice ${slice_cap}, current charges ${spent:.4f} -> {dst}")
    json.dump({"split": sorted(slices), "slices": slices, "note": "Do not run models in main until merged"},
              open(MAIN / "PARALLEL_SPLIT.json", "w"), indent=2)
    main_lock.close()


def set_slice(label, new_cap):
    dst = PAR / safe_label(label)
    held = lock(dst)
    meta = json.load(open(MAIN / "PARALLEL_SPLIT.json"))
    slices = meta["slices"]
    cap = json.load(open(MAIN / "budget.json"))["cap_usd"]
    labels = {json.load(open(p))["label"] for p in MAIN.glob("model-*.json")}
    unsplit = sum(charges(MAIN, l) for l in labels - set(slices))
    # Charges already in finished slices count at their actual value, not their slice.
    others = 0.0
    for other, c in slices.items():
        if other == label:
            continue
        o = PAR / safe_label(other)
        try:
            fcntl.flock((o / ".run.lock").open("a"), fcntl.LOCK_EX | fcntl.LOCK_NB)
            others += charges(o)  # idle: its actual charges are final unless restarted
        except BlockingIOError:
            others += c  # still running: count its full slice
    if unsplit + others + new_cap > cap + 1e-9:
        raise SystemExit(f"New slice would exceed the cap: {unsplit:.2f} + {others:.2f} + {new_cap} > {cap}")
    json.dump({"cap_usd": new_cap, "scope": f"Slice of runs/fellowship/main (cap ${cap}) for {label}"},
              open(dst / "budget.json", "w"), indent=2)
    slices[label] = new_cap
    json.dump(meta, open(MAIN / "PARALLEL_SPLIT.json", "w"), indent=2)
    print(f"{label}: slice set to ${new_cap}")
    held.close()


def merge():
    meta = json.load(open(MAIN / "PARALLEL_SPLIT.json"))
    main_lock = lock(MAIN)
    starts = read_jsonl(MAIN / "attempt_starts.jsonl")
    keep = [s for s in starts if s["model_label"] not in meta["split"]]
    for label in meta["split"]:
        dst = PAR / safe_label(label)
        lock(dst)
        cs = read_jsonl(dst / "attempt_starts.jsonl")
        recs = {r["attempt_id"] for r in read_jsonl(dst / "responses" / f"{safe_label(label)}.jsonl")}
        if any(s["attempt_id"] not in recs for s in cs):
            raise SystemExit(f"{label}: unrecorded attempts in its copy; reconcile first")
        for name in FROZEN:
            if (dst / name).read_bytes() != (MAIN / name).read_bytes():
                raise SystemExit(f"{label}: {name} differs from main")
        keep += cs
        shutil.copy2(dst / "responses" / f"{safe_label(label)}.jsonl",
                     MAIN / "responses" / f"{safe_label(label)}.jsonl")
        log = dst / "driver_log.txt"
        if log.exists():
            with open(MAIN / "driver_log.txt", "a") as out:
                out.write(f"--- merged log from parallel/{safe_label(label)} ---\n" + log.read_text())
    keep.sort(key=lambda s: s["started_unix"])
    if len({s["attempt_id"] for s in keep}) != len(keep):
        raise SystemExit("Duplicate attempt ids after merge")
    write_jsonl(MAIN / "attempt_starts.jsonl", keep)
    cap = json.load(open(MAIN / "budget.json"))["cap_usd"]
    total = charges(MAIN)
    print(f"merged {len(meta['split'])} models; main charges ${total:.4f} of cap ${cap}")
    if total > cap + 1e-9:
        raise SystemExit("Merged charges exceed the cap; investigate")
    (MAIN / "PARALLEL_SPLIT.json").rename(MAIN / "PARALLEL_SPLIT.merged.json")
    main_lock.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("--slices", required=True)
    c = sub.add_parser("set-slice")
    c.add_argument("--label", required=True)
    c.add_argument("--cap", type=float, required=True)
    sub.add_parser("merge")
    a = ap.parse_args()
    if a.cmd == "split":
        split(json.loads(a.slices))
    elif a.cmd == "set-slice":
        set_slice(a.label, a.cap)
    else:
        merge()


if __name__ == "__main__":
    main()
