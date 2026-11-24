"""Analysis of the graduate research fellowship evaluation run.

    python analysis/fellowship.py
    (reads results/fellowship-main/; the attempts table also needs the local raw
    replies in runs/fellowship/main/responses, and is skipped if those are absent)

Reuses the PhD estimators in analyze_main.py and adds what the fellowship run
specification asks for (old/docs/fellowship-run-spec.md, step 4):

- Both exports are analysed: results.csv (eventual valid reply per request) and
  first_attempt_results.csv (the first attempt only, so retried requests count
  as missing there). The `input` column says which one.
- Paired contrasts use matched cells: a condition is compared with its
  reference only within the same applicant, wording, format and repeat, and
  only where both replies are valid. Cell differences are averaged within
  applicant, then across applicants, with an applicant-clustered t interval.
  `n_cells` and `n_applicants` give the denominators. A parse failure is never
  coded as a score of zero.
- The mixed model (score ~ condition + wording + format, applicant random
  intercept) is a sensitivity analysis.
- Multiplicity: Holm within model x prompt x outcome x analysis x input, over
  contrast families a-d plus neutral_control vs clean; Bonferroni intervals for
  the same set (`ci_low_adj`/`ci_high_adj`).
- Binary outcome: the advance (yes) and final-decision (award) rate.
- Heterogeneity: by original provisional generation tier (descriptive only)
  and by each model's own clean score, cross-fitted across the two clean
  wordings. Clean means below 15 are floor-flagged, above 85 ceiling-flagged.
- Wording and format moderation. Llama 4 Maverick's format contrast is marked
  not interpretable, because it wrote prose in both formats in the PhD run.
- Rationale scan: how often rationale-format replies mention the integrity
  record, and how often they tie it to the applicant's listed work.
- PhD comparison: the same model's PhD estimate beside the fellowship one, for
  description only. Applicants are not matched people across opportunities.

No equivalence tests are run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_main import (ADVERSE, CLEARED, CONDITION_ORDER, FLOOR, NOT_INTERPRETABLE_FORMAT,  # noqa: E402
                          TASKS, TIERS, add_intervals, contrast_families, make_figures, mixed_block,
                          moderation_block, strength_block, summarize_diffs)

CEILING = 85.0
CELL = ["applicant_id", "wording", "format", "repeat"]
INTEGRITY = re.compile(r"integrity|allegation|accus|misconduct|generative ai|\bai\b|hearing|appeal|"
                       r"responsib|exonerat|cleared|dismiss|withdr|sanction|investigat|registrar", re.I)
# Listed-work words only. "course", "assignment" and "grade" are left out on purpose:
# they appear in the condition wording itself ("a course assignment ... grade of zero").
# This is a coarse screen; the write-up backs it with read examples.
WORK = r"(project|capstone|research assist|research experience|research output|poster|preprint|symposium|independent study|proposal)"
LINKED_WORK = re.compile(r"(integrity|allegation|accus|misconduct|\bai\b)[^.]{0,120}" + WORK + "|"
                         + WORK + r"[^.]{0,120}(integrity|allegation|accus|misconduct|\bai\b)", re.I)


def load(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = raw[raw.valid.astype(str).str.lower() == "true"].copy()
    df["score"] = pd.to_numeric(df.score, errors="coerce")
    df["decision"] = pd.to_numeric(df.decision, errors="coerce")
    return df


def matched_block(d: pd.DataFrame, value: str, contrasts, base) -> list[dict]:
    """Paired contrasts on matched applicant/wording/format/repeat cells."""
    wide = d.pivot_table(index=CELL, columns="condition", values=value, aggfunc="mean")
    rows = []
    for family, a, b in contrasts:
        if a not in wide or b not in wide:
            continue
        diff = (wide[a] - wide[b]).dropna()
        per_applicant = diff.groupby(level="applicant_id").mean()
        r = summarize_diffs(per_applicant)
        ref = wide[b].reindex(diff.index)
        rows.append({**base, "family": family, "contrast": f"{a} - {b}", "condition": a, "reference": b,
                     "reference_mean": ref.mean(), "n_cells": int(len(diff)), **r})
    return rows


def analyse(df: pd.DataFrame, label: str) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    contrasts = contrast_families(set(df.condition))
    ac = [c for c in contrasts if c[0] in ("a_cleared_vs_clean", "c_adverse_vs_clean")]
    main_rows, tier_rows, strength_rows, mod_rows, mixed_info, cells = [], [], [], [], [], []
    for (model, task), d in df.groupby(["model_label", "task"], sort=False):
        base = {"input": label, "model": model, "task": task, "subset": None}
        rows, info = mixed_block(d, contrasts, {**base, "analysis": "mixed", "outcome": "score"})
        main_rows += rows
        mixed_info.append({"input": label, **info})
        main_rows += matched_block(d, "score", contrasts, {**base, "analysis": "paired", "outcome": "score"})
        if d.decision.notna().any():
            main_rows += matched_block(d[d.decision.notna()], "decision", contrasts,
                                       {**base, "analysis": "paired", "outcome": "decision_yes_rate"})
        for tier in TIERS:
            dt = d[d.cv_tier == tier]
            if dt.empty:
                continue
            clean_score = dt[dt.condition == "clean"].score.mean()
            for value, outcome in (("score", "score"), ("decision", "decision_yes_rate")):
                if dt[value].notna().any():
                    rs = matched_block(dt[dt[value].notna()], value, ac,
                                       {**base, "analysis": "by_original_tier", "outcome": outcome, "subset": tier})
                    for r in rs:
                        r.update(clean_mean_score=clean_score, floor_flag=bool(clean_score < FLOOR),
                                 ceiling_flag=bool(clean_score > CEILING),
                                 note="descriptive: original provisional generation tier, not a validated rating")
                    tier_rows += rs
        strength_rows += strength_block(d, {**base, "analysis": "by_clean_score", "outcome": "score"})
        for factor in ("wording", "format"):
            rs = moderation_block(d, "score", factor, {**base, "analysis": f"by_{factor}", "outcome": "score"})
            if factor == "format" and model in NOT_INTERPRETABLE_FORMAT:
                for r in rs:
                    r["note"] = "interpret with caution: this model wrote prose in both formats in the PhD run"
            mod_rows += rs
        for c, dc in d.groupby("condition"):
            cells.append(dict(input=label, model=model, task=task, condition=c, n=len(dc),
                              mean_score=dc.score.mean(), sd_score=dc.score.std(), yes_rate=dc.decision.mean(),
                              share_score_le_5=(dc.score <= 5).mean(), share_score_ge_95=(dc.score >= 95).mean()))
        for t, dc in d[d.condition == "clean"].groupby("cv_tier"):
            m = dc.score.mean()
            cells.append(dict(input=label, model=model, task=task, condition="clean", cv_tier=t, n=len(dc),
                              mean_score=m, sd_score=dc.score.std(), yes_rate=dc.decision.mean(),
                              share_score_le_5=(dc.score <= 5).mean(), share_score_ge_95=(dc.score >= 95).mean(),
                              floor_flag=bool(m < FLOOR), ceiling_flag=bool(m > CEILING)))
    keys = ["input", "model", "task", "outcome", "analysis"]
    parts = [add_intervals(main_rows, keys), add_intervals(tier_rows, keys),
             add_intervals([r for r in strength_rows if r.get("subset") is None], keys),
             add_intervals([r for r in strength_rows if r.get("subset") is not None], keys),
             add_intervals(mod_rows, keys)]
    est = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    return est, mixed_info, cells


def rationale_scan(df: pd.DataFrame) -> pd.DataFrame:
    r = df[(df.format == "rationale") & df.rationale.notna()].copy()
    r["mentions_record"] = r.rationale.str.contains(INTEGRITY)
    r["links_record_to_work"] = r.rationale.str.contains(LINKED_WORK)
    return (r.groupby(["model_label", "condition"])
             .agg(n=("rationale", "size"), mentions_record=("mentions_record", "mean"),
                  links_record_to_work=("links_record_to_work", "mean"))
             .reset_index())


def retries_by_condition(responses: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(responses.glob("*.jsonl")):
        recs = [json.loads(line) for line in f.open()]
        first = {}
        for r in recs:
            first.setdefault(r["request_id"], r)
        for r in first.values():
            rows.append(dict(model=r["model_label"], condition=r["condition"],
                             first_valid=bool(r["valid"]), first_error=bool(r["error"]),
                             first_unparseable=(not r["valid"]) and not r["error"]))
        extra = sum("extra_attempt" in r for r in recs)
        rows.append(dict(model=recs[0]["model_label"], condition="_all", extra_third_attempts=extra))
    t = pd.DataFrame(rows)
    g = t[t.condition != "_all"].groupby(["model", "condition"]).agg(
        requests=("first_valid", "size"), first_attempt_valid=("first_valid", "sum"),
        first_attempt_error=("first_error", "sum"), first_attempt_unparseable=("first_unparseable", "sum"))
    return g.reset_index()


def phd_comparison(est: pd.DataFrame, phd_path: Path) -> pd.DataFrame:
    if not phd_path.exists():
        return pd.DataFrame()
    phd = pd.read_csv(phd_path)
    phd = phd[(phd.analysis == "paired") & (phd.outcome == "score") & phd.subset.isna()
              & (phd.reference == "clean")]
    fel = est[(est.input == "eventual") & (est.analysis == "paired") & (est.outcome == "score")
              & est.subset.isna() & (est.reference == "clean")]
    cols = ["model", "task", "condition", "estimate", "ci_low", "ci_high", "holm_significant"]
    j = fel[cols].merge(phd[cols], on=["model", "task", "condition"], suffixes=("_fellowship", "_phd"))
    j["note"] = "descriptive; different fictional applicants and opportunity, not matched people"
    return j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/fellowship-main", help="folder with results.csv and first_attempt_results.csv")
    ap.add_argument("--responses", default="runs/fellowship/main/responses", help="raw replies (local; optional)")
    ap.add_argument("--out", default="results/fellowship-main/analysis")
    ap.add_argument("--phd-estimates", default="results/phd-main/analysis/estimates.csv")
    args = ap.parse_args()
    plan = Path(args.results)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    parts, fits, cells = [], [], []
    for label, name in (("eventual", "results.csv"), ("first_attempt", "first_attempt_results.csv")):
        if not (plan / name).exists():
            continue
        df = load(plan / name)
        e, f, c = analyse(df, label)
        parts.append(e)
        fits += f
        cells += c
        if label == "eventual":
            rationale_scan(df).to_csv(out / "rationale_scan.csv", index=False)
    est = pd.concat(parts, ignore_index=True)
    for flag in ("floor_flag", "ceiling_flag"):
        if flag in est:
            est[flag] = est[flag].fillna(False).astype(bool)
    first = ["input", "model", "task", "outcome", "analysis", "subset", "family", "contrast", "condition",
             "reference", "estimate", "se", "ci_low", "ci_high", "p_raw", "p_holm", "ci_low_adj", "ci_high_adj",
             "holm_significant", "n_in_family", "n_applicants", "n_cells", "df"]
    est = est[[c for c in first if c in est] + [c for c in est.columns if c not in first]]
    est.to_csv(out / "estimates.csv", index=False)
    pd.DataFrame(fits).to_csv(out / "mixed_model_fits.csv", index=False)
    pd.DataFrame(cells).to_csv(out / "cell_means.csv", index=False)
    if Path(args.responses).is_dir():
        retries_by_condition(Path(args.responses)).to_csv(out / "attempts_by_model_condition.csv", index=False)

    ev = est[est.input == "eventual"]
    m = ev[ev.analysis == "mixed"].set_index(["model", "task", "contrast"])
    p = ev[(ev.analysis == "paired") & (ev.outcome == "score")].set_index(["model", "task", "contrast"])
    cols = ["estimate", "se", "holm_significant"]
    j = m[cols].add_suffix("_mixed").join(p[cols].add_suffix("_paired"))
    j["same_conclusion"] = j.holm_significant_mixed == j.holm_significant_paired
    j.reset_index().to_csv(out / "mixed_vs_paired.csv", index=False)
    phd_comparison(est, Path(args.phd_estimates)).to_csv(out / "phd_comparison.csv", index=False)
    make_figures(ev.drop(columns=["input"]), out)
    print(json.dumps({"estimates": int(len(est)), "inputs": sorted(est.input.unique()),
                      "models": sorted(est.model.unique()), "mixed_vs_paired_same": int(j.same_conclusion.sum()),
                      "mixed_vs_paired_total": int(len(j)), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
