"""Offline analysis of a future collected PhD follow-up. Does not call APIs.

Requires scipy from analysis/requirements.txt. Reads results.csv, design.jsonl,
and optional raw attempt logs. No existing experiment is modified.
"""

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.phd_followup_spec import (  # noqa: E402
    CONDITIONS, MODELS, PRIMARY_PAIRS, SCENARIOS, TASKS, load_manifest,
)


def truth(value):
    if value is True or value == "True" or value == "true":
        return True
    if value is False or value == "False" or value == "false":
        return False
    raise ValueError(f"Invalid validity flag: {value!r}")


def paired_summary(values, family_size):
    """Each value is one applicant's paired difference, after averaging wording."""
    from scipy import stats

    values = list(values)
    n = len(values)
    result = dict(n_applicants=n, estimate=None, se=None, df=max(n - 1, 0),
                  ci_low=None, ci_high=None, ci_low_adj=None, ci_high_adj=None, p_raw=None)
    if n:
        result["estimate"] = statistics.mean(values)
    if n < 2:
        return result
    se = statistics.stdev(values) / math.sqrt(n)
    mean = result["estimate"]
    raw_margin = stats.t.ppf(.975, n - 1) * se
    adjusted_margin = stats.t.ppf(1 - .05 / (2 * family_size), n - 1) * se
    p = float(2 * stats.t.sf(abs(mean / se), n - 1)) if se else (0.0 if mean else 1.0)
    result.update(se=se, ci_low=mean - raw_margin, ci_high=mean + raw_margin,
                  ci_low_adj=mean - adjusted_margin, ci_high_adj=mean + adjusted_margin,
                  p_raw=p)
    return result


def holm_fixed(pvalues):
    """Retain missing planned tests as p=1 internally; output missing as None."""
    pvalues = list(pvalues)
    order = sorted(range(len(pvalues)), key=lambda i: 1 if pvalues[i] is None else pvalues[i])
    result = [None] * len(pvalues)
    largest = 0.0
    for rank, index in enumerate(order):
        p = 1.0 if pvalues[index] is None else pvalues[index]
        largest = min(1.0, max(largest, (len(order) - rank) * p))
        if pvalues[index] is not None:
            result[index] = largest
    return result


def read_design(path):
    with Path(path).open() as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    by_id = {r["request_id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate planned request IDs")
    applicants = sorted({r["applicant_id"] for r in rows})
    expected = {(a, c, w, t) for a in applicants for c in CONDITIONS for w in (1, 2) for t in TASKS}
    observed = {(r["applicant_id"], r["condition"], r["wording"], r["task"]) for r in rows}
    if not applicants or observed != expected or len(rows) != len(expected):
        raise ValueError("Design is not the complete specified within-applicant crossing")
    tiers = {}
    for row in rows:
        expected_id = f"{row['applicant_id']}|{row['condition']}|w{row['wording']}|{row['task']}|answer_only|r1"
        if row["format"] != "answer_only" or row["repeat"] != 1 or row["request_id"] != expected_id:
            raise ValueError("Unexpected format, repeat, or request ID in design")
        if row["cv_tier"] not in {"weak", "borderline", "strong"}:
            raise ValueError("Invalid CV tier")
        if tiers.setdefault(row["applicant_id"], row["cv_tier"]) != row["cv_tier"]:
            raise ValueError("Applicant tier changes across requests")
    return by_id, applicants, tiers


def normalize(row, design):
    model, rid = row["model_label"], row["request_id"]
    if model not in MODELS or row["api_model"] != MODELS[model]:
        raise ValueError("Unknown model label or mismatched API model")
    if rid not in design:
        raise ValueError(f"Unplanned request: {rid}")
    planned = design[rid]
    for field in ("applicant_id", "condition", "wording", "task", "format", "repeat", "cv_tier"):
        if str(row[field]) != str(planned[field]):
            raise ValueError(f"Result metadata disagrees with design: {rid}, {field}")
    valid = truth(row["valid"])
    result = dict(row, valid=valid, wording=int(row["wording"]), repeat=int(row["repeat"]))
    if valid:
        if row.get("error"):
            raise ValueError("A valid row cannot also contain a request error")
        score = float(row["score"])
        if not math.isfinite(score) or not score.is_integer() or not 0 <= score <= 100:
            raise ValueError("A valid score must be an integer in [0,100]")
        result["score"] = score
        if row["task"] == "advance":
            decision = float(row["decision"])
            if decision not in (0, 1):
                raise ValueError("A valid advancement decision must be 0 or 1")
            result["decision"] = decision
    return result


def read_results(path, design):
    with Path(path).open(newline="") as stream:
        rows = [normalize(row, design) for row in csv.DictReader(stream)]
    keys = [(r["model_label"], r["request_id"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate collected rows; do not count retries as observations")
    return rows


def cell_values(rows, outcome):
    """Index valid wording cells; never fill a missing word with the other one."""
    result = {}
    for row in rows:
        if not row["valid"] or (outcome == "decision" and row["task"] != "advance"):
            continue
        key = (row["model_label"], row["task"], row["applicant_id"], row["condition"], row["wording"])
        if key in result:
            raise ValueError("Duplicate analysis cell")
        result[key] = row[outcome]
    return result


def differences(cells, model, task, applicants, weights, wording_interaction=False):
    values = {}
    for applicant in applicants:
        keys = [(model, task, applicant, condition, w) for condition in weights for w in (1, 2)]
        if not all(key in cells for key in keys):
            continue
        by_wording = [sum(weight * cells[(model, task, applicant, condition, w)]
                         for condition, weight in weights.items()) for w in (1, 2)]
        values[applicant] = by_wording[1] - by_wording[0] if wording_interaction else statistics.mean(by_wording)
    return values


def contrast_specs():
    """Enumerate every comparison before inspecting values, including absent models."""
    specs = []
    for model in MODELS:
        for task, outcome, family in (("advance", "score", "primary_advance_score"),
                                      ("quality", "score", "secondary_quality_score"),
                                      ("advance", "decision", "secondary_advance_yes_rate")):
            for scenario in SCENARIOS:
                for state, reference in PRIMARY_PAIRS:
                    specs.append(dict(model=model, task=task, outcome=outcome, family=family,
                                      scenario=scenario, contrast=f"{scenario}_{state}-minus-{scenario}_{reference}",
                                      weights={f"{scenario}_{state}": 1, f"{scenario}_{reference}": -1},
                                      wording_interaction=False))
        for task in TASKS:
            for reference in ("clean", "neutral_control"):
                for condition in CONDITIONS:
                    if condition == reference:
                        continue
                    specs.append(dict(model=model, task=task, outcome="score", family=f"secondary_{task}_vs_{reference}",
                                      scenario="shared" if condition in ("clean", "neutral_control") else condition.rsplit("_", 1)[0],
                                      contrast=f"{condition}-minus-{reference}",
                                      weights={condition: 1, reference: -1}, wording_interaction=False))
            for state, reference in PRIMARY_PAIRS:
                specs.append(dict(model=model, task=task, outcome="score", family=f"secondary_{task}_scenario_interaction",
                                  scenario="fabrication-minus-technical_error",
                                  contrast=f"fabrication-minus-technical_error:{state}-minus-{reference}",
                                  weights={f"fabrication_{state}": 1, f"fabrication_{reference}": -1,
                                           f"technical_error_{state}": -1, f"technical_error_{reference}": 1},
                                  wording_interaction=False))
            for scenario in SCENARIOS:
                for state, reference in PRIMARY_PAIRS:
                    specs.append(dict(model=model, task=task, outcome="score", family=f"secondary_{task}_wording_interaction",
                                      scenario=scenario, contrast=f"wording2-minus-wording1:{scenario}_{state}-minus-{scenario}_{reference}",
                                      weights={f"{scenario}_{state}": 1, f"{scenario}_{reference}": -1},
                                      wording_interaction=True))
    return specs


def estimate_all(rows, applicants, analysis="collected"):
    specs = contrast_specs()
    family_sizes = Counter(s["family"] for s in specs)
    cells = {outcome: cell_values(rows, outcome) for outcome in ("score", "decision")}
    estimates = []
    for spec in specs:
        values = differences(cells[spec["outcome"]], spec["model"], spec["task"], applicants,
                             spec["weights"], spec["wording_interaction"])
        clean = differences(cells["score"], spec["model"], spec["task"], values.keys(), {"clean": 1})
        clean_mean = statistics.mean(clean.values()) if clean else None
        size = family_sizes[spec["family"]]
        estimates.append({k: v for k, v in spec.items() if k not in ("weights", "wording_interaction")} |
                         dict(analysis=analysis, weights=json.dumps(spec["weights"], sort_keys=True),
                              n_expected=len(applicants), n_in_family=size,
                              clean_mean_score=clean_mean, n_with_clean=len(clean),
                              floor_flag=clean_mean < 15 if clean_mean is not None else None,
                              units="proportion" if spec["outcome"] == "decision" else "score_points",
                              **paired_summary(values.values(), size)))
    for family in family_sizes:
        subset = [r for r in estimates if r["family"] == family]
        for row, adjusted in zip(subset, holm_fixed(r["p_raw"] for r in subset)):
            row["p_holm"] = adjusted
            row["corrected_interval_excludes_zero"] = (
                row["ci_low_adj"] > 0 or row["ci_high_adj"] < 0) if row["ci_low_adj"] is not None else None
    return estimates


def cell_means(rows, applicants, tiers):
    result = []
    for outcome in ("score", "decision"):
        cells = cell_values(rows, outcome)
        for model in MODELS:
            for task in TASKS if outcome == "score" else ("advance",):
                for tier in ("all", "weak", "borderline", "strong"):
                    selected = [a for a in applicants if tier == "all" or tiers[a] == tier]
                    for condition in CONDITIONS:
                        values = differences(cells, model, task, selected, {condition: 1})
                        mean = statistics.mean(values.values()) if values else None
                        result.append(dict(model=model, task=task, outcome=outcome, cv_tier=tier,
                                           condition=condition, mean=mean, n_applicants=len(values), n_expected=len(selected),
                                           floor_flag=(mean < 15) if outcome == "score" and condition == "clean" and mean is not None else None))
    return result


def attempt_audit(folder, design):
    """Returns earliest-attempt rows and attempt counts. Does not retry anything."""
    groups = defaultdict(list)
    for path in sorted(Path(folder).glob("*.jsonl")):
        with path.open() as stream:
            for line in stream:
                raw = json.loads(line)
                if raw.get("request_parameters") != {}:
                    raise ValueError("Attempt log contains changed request parameters")
                row = normalize(raw, design)
                groups[(row["model_label"], row["request_id"])].append(row)
    first = [rows[0] for rows in groups.values()]
    audit = []
    for model in MODELS:
        for condition in CONDITIONS:
            requests = [rows for (label, rid), rows in groups.items()
                        if label == model and design[rid]["condition"] == condition]
            attempts = [r for group in requests for r in group]
            retried_unparseable = 0
            for group in requests:
                seen_unparseable = False
                for row in group:
                    if row["valid"]:
                        retried_unparseable += seen_unparseable
                        break
                    seen_unparseable |= not bool(row.get("error"))
            usage = [((r.get("response") or {}).get("usage") or {}) for r in attempts]
            valid_requests = sum(any(r["valid"] for r in group) for group in requests)
            planned = sum(r["condition"] == condition for r in design.values())
            audit.append(dict(model=model, condition=condition, planned_requests=planned,
                              observed_requests=len(requests), attempts=len(attempts), valid_requests=valid_requests,
                              missing_requests=planned-len(requests), remaining_without_valid=planned-valid_requests,
                              first_attempt_valid=sum(group[0]["valid"] for group in requests),
                              unparseable_attempts=sum(not r["valid"] and not r.get("error") for r in attempts),
                              error_attempts=sum(bool(r.get("error")) for r in attempts),
                              requests_retried_after_unparseable=retried_unparseable,
                              known_cost_usd=sum(u.get("cost") or 0 for u in usage),
                              attempts_without_reported_cost=sum(u.get("cost") is None for u in usage)))
    return first, audit


def completion(rows, design):
    return [dict(model=model, expected=len(design), observed=sum(r["model_label"] == model for r in rows),
                 valid=sum(r["model_label"] == model and r["valid"] for r in rows)) for model in MODELS]


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Must be a new output directory")
    parser.add_argument("--manifest", type=Path, default=ROOT / "analysis/phd_followup_conditions.csv")
    parser.add_argument("--allow-incomplete", action="store_true", help="Mark output provisional; preserve all planned correction families")
    args = parser.parse_args(argv)
    load_manifest(args.manifest)
    from phd_resumes.io import digest
    pinned_config = json.loads((args.plan / "config.json").read_text())
    pinned_plan = json.loads((args.plan / "plan.json").read_text())
    pinned_design = [json.loads(line) for line in (args.plan / "design.jsonl").read_text().splitlines() if line.strip()]
    if digest(pinned_config) != pinned_plan["config_hash"] or digest(pinned_design) != pinned_plan["design_hash"]:
        raise ValueError("Pinned config or design hash changed")
    if pinned_config.get("followup", {}).get("study_id") != "phd-focused-followup-v1":
        raise ValueError("Input is not the specified follow-up")
    if pinned_config.get("request_parameters") != {}:
        raise ValueError("Input used unexpected request parameters")
    design, applicants, tiers = read_design(args.plan / "design.jsonl")
    if len(applicants) != 100:
        raise ValueError("The study requires 100 applicants")
    rows = read_results(args.plan / "results.csv", design)
    counts = completion(rows, design)
    complete = all(c["observed"] == c["valid"] == c["expected"] for c in counts)
    if not complete and not args.allow_incomplete:
        raise ValueError("Incomplete study: inspect missing models/cells or explicitly request a provisional analysis")
    estimates = estimate_all(rows, applicants)
    first, attempts = attempt_audit(args.plan / "responses", design)
    if first:
        estimates += estimate_all(first, applicants, analysis="first_attempt_sensitivity")
    means = cell_means(rows, applicants, tiers)
    status = dict(complete=complete, provisional=not complete, applicants=len(applicants),
                  models=counts, first_attempt_logs_available=bool(first),
                  first_attempt_observed_requests=len(first), planned_requests_all_models=len(design)*4,
                  correction_families=dict(Counter(s["family"] for s in contrast_specs())),
                  interval_method="Applicant-level paired Student t; Bonferroni simultaneous intervals within fixed families",
                  p_adjustment="Holm within fixed families; missing planned comparisons remain in family",
                  limitations=["Same applicant bank; no human comparison or equivalence test.",
                               "Missing wording cells are not imputed; contrasts require both wordings for every involved condition.",
                               "First-attempt estimates condition on available parseable pairs and are sensitivity analyses, not a correction for selection.",
                               "These are comparisons of specific scenarios, not a general causal estimate of integrity versus competence."])
    # All reads/calculations finish before creating the requested new output directory.
    args.out.mkdir(parents=True, exist_ok=False)
    write_csv(args.out / "estimates.csv", estimates)
    write_csv(args.out / "cell_means.csv", means)
    write_csv(args.out / "attempts_by_model_condition.csv", attempts)
    (args.out / "analysis_status.json").write_text(json.dumps(status, indent=2) + "\n")
    summary = ["# PhD follow-up analysis", "", "Status: " + ("complete" if complete else "PROVISIONAL / INCOMPLETE"), "",
               "Primary outcome: advancement score. The primary family includes 36 planned comparisons across four models, even when some comparisons are missing.", "",
               "Each observation for inference is an applicant-level contrast averaged over two wordings. Raw intervals are 95% Student t intervals. Adjusted intervals use Bonferroni; p_holm uses Holm. They are different corrections. A small difference is not described as an effect unless its adjusted interval excludes zero.", "",
               "Cell means and floor flags are in cell_means.csv. Attempt and retry counts are in attempts_by_model_condition.csv. First-attempt sensitivity results are separate rows in estimates.csv when logs exist. Report unavailable logs and missing costs explicitly.", "",
               "No equivalence test or human-model comparison was performed. The outputs require interpretation against the reviewed condition wording. No mechanism is identified by a score difference alone.", ""]
    (args.out / "SUMMARY.md").write_text("\n".join(summary))
    print(json.dumps({"output": str(args.out), "complete": complete, "api_calls": 0}))


if __name__ == "__main__":
    main()
