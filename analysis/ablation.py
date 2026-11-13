"""No-infer ablation: does deleting "Do not assume or infer details that are not stated."
from the system message change model behaviour?

Arm A = runs/ablation/plan_A (original config), arm B = runs/ablation/plan_B (sentence removed).
Both plans hold the same 2,400 requests per model (4 conditions x 2 wordings x 3 tasks x
answer_only x 100 applicants); only the system message differs.

usage: python analysis/ablation.py [--root runs/ablation] [--main runs/main/results.csv]
Outputs go to <root>/analysis/.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

CONDITIONS = ["clean", "cleared", "pending", "responsible"]
TASKS = ["quality", "advance", "decide"]
MODELS = ["Gemma 4 31B IT", "Qwen3-32B", "GPT-5.4 mini"]


def applicant_means(df):
    """Mean score per model x task x applicant x condition (averaging the two wordings)."""
    v = df[df["valid"]]
    return (v.groupby(["model_label", "task", "applicant_id", "condition"])["score"].mean()
             .unstack("condition"))


def paired_ci(d):
    """Mean of applicant-level differences with a t interval (clustered by applicant)."""
    d = pd.Series(d).dropna()
    n = len(d)
    if n < 2:
        return dict(estimate=np.nan, se=np.nan, ci_low=np.nan, ci_high=np.nan, p=np.nan, n_applicants=n)
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    p = 2 * stats.t.sf(abs(m / se), n - 1) if se > 0 else (0.0 if m != 0 else 1.0)
    return dict(estimate=m, se=se, ci_low=m - t * se, ci_high=m + t * se, p=p, n_applicants=n)


def load(path, arm):
    df = pd.read_csv(path)
    df["valid"] = df["valid"].astype(str).str.lower().eq("true")
    df["arm"] = arm
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="runs/ablation")
    ap.add_argument("--main", default="runs/main/results.csv")
    args = ap.parse_args()
    root = Path(args.root)
    out = root / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    A = load(root / "plan_A" / "results.csv", "A")
    B = load(root / "plan_B" / "results.csv", "B")
    M = load(args.main, "main")
    M = M[(M["format"] == "answer_only") & M["condition"].isin(CONDITIONS) & M["model_label"].isin(MODELS)]
    models = [m for m in MODELS if m in set(A["model_label"]) | set(B["model_label"])]

    means = {k: applicant_means(d) for k, d in {"A": A, "B": B, "main": M}.items()}

    rows = []  # tidy estimates
    cell = []  # mean score by condition
    for model in models:
        for task in TASKS:
            for arm in ["A", "B", "main"]:
                try:
                    w = means[arm].loc[(model, task)]
                except KeyError:
                    continue
                for c in CONDITIONS:
                    cell.append(dict(model=model, task=task, arm=arm, condition=c,
                                     mean=w[c].mean(), n_applicants=w[c].notna().sum()))
                for c in CONDITIONS[1:]:
                    rows.append(dict(model=model, task=task, quantity="gap_vs_clean", arm=arm,
                                     condition=c, **paired_ci(w[c] - w["clean"])))
            # effect of removing the sentence: (B gap) - (A gap), paired by applicant
            try:
                wa, wb = means["A"].loc[(model, task)], means["B"].loc[(model, task)]
            except KeyError:
                continue
            for c in CONDITIONS[1:]:
                d = (wb[c] - wb["clean"]) - (wa[c] - wa["clean"])
                rows.append(dict(model=model, task=task, quantity="removal_effect", arm="B-A",
                                 condition=c, **paired_ci(d)))
            # baseline level shift (clean B - clean A) for context
            rows.append(dict(model=model, task=task, quantity="clean_level_shift", arm="B-A",
                             condition="clean", **paired_ci(wb["clean"] - wa["clean"])))
            # noise check: arm A vs the same cells in the main run
            try:
                wm = means["main"].loc[(model, task)]
                for c in CONDITIONS[1:]:
                    d = (wa[c] - wa["clean"]) - (wm[c] - wm["clean"])
                    rows.append(dict(model=model, task=task, quantity="rerun_difference", arm="A-main",
                                     condition=c, **paired_ci(d)))
            except KeyError:
                pass

    est = pd.DataFrame(rows)
    cells = pd.DataFrame(cell)
    est.to_csv(out / "estimates.csv", index=False)
    cells.to_csv(out / "cell_means.csv", index=False)

    # noise level per model: typical (median and mean) absolute A-vs-main gap difference
    rr = est[est["quantity"] == "rerun_difference"].copy()
    rr["abs"] = rr["estimate"].abs()
    noise = (rr.groupby("model")["abs"].agg(noise_median="median", noise_mean="mean", noise_max="max")
               .reset_index())
    noise_cleared = (rr[rr["condition"] == "cleared"].groupby("model")["abs"]
                     .agg(noise_cleared_max="max").reset_index())
    noise = noise.merge(noise_cleared, on="model", how="left")
    noise.to_csv(out / "noise.csv", index=False)

    # parse / valid / error rates per arm from the raw attempt logs
    rates = []
    for arm in ["A", "B"]:
        for f in sorted((root / f"plan_{arm}" / "responses").glob("*.jsonl")):
            recs = [json.loads(l) for l in open(f)]
            label = recs[0]["model_label"] if recs else f.stem
            valid_ids = {r["request_id"] for r in recs if r.get("valid")}
            rates.append(dict(
                model=label, arm=arm, attempts=len(recs), valid_requests=len(valid_ids),
                unparseable_attempts=sum(1 for r in recs if not r.get("valid") and not r.get("error")),
                error_attempts=sum(1 for r in recs if r.get("error")),
                cost_usd=sum(((r.get("response") or {}).get("usage") or {}).get("cost") or 0 for r in recs)))
    rates = pd.DataFrame(rates)
    if len(rates):
        rates["valid_share_of_attempts"] = rates["valid_requests"] / rates["attempts"]
    rates.to_csv(out / "rates.csv", index=False)

    # ordering check: clean > cleared > pending > responsible (strict, on condition means)
    order = []
    for (model, task, arm), g in cells[cells["arm"].isin(["A", "B"])].groupby(["model", "task", "arm"]):
        m = g.set_index("condition")["mean"]
        ranking = list(m.sort_values(ascending=False).index)
        order.append(dict(model=model, task=task, arm=arm, ranking=" > ".join(ranking),
                          expected=ranking == CONDITIONS))
    order = pd.DataFrame(order)
    order.to_csv(out / "ordering.csv", index=False)

    verdict_rows = []
    for model in models:
        nz = noise.set_index("model").loc[model] if model in set(noise["model"]) else None
        level = nz["noise_median"] if nz is not None else np.nan
        e = est[(est["model"] == model) & (est["quantity"] == "removal_effect") & (est["condition"] == "cleared")]
        for _, r in e.iterrows():
            verdict_rows.append(dict(model=model, task=r["task"], removal_effect_cleared=r["estimate"],
                                     ci_low=r["ci_low"], ci_high=r["ci_high"], noise_level=level,
                                     exceeds_noise=abs(r["estimate"]) > level,
                                     ci_excludes_zero=(r["ci_low"] > 0) or (r["ci_high"] < 0)))
    pd.DataFrame(verdict_rows).to_csv(out / "verdict_inputs.csv", index=False)
    write_tables(est, cells, noise, out / "tables.md", models)
    print(f"wrote {out}")


def write_tables(est, cells, noise, path, models):
    """One markdown table per prompt: gaps vs clean in each arm and the removal effect."""
    f = lambda r: f"{r['estimate']:+.1f} [{r['ci_low']:+.1f}, {r['ci_high']:+.1f}]"
    nz = noise.set_index("model")
    lines = []
    for task in TASKS:
        lines += [f"### {task}", "",
                  "| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B - A | Re-run noise (A vs main) |",
                  "|---|---|---|---|---|---|"]
        for model in models:
            cm = cells[(cells.model == model) & (cells.task == task) & (cells.condition == "clean")].set_index("arm")["mean"]
            lines.append(f"| {model} | clean (mean score) | {cm.get('A', np.nan):.1f} | {cm.get('B', np.nan):.1f} | "
                         f"{f(est[(est.model == model) & (est.task == task) & (est.quantity == 'clean_level_shift')].iloc[0])} (level shift) | |")
            for c in CONDITIONS[1:]:
                g = lambda q, a: est[(est.model == model) & (est.task == task) & (est.quantity == q) & (est.arm == a) & (est.condition == c)].iloc[0]
                lines.append(f"| {model} | {c} | {f(g('gap_vs_clean', 'A'))} | {f(g('gap_vs_clean', 'B'))} | "
                             f"{f(g('removal_effect', 'B-A'))} | {g('rerun_difference', 'A-main')['estimate']:+.1f} |")
        lines.append("")
    lines += ["### Noise level per model (absolute difference in condition-vs-clean gaps, arm A vs the main run, 9 gaps per model)", "",
              "| Model | Median | Mean | Max |", "|---|---|---|---|"]
    for model in models:
        r = nz.loc[model]
        lines.append(f"| {model} | {r.noise_median:.2f} | {r.noise_mean:.2f} | {r.noise_max:.2f} |")
    Path(path).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
