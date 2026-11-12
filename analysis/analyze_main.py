"""Analysis of the PhD evaluation run.

Reads results.csv written by `python3 -m phd_eval collect` and writes a tidy CSV
of estimates, one figure per prompt and supporting tables.

    python analysis/analyze_main.py --plan runs/main

Everything is computed separately for each model and prompt (task).

Estimators
- mixed:  score ~ condition (reference = clean) + wording + format, with a
          random intercept for applicant (statsmodels MixedLM, REML). Contrasts
          are linear combinations of the fixed effects; intervals are Wald (z).
- paired: for each applicant, the mean outcome in condition A minus the mean in
          condition B over that applicant's cells; then the mean of those
          applicant-level differences. The standard error is sd/sqrt(n) over
          applicants, which is the applicant-clustered standard error for this
          contrast. Intervals use t with n-1 degrees of freedom.

Multiple comparisons: Holm within model x prompt x outcome x estimator, over the
contrast families a-d plus neutral_control vs clean. `ci_low_adj`/`ci_high_adj`
are Bonferroni intervals for the same set (level 1 - 0.05/m), which are at
least as wide as anything Holm implies.
"""
from __future__ import annotations

import argparse
import itertools
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

CLEARED = ["cleared", "dismissed", "withdrawn", "exonerated_on_appeal",
           "exonerated_acknowledged", "procedural_reversal"]
ADVERSE = ["pending", "responsible", "responsible_rehabilitated"]
CONDITION_ORDER = ["neutral_control"] + CLEARED + ADVERSE
TASKS = ["quality", "advance", "decide"]
TIERS = ["weak", "borderline", "strong"]
FLOOR = 15.0
ALPHA = 0.05
NOT_INTERPRETABLE_FORMAT = {"Llama 4 Maverick"}


def contrast_families(conditions: set[str]) -> list[tuple[str, str, str]]:
    """(family, A, B) meaning A minus B, restricted to conditions present."""
    out = []
    has = lambda *c: all(x in conditions for x in c)
    if has("neutral_control", "clean"):
        out.append(("control_vs_clean", "neutral_control", "clean"))
    out += [("a_cleared_vs_clean", c, "clean") for c in CLEARED if has(c, "clean")]
    out += [("b_cleared_vs_control", c, "neutral_control") for c in CLEARED
            if has(c, "neutral_control")]
    out += [("c_adverse_vs_clean", c, "clean") for c in ADVERSE if has(c, "clean")]
    out += [("d_cleared_pairwise", a, b)
            for a, b in itertools.combinations(CLEARED, 2) if has(a, b)]
    return out


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    out = np.full(p.shape, np.nan)
    ok = ~np.isnan(p)
    m = int(ok.sum())
    if m == 0:
        return out
    idx = np.where(ok)[0][np.argsort(p[ok])]
    running = 0.0
    for rank, i in enumerate(idx):
        running = max(running, (m - rank) * p[i])
        out[i] = min(1.0, running)
    return out


def summarize_diffs(d: pd.Series) -> dict:
    """Mean of applicant-level differences with a t interval."""
    d = d.dropna()
    n = len(d)
    if n < 2:
        return dict(estimate=np.nan, se=np.nan, df=np.nan, p_raw=np.nan, n_applicants=n)
    est, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
    if se == 0:
        p = 1.0 if est == 0 else 0.0
    else:
        p = 2 * stats.t.sf(abs(est / se), n - 1)
    return dict(estimate=est, se=se, df=n - 1, p_raw=p, n_applicants=n)


def add_intervals(rows: list[dict], group_keys: list[str]) -> pd.DataFrame:
    """Raw 95% intervals, Holm p-values and Bonferroni intervals within groups."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    def crit(level, dfree):
        return np.where(np.isnan(dfree), stats.norm.ppf(level),
                        stats.t.ppf(level, np.where(np.isnan(dfree), 1, dfree)))

    c = crit(1 - ALPHA / 2, df["df"].to_numpy(float))
    df["ci_low"], df["ci_high"] = df.estimate - c * df.se, df.estimate + c * df.se
    df["p_holm"] = np.nan
    df["n_in_family"] = 0
    df["ci_low_adj"] = np.nan
    df["ci_high_adj"] = np.nan
    for _, idx in df.groupby(group_keys, sort=False).groups.items():
        m = int(df.loc[idx, "p_raw"].notna().sum())
        df.loc[idx, "p_holm"] = holm(df.loc[idx, "p_raw"].to_numpy())
        df.loc[idx, "n_in_family"] = m
        if m:
            ca = crit(1 - ALPHA / (2 * m), df.loc[idx, "df"].to_numpy(float))
            df.loc[idx, "ci_low_adj"] = df.loc[idx, "estimate"] - ca * df.loc[idx, "se"]
            df.loc[idx, "ci_high_adj"] = df.loc[idx, "estimate"] + ca * df.loc[idx, "se"]
    df["holm_significant"] = df.p_holm < ALPHA
    return df


def applicant_means(d: pd.DataFrame, value: str) -> pd.DataFrame:
    """Applicants x conditions table of mean outcome."""
    return d.pivot_table(index="applicant_id", columns="condition", values=value, aggfunc="mean")


def paired_block(d, value, contrasts, base):
    wide = applicant_means(d, value)
    rows = []
    for family, a, b in contrasts:
        if a not in wide or b not in wide:
            continue
        r = summarize_diffs(wide[a] - wide[b])
        rows.append({**base, "family": family, "contrast": f"{a} - {b}",
                     "condition": a, "reference": b,
                     "reference_mean": wide[b].mean(), **r})
    return rows


def mixed_block(d, contrasts, base):
    conds = sorted(d.condition.unique())
    terms = ["C(condition, Treatment('clean'))"]
    if d.wording.nunique() > 1:
        terms.append("C(wording)")
    if d.format.nunique() > 1:
        terms.append("C(format)")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fit = smf.mixedlm("score ~ " + " + ".join(terms), d, groups=d["applicant_id"]).fit(reml=True)
    notes = "; ".join(sorted({str(w.message)[:80] for w in caught}))
    fe = fit.fe_params
    cov = fit.cov_params().loc[fe.index, fe.index]
    name = lambda c: f"C(condition, Treatment('clean'))[T.{c}]"
    rows = []
    for family, a, b in contrasts:
        if a not in conds or b not in conds:
            continue
        L = pd.Series(0.0, index=fe.index)
        if a != "clean":
            L[name(a)] += 1
        if b != "clean":
            L[name(b)] -= 1
        est = float(L @ fe)
        se = float(np.sqrt(L @ cov @ L))
        rows.append({**base, "family": family, "contrast": f"{a} - {b}", "condition": a,
                     "reference": b, "estimate": est, "se": se, "df": np.nan,
                     "p_raw": 2 * stats.norm.sf(abs(est / se)) if se > 0 else np.nan,
                     "n_applicants": d.applicant_id.nunique(), "note": notes})
    extra = {"model": base["model"], "task": base["task"],
             "applicant_sd": float(np.sqrt(fit.cov_re.iloc[0, 0])),
             "residual_sd": float(np.sqrt(fit.scale)), "converged": bool(fit.converged),
             "n_rows": int(len(d)), "warnings": notes}
    for k in fe.index:
        if k.startswith("C(wording)") or k.startswith("C(format)"):
            extra[k] = float(fe[k])
    return rows, extra


def moderation_block(d, value, factor, base):
    """Does (condition - clean) differ between the two levels of wording or format?"""
    levels = sorted(d[factor].unique())
    if len(levels) != 2 or "clean" not in set(d.condition):
        return []
    lo, hi = levels
    w = d.pivot_table(index="applicant_id", columns=["condition", factor], values=value, aggfunc="mean")
    rows = []
    for c in CONDITION_ORDER:
        if c not in w.columns.get_level_values(0):
            continue
        d_lo = w[(c, lo)] - w[("clean", lo)]
        d_hi = w[(c, hi)] - w[("clean", hi)]
        r = summarize_diffs(d_hi - d_lo)
        rows.append({**base, "family": f"moderation_{factor}", "condition": c, "reference": "clean",
                     "contrast": f"({c} - clean) at {factor}={hi} minus at {factor}={lo}",
                     "diff_at_first_level": d_lo.mean(), "diff_at_second_level": d_hi.mean(), **r})
    return rows


def strength_block(d, base):
    """Penalty as a function of the applicant's own clean-record score.

    The clean score is both the baseline and the moderator, so noise in it would
    create a spurious negative slope. Cross-fitting avoids that: strength is the
    clean mean under one clean wording, and the difference is taken against the
    clean mean under the other wording; both halves are stacked and standard
    errors are clustered by applicant.
    """
    if d.wording.nunique() != 2 or "clean" not in set(d.condition):
        return []
    clean = d[d.condition == "clean"].pivot_table(index="applicant_id", columns="wording",
                                                  values="score", aggfunc="mean")
    w1, w2 = sorted(clean.columns)
    cond = applicant_means(d, "score")
    rows = []
    for c in CLEARED + ADVERSE:
        if c not in cond:
            continue
        parts = []
        for s, o in ((w1, w2), (w2, w1)):
            parts.append(pd.DataFrame({"applicant_id": clean.index, "strength": clean[s].values,
                                       "diff": (cond[c].reindex(clean.index) - clean[o]).values}))
        st = pd.concat(parts).dropna()
        if st.applicant_id.nunique() < 10 or st.strength.std() == 0:
            continue
        st["s10"] = (st.strength - st.strength.mean()) / 10.0
        fit = smf.ols("diff ~ s10", st).fit(cov_type="cluster", cov_kwds={"groups": st.applicant_id})
        n = st.applicant_id.nunique()
        fam = "a_cleared_vs_clean" if c in CLEARED else "c_adverse_vs_clean"
        rows.append({**base, "family": fam, "condition": c, "reference": "clean",
                     "contrast": f"slope of ({c} - clean) per 10 points of own clean score",
                     "estimate": fit.params["s10"], "se": fit.bse["s10"], "df": n - 1,
                     "p_raw": 2 * stats.t.sf(abs(fit.params["s10"] / fit.bse["s10"]), n - 1),
                     "n_applicants": n, "reference_mean": st.strength.mean()})
        bands = [("clean score < 15", st.strength < FLOOR),
                 ("clean score 15 to <50", (st.strength >= FLOOR) & (st.strength < 50)),
                 ("clean score >= 50", st.strength >= 50)]
        for label, mask in bands:
            sb = st[mask]
            k = sb.applicant_id.nunique()
            if k < 5:
                continue
            per = sb.groupby("applicant_id")["diff"].mean()
            r = summarize_diffs(per)
            rows.append({**base, "family": fam, "condition": c, "reference": "clean",
                         "subset": label, "contrast": f"{c} - clean", **r,
                         "reference_mean": sb.strength.mean(),
                         "floor_flag": bool(sb.strength.mean() < FLOOR)})
    return rows


def reply_tables(plan: Path, out: Path):
    """Attempt counts from the raw replies (every attempt is one line)."""
    rdir = plan / "responses"
    if not rdir.is_dir():
        return None, None
    per_model, retries = [], []
    for f in sorted(rdir.glob("*.jsonl")):
        recs = [json.loads(line) for line in f.open()]
        if not recs:
            continue
        label = recs[0]["model_label"]
        cost = sum(((r.get("response") or {}).get("usage") or {}).get("cost") or 0 for r in recs)
        valid = sum(bool(r["valid"]) for r in recs)
        err = sum((not r["valid"]) and bool(r.get("error")) for r in recs)
        unp = sum((not r["valid"]) and not r.get("error") for r in recs)
        per_model.append(dict(model=label, api_model=recs[0]["api_model"], sent=len(recs),
                              valid=valid, valid_unique=len({r["request_id"] for r in recs if r["valid"]}),
                              unparseable=unp, errors=err, cost_usd=round(cost, 2)))
        for r in recs:
            if not r["valid"]:
                retries.append(dict(model=label, condition=r["condition"], task=r["task"],
                                    format=r["format"], request_id=r["request_id"],
                                    kind="error" if r.get("error") else "unparseable",
                                    problem=r.get("problem"), reply_excerpt=(r.get("reply") or "")[:300]))
    pm = pd.DataFrame(per_model)
    rt = pd.DataFrame(retries)
    pm.to_csv(out / "replies_by_model.csv", index=False)
    rt.to_csv(out / "invalid_attempts.csv", index=False)
    if not rt.empty:
        (rt[rt.kind == "unparseable"].groupby(["model", "condition"]).request_id.nunique()
         .unstack(fill_value=0).to_csv(out / "unparseable_retries_by_model_condition.csv"))
    return pm, rt


def make_figures(est: pd.DataFrame, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid, blue = "#1f1f1e", "#6b6a63", "#e4e3dc", "#2a78d6"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": grid, "axes.labelcolor": muted,
                         "xtick.color": muted, "ytick.color": ink, "font.family": "DejaVu Sans"})
    main = est[(est.analysis == "paired") & (est.outcome == "score") & (est.reference == "clean")
               & est.subset.isna()]
    models = list(dict.fromkeys(main.model))
    for task in [t for t in TASKS if t in set(main.task)]:
        for suffix, conds in (("", CONDITION_ORDER), ("_cleared_zoom", ["neutral_control"] + CLEARED)):
            sub = main[(main.task == task) & main.condition.isin(conds)]
            conds_present = [c for c in conds if c in set(sub.condition)]
            if not conds_present:
                continue
            fig, axes = plt.subplots(1, len(models), figsize=(2.15 * len(models) + 1.9, 0.36 * len(conds_present) + 1.9),
                                     sharex=True, sharey=True)
            axes = np.atleast_1d(axes)
            ypos = {c: i for i, c in enumerate(reversed(conds_present))}
            for ax, m in zip(axes, models):
                s = sub[sub.model == m]
                ax.axvline(0, color=muted, lw=1, zorder=1)
                for _, r in s.iterrows():
                    y = ypos[r.condition]
                    ax.plot([r.ci_low, r.ci_high], [y, y], color=blue, lw=2, solid_capstyle="round", zorder=2)
                    ax.plot(r.estimate, y, "o", ms=6.5, mec=blue, mew=1.6,
                            mfc=blue if r.holm_significant else "white", zorder=3)
                ax.set_title(m, fontsize=9, color=ink, loc="left")
                ax.set_yticks(list(ypos.values()), list(ypos.keys()))
                ax.set_ylim(-0.6, len(conds_present) - 0.4)
                ax.grid(axis="x", color=grid, lw=0.8)
                ax.set_axisbelow(True)
                ax.tick_params(length=0)
                for sp in ("top", "right", "left"):
                    ax.spines[sp].set_visible(False)
            fig.supxlabel("Mean difference from the same applicant's clean record (score points, 0-100)",
                          fontsize=9, color=muted)
            from matplotlib.lines import Line2D
            handles = [Line2D([], [], marker="o", color=blue, mfc=blue, mec=blue, lw=2, label="Holm-corrected p < .05"),
                       Line2D([], [], marker="o", color=blue, mfc="white", mec=blue, lw=2, label="not significant after Holm")]
            fig.legend(handles=handles, loc="upper right", ncol=2, frameon=False, fontsize=8)
            zoom = " (cleared-type conditions only)" if suffix else ""
            fig.suptitle(f"Prompt: {task}{zoom}. Points are paired applicant-level means; bars are raw 95% intervals",
                         x=0.01, ha="left", fontsize=10, color=ink)
            fig.tight_layout(rect=(0, 0, 1, 0.93))
            fig.savefig(out / f"fig_{task}{suffix}.png", dpi=180, facecolor="white")
            plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="runs/main", help="plan directory containing results.csv")
    ap.add_argument("--out", default=None, help="output directory (default <plan>/analysis)")
    args = ap.parse_args()
    plan = Path(args.plan)
    out = Path(args.out) if args.out else plan / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(plan / "results.csv")
    df = raw[raw.valid.astype(str).str.lower() == "true"].copy()
    df["score"] = pd.to_numeric(df.score, errors="coerce")
    df["decision"] = pd.to_numeric(df.decision, errors="coerce")
    conditions = set(df.condition)
    contrasts = contrast_families(conditions)
    ac = [c for c in contrasts if c[0] in ("a_cleared_vs_clean", "c_adverse_vs_clean")]

    main_rows, tier_rows, strength_rows, mod_rows, mixed_info, cells = [], [], [], [], [], []
    for (model, task), d in df.groupby(["model_label", "task"], sort=False):
        base = {"model": model, "task": task, "subset": None}
        # Mixed model and paired estimates of the score
        rows, info = mixed_block(d, contrasts, {**base, "analysis": "mixed", "outcome": "score"})
        main_rows += rows
        mixed_info.append(info)
        main_rows += paired_block(d, "score", contrasts, {**base, "analysis": "paired", "outcome": "score"})
        # Binary decision: difference in yes-rate
        if d.decision.notna().any():
            main_rows += paired_block(d[d.decision.notna()], "decision", contrasts,
                                      {**base, "analysis": "paired", "outcome": "decision_yes_rate"})
        # Heterogeneity by CV tier
        for tier in TIERS:
            dt = d[d.cv_tier == tier]
            if dt.empty:
                continue
            for value, outcome in (("score", "score"), ("decision", "decision_yes_rate")):
                if dt[value].notna().any():
                    rs = paired_block(dt[dt[value].notna()], value, ac,
                                      {**base, "analysis": "by_cv_tier", "outcome": outcome, "subset": tier})
                    clean_score = dt[dt.condition == "clean"].score.mean()
                    for r in rs:
                        r["clean_mean_score"] = clean_score
                        r["floor_flag"] = bool(clean_score < FLOOR)
                    tier_rows += rs
        # Heterogeneity by own clean score
        strength_rows += strength_block(d, {**base, "analysis": "by_clean_score", "outcome": "score"})
        # Wording and format
        for factor in ("wording", "format"):
            rs = moderation_block(d, "score", factor, {**base, "analysis": f"by_{factor}", "outcome": "score"})
            if factor == "format" and model in NOT_INTERPRETABLE_FORMAT:
                for r in rs:
                    r["note"] = "not interpretable: this model writes long prose in both formats"
            mod_rows += rs
        # Descriptive cell means
        for c, dc in d.groupby("condition"):
            cells.append(dict(model=model, task=task, condition=c, n=len(dc), mean_score=dc.score.mean(),
                              sd_score=dc.score.std(), yes_rate=dc.decision.mean(),
                              share_score_le_5=(dc.score <= 5).mean(), share_score_ge_95=(dc.score >= 95).mean()))
        for t, dc in d[d.condition == "clean"].groupby("cv_tier"):
            cells.append(dict(model=model, task=task, condition="clean", cv_tier=t, n=len(dc),
                              mean_score=dc.score.mean(), sd_score=dc.score.std(), yes_rate=dc.decision.mean(),
                              share_score_le_5=(dc.score <= 5).mean(), share_score_ge_95=(dc.score >= 95).mean()))

    keys = ["model", "task", "outcome", "analysis"]
    parts = [add_intervals(main_rows, keys),
             add_intervals(tier_rows, keys),
             add_intervals([r for r in strength_rows if r.get("subset") is None], keys),
             add_intervals([r for r in strength_rows if r.get("subset") is not None], keys),
             add_intervals(mod_rows, keys)]
    est = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    if "floor_flag" in est:
        est["floor_flag"] = est.floor_flag.fillna(False).astype(bool)
    first = ["model", "task", "outcome", "analysis", "subset", "family", "contrast", "condition", "reference",
             "estimate", "se", "ci_low", "ci_high", "p_raw", "p_holm", "ci_low_adj", "ci_high_adj",
             "holm_significant", "n_in_family", "n_applicants", "df"]
    est = est[first + [c for c in est.columns if c not in first]]
    est.to_csv(out / "estimates.csv", index=False)
    pd.DataFrame(mixed_info).to_csv(out / "mixed_model_fits.csv", index=False)
    pd.DataFrame(cells).to_csv(out / "cell_means.csv", index=False)

    # Agreement between the mixed model and the paired estimate
    m = est[(est.analysis == "mixed")].set_index(["model", "task", "contrast"])
    p = est[(est.analysis == "paired") & (est.outcome == "score")].set_index(["model", "task", "contrast"])
    cols = ["estimate", "se", "holm_significant"]
    j = m[cols].add_suffix("_mixed").join(p[cols].add_suffix("_paired"))
    j["estimate_gap"] = (j.estimate_mixed - j.estimate_paired).abs()
    j["se_ratio_paired_over_mixed"] = j.se_paired / j.se_mixed
    j["same_conclusion"] = j.holm_significant_mixed == j.holm_significant_paired
    j.reset_index().to_csv(out / "mixed_vs_paired.csv", index=False)

    pm, rt = reply_tables(plan, out)
    make_figures(est, out)

    print(json.dumps({
        "rows_read": int(len(raw)), "valid_rows": int(len(df)),
        "models": sorted(df.model_label.unique()), "conditions": sorted(conditions),
        "estimates": int(len(est)),
        "mixed_vs_paired": {"max_estimate_gap": float(j.estimate_gap.max()),
                            "contrasts": int(len(j)), "same_conclusion": int(j.same_conclusion.sum())},
        "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
