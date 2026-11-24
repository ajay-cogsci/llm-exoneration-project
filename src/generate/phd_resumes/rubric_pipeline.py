"""Versioned rubric sampling and read-only audits of historical applicant facts.

This module has no API client. Future CV wording uses the existing generate
command only after an explicitly allocated new sample has been saved.
"""

import csv
import hashlib
import math
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path

from .io import digest, implementation_hash, read_json, read_jsonl, write_json, write_jsonl
from .provenance import source_map
from .rubric import PATTERNS, TIERS, check_rubric, evaluate, number, summarize
from .sampling import check_config, make_profile, percentile_ranks, quintiles, standardized, validate_profile


def check_sampling(policy, config):
    check_config(config)
    digest(policy)
    if policy.get("version") != "phd-conditional-v3":
        raise ValueError("Unsupported conditional sampler version")
    if type(policy["pool_per_cohort"]) is not int or policy["pool_per_cohort"] < 10:
        raise ValueError("Pool size must be an integer >= 10")
    for key, width in (("academic_given_research_probabilities", 5), ("gpa_bin_probabilities_by_academic_level", len(config["gpa_bins"]))):
        matrix = policy[key]
        if len(matrix) != 5 or any(len(row) != width or any(not number(p) or p < 0 for p in row) or not math.isclose(sum(row), 1) for row in matrix):
            raise ValueError(f"Invalid conditional probability matrix: {key}")
    check_allocation(policy["allocation"])


def check_allocation(allocation):
    if allocation is None:
        return
    if not isinstance(allocation, dict) or set(allocation) != {"seed", "cells"}:
        raise ValueError("Allocation must contain seed and cells")
    if type(allocation["seed"]) is not int or allocation["seed"] < 0 or not isinstance(allocation["cells"], list) or not allocation["cells"]:
        raise ValueError("Allocation requires a nonnegative seed and explicit cells")
    seen, total = set(), 0
    for cell in allocation["cells"]:
        if not isinstance(cell, dict) or set(cell) != {"tier", "pattern", "count"}:
            raise ValueError("Allocation cells require tier, pattern, count")
        key = (cell["tier"], cell["pattern"])
        if set(cell) != {"tier", "pattern", "count"} or cell["tier"] not in TIERS or cell["pattern"] not in PATTERNS or type(cell["count"]) is not int or cell["count"] < 0 or key in seen:
            raise ValueError("Invalid/duplicate allocation cell")
        seen.add(key)
        total += cell["count"]
    if total <= 0:
        raise ValueError("Allocation must request at least one profile")


def revision_provenance(config, rubric, sampling):
    return {
        "legacy_base": source_map(config),
        "rubric": {"version": rubric["version"], "policy": rubric, "basis": "Study operationalization of observable academic and research dimensions in Brandeis and UW; not their exact rubric, not a CS/ML admissions threshold.", "numeric_thresholds": "All GPA, duration, exposure, contribution-duration and mixed-profile boundaries are provisional study choices. No threshold is derived from Penn admitted means.", "tier_table": "Explicit study decision rules, independent of cohort composition and quotas.", "not_scored": "Publications are reported as evidence only; venue prestige, work domain, projects, letters, fit and character do not add points."},
        "sampling": {"policy": sampling, "basis": "Conditional structured sampling and inverse-frequency sampling without replacement follow the paper's pattern. Academic/research separation and exact tier/pattern allocation are PhD experimental adaptations.", "parameter_families": {"pool_per_cohort": "Engineering pool capacity, not population size.", "academic_given_research_probabilities": "Provisional five-by-five conditional table; nonzero off-diagonal support permits mixed preparation.", "gpa_bin_probabilities_by_academic_level": "Provisional conditional GPA masses; no longer preserves the legacy unconditional GPA marginal.", "allocation": "User-set counts by fixed tier and mutually exclusive pattern. Null until chosen. No empirical frequency interpretation."}},
        "base_settings_reused": ["seeds", "pathways", "research_areas", "preparation_probabilities (research level only)", "research duration/contribution/output/internship/work/project conditional settings", "coursework patterns (academic level only)", "GPA bin boundaries", "dates", "generation settings"],
        "base_settings_superseded": ["n_per_cohort", "oversample", "gpa_latent_rank_coefficient", "gpa_bin_probabilities", "subsample_cells", "strength_by_quintile (diagnostic only)"],
        "remaining_limitations": ["Uncalibrated PhD joint distribution.", "Research duration, contribution and output probabilities remain coupled to a research preparation level.", "Course grades still use five templates; difficulty and full transcripts are absent.", "No invented evidence for faculty fit, motivation, letters or essays.", "Same-model wording review is not independent human validation; technical prose can still affect perceived merit.", "Exact allocation can distort marginals/correlations; inspect the pool and selection separately."],
    }


def inspect_revision(config, rubric, sampling):
    check_sampling(sampling, config)
    check_rubric(rubric)
    return {"valid": True, "api_calls": 0, "records_generated": 0, "allocation": sampling["allocation"], "planned_pool": sampling["pool_per_cohort"] * len(config["seeds"]), "provenance": revision_provenance(config, rubric, sampling)}


def make_pool(config, rubric, sampling, seed):
    check_sampling(sampling, config)
    check_rubric(rubric)
    # Domain-separated streams: changing coursework draws cannot replay the
    # selection stream or change research chronology through RNG consumption.
    research_rng = random.Random(f"phd-v3-research:{seed}")
    academic_rng = random.Random(f"phd-v3-academic:{seed}")
    profile_rng = random.Random(f"phd-v3-profile:{seed}")
    pool = []
    for index in range(sampling["pool_per_cohort"]):
        research_level = research_rng.choices(range(1, 6), config["preparation_probabilities"])[0]
        academic_level = academic_rng.choices(range(1, 6), sampling["academic_given_research_probabilities"][research_level-1])[0]
        gpa_bin = academic_rng.choices(config["gpa_bins"], sampling["gpa_bin_probabilities_by_academic_level"][academic_level-1])[0]
        gpa = round(academic_rng.uniform(*gpa_bin), 2)
        row = make_profile(config, profile_rng, seed, index, research_level, gpa)
        row["facts"]["coursework"] = deepcopy(config["coursework_by_preparation"][academic_level-1])
        # A new namespace prevents accidental cache reuse against legacy IDs.
        row["profile_id"] = row["facts"]["applicant_id"] = f"PHDv3-{seed}-{index:05d}"
        row["latent_research_level"] = row.pop("latent_preparation_quintile")
        row["latent_academic_level"] = academic_level
        row["facts_hash"] = digest(row["facts"])
        issues = validate_profile(row)
        if issues:
            raise ValueError(f"Invalid v3 record {row['profile_id']}: {issues}")
        row["rubric"] = evaluate(row["facts"], rubric)
        if row["rubric"]["tier"] == "unrated":
            raise ValueError(f"Unrated generated record: {row['rubric']['issues']}")
        row["strength"] = row["rubric"]["tier"]
        row["strength_status"] = "provisional_cv_rubric_pending_human_review"
        pool.append(row)
    # Preserve the old composite calculation only as a diagnostic, never as
    # the label or selection criterion of a new run.
    scaled = {k: (percentile_ranks if config["performance_normalization"][k] == "percentile" else standardized)([row["features"][k] for row in pool]) for k in config["performance_weights"]}
    scores = [sum(config["performance_weights"][k] * scaled[k][i] for k in scaled) for i in range(len(pool))]
    for row, score, quintile in zip(pool, scores, quintiles(scores)):
        row["legacy_diagnostic"] = {"performance_index": round(score, 8), "perf_quintile": quintile, "strength": config["strength_by_quintile"][str(quintile)]}
    return pool


def select_allocated(pool, rubric, allocation):
    check_allocation(allocation)
    if allocation is None:
        raise ValueError("Allocation is unset. Choose tier/pattern counts before creating a replacement sample.")
    if len({row["profile_id"] for row in pool}) != len(pool):
        raise ValueError("Duplicate source profile IDs")
    buckets = {}
    for row in pool:
        rating = evaluate(row["facts"], rubric)
        if row["facts_hash"] != digest(row["facts"]) or row["rubric"] != rating or row["strength"] != rating["tier"]:
            raise ValueError("Pool facts or rubric metadata changed")
        buckets.setdefault((rating["tier"], rating["selection_pattern"]), []).append(row)
    shortages = []
    for cell in allocation["cells"]:
        available = len(buckets.get((cell["tier"], cell["pattern"]), []))
        if available < cell["count"]:
            shortages.append({**cell, "available": available})
    if shortages:
        raise ValueError(f"Insufficient pool support; do not relabel to meet quotas: {shortages}")
    selected = []
    for cell in sorted(allocation["cells"], key=lambda c: (c["tier"], c["pattern"])):
        candidates = sorted(buckets.get((cell["tier"], cell["pattern"]), []), key=lambda row: row["profile_id"])
        # Within each allocated tier/pattern, improve pathway coverage using
        # the paper's inverse-frequency exponential race without replacement.
        counts = Counter(row["pathway"] for row in candidates)
        rng = random.Random(f"phd-v3-selection:{allocation['seed']}:{cell['tier']}:{cell['pattern']}")
        ranked = sorted(candidates, key=lambda row: -math.log(max(rng.random(), 1e-300)) * counts[row["pathway"]])
        selected.extend(ranked[:cell["count"]])
    return sorted(selected, key=lambda row: row["profile_id"])


def empty_output(root):
    root = Path(root)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("Output must be a new or empty directory; existing data are preserved")
    return root


def sample_revision(config, rubric, sampling, root):
    inspect_revision(config, rubric, sampling)
    if sampling["allocation"] is None:
        raise ValueError("Allocation is unset; no replacement sample created")
    root = empty_output(root)
    pool = [row for seed in config["seeds"] for row in make_pool(config, rubric, sampling, seed)]
    selected = select_allocated(pool, rubric, sampling["allocation"])
    evidence = revision_provenance(config, rubric, sampling)
    root.mkdir(parents=True, exist_ok=True)
    for filename, value in (("config.json", config), ("rubric.json", rubric), ("sampling_policy.json", sampling), ("source_map.json", evidence)):
        write_json(root / filename, value)
    write_jsonl(root / "pool.jsonl", pool)
    write_jsonl(root / "profiles.jsonl", selected)
    write_jsonl(root / "evaluator_fields.jsonl", [row["facts"] for row in selected])
    write_json(root / "manifest.json", {"dataset_version": sampling["version"], "dataset_status": "provisional_pending_human_review", "implementation_hash": implementation_hash(), "config_hash": digest(config), "profiles_hash": digest(selected), "source_map_hash": digest(evidence), "policy_hashes": {"rubric.json": digest(rubric), "sampling_policy.json": digest(sampling)}, "profile_count": len(selected), "pool_count": len(pool)})
    report = {"pool": summarize(pool, rubric), "selected": summarize(selected, rubric), "api_calls": 0, "human_review": "pending", "empirical_calibration": "not_established"}
    write_json(root / "validation.json", report)
    return report


def tree_hash(root):
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}
    return {"file_count": len(files), "sha256_of_path_content_hashes": digest(files)}


def sensitivity(rows, rubric):
    baseline = [evaluate(row["facts"], rubric)["tier"] for row in rows]
    cases = []
    # One-at-a-time scenarios, not confidence intervals or empirical validation.
    for section, key, values in (("academic", "high_gpa_min", (3.4, 3.6)), ("academic", "adequate_gpa_min", (2.9, 3.1)), ("research", "high_months_min", (15, 24)), ("research", "high_fte_months_min", (3.5, 6)), ("research", "high_intellectual_months_min", (6, 12)), ("research", "adequate_months_min", (3, 9))):
        for value in values:
            variant = deepcopy(rubric)
            variant[section][key] = value
            tiers = [evaluate(row["facts"], variant)["tier"] for row in rows]
            cases.append({"parameter": f"{section}.{key}", "value": value, "changed": sum(a != b for a, b in zip(baseline, tiers)), "transitions": dict(Counter(f"{a}:{b}" for a, b in zip(baseline, tiers) if a != b)), "tiers": dict(Counter(tiers))})
    return cases


def audit_existing(source, root, config, rubric, sampling):
    """Audit the packaged original sample; write sidecars and a blind review pack.

    No replacement sample or new model-generated prose is created. Simulated
    pools are used only for coverage diagnostics, then discarded.
    """
    inspect_revision(config, rubric, sampling)
    source, root = Path(source).resolve(), empty_output(root).resolve()
    if root == source or source in root.parents:
        raise ValueError("Audit output must be outside the original sample")
    before = tree_hash(source)
    rows = read_jsonl(source / "profiles.jsonl")
    pool = [row for path in sorted((source / "cohorts").glob("*/pool.jsonl")) for row in read_jsonl(path)]
    if not rows or not pool or len({r["profile_id"] for r in pool}) != len(pool) or len({r["profile_id"] for r in rows}) != len(rows):
        raise ValueError("Source pool/selected records must exist with unique IDs")
    by_id = {r["profile_id"]: r for r in pool}
    for row in pool + rows:
        issues = validate_profile(row)
        if issues:
            raise ValueError(f"Source validation failed: {row['profile_id']}: {issues}")
    if any(row != by_id.get(row["profile_id"]) for row in rows):
        raise ValueError("Selected records differ from the original source pool")
    manifests = read_json(source / "resume_manifest.json")
    if len(manifests) != len(rows) or {m["profile_id"] for m in manifests} != {r["profile_id"] for r in rows}:
        raise ValueError("Resume manifest does not match selected IDs")
    texts = {}
    for item in manifests:
        cv_path = (source / item["resume"]).resolve()
        content_path = (source / item["content_source"]).resolve()
        if source not in cv_path.parents or source not in content_path.parents:
            raise ValueError("Manifest paths must stay inside the sample")
        text = cv_path.read_text(encoding="utf-8")
        row = by_id[item["profile_id"]]
        # Verify potential reuse: exact same fixed facts and rendered prose.
        from .writing import render_cv, validate_content
        content = read_json(content_path)
        if item["facts_hash"] != row["facts_hash"] or digest(text) != item["cv_hash"] or validate_content(row["facts"], content) or render_cv(row["facts"], content) != text:
            raise ValueError(f"Source CV/content mismatch: {item['profile_id']}")
        texts[item["profile_id"]] = text
    sidecars = [{"profile_id": row["profile_id"], "old_strength": row["strength"], "legacy_diagnostic": {k: row[k] for k in ("performance_index", "perf_quintile")}, "retained_in_original_100": row["profile_id"] in texts, "rubric": evaluate(row["facts"], rubric)} for row in pool]
    # Software coverage check only. No experimental sample is retained.
    simulated = [row for seed in config["seeds"] for row in make_pool(config, rubric, sampling, seed)]
    coverage = summarize(simulated, rubric)
    coverage["latent_academic_by_research"] = dict(Counter(f"{r['latent_academic_level']}:{r['latent_research_level']}" for r in simulated))
    coverage["purpose"] = "Discarded synthetic fixtures for software coverage, not a replacement sample, empirical target or model-generated CVs."
    report = {"status": "automated_audit_complete_human_review_pending", "api_calls": 0, "replacement_sample_generated": False, "implementation_hash": implementation_hash(), "rubric_hash": digest(rubric), "sampling_policy_hash": digest(sampling), "original_selected": summarize(rows, rubric), "original_pool": summarize(pool, rubric), "cv_content_reuse_verified": len(texts), "reuse_limit": "Exact facts/prose fidelity verified; human agreement with the proposed rubric and wording merit remains untested.", "sensitivity_original_100": sensitivity(rows, rubric), "sampler_coverage": coverage, "source_tree_before": before}
    after = tree_hash(source)
    if before != after:
        raise ValueError("Original sample changed during audit")
    report["source_tree_after"] = after
    report["original_files_unchanged"] = True
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "rubric.json", rubric)
    write_json(root / "sampling_policy.json", sampling)
    write_json(root / "base_config.json", config)
    write_json(root / "source_map.json", revision_provenance(config, rubric, sampling))
    write_jsonl(root / "proposed_labels.jsonl", sidecars)
    # Reviewers see randomized neutral identifiers and the existing prose.
    # The administrative mapping and proposed labels stay outside this folder.
    ordered = sorted(rows, key=lambda row: row["profile_id"])
    random.Random("phd-rubric-v1-blind-review").shuffle(ordered)
    review_dir = root / "blind_review"
    review_dir.mkdir()
    mapping = []
    with (review_dir / "ratings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        columns = ["review_id", "reviewer", "academic_rating", "research_rating", "overall_tier", "plausible", "confidence", "prose_inflates_evidence", "notes"]
        writer.writerow(columns)
        for i, row in enumerate(ordered, 1):
            review_id = f"REVIEW-{i:03d}"
            (review_dir / f"{review_id}.txt").write_text(texts[row["profile_id"]].replace(row["profile_id"], review_id), encoding="utf-8")
            writer.writerow([review_id] + [""] * (len(columns)-1))
            mapping.append({"review_id": review_id, "profile_id": row["profile_id"]})
    (review_dir / "README.txt").write_text("BLIND HUMAN REVIEW - NOT COMPLETED\n\nReview the randomized existing CVs for the generic research CS PhD opportunity.\nRate academics and research as low/adequate/high/unrated, then overall weak/borderline/strong/unrated. Record plausibility, confidence, contradictions and any prose that exaggerates fixed evidence. Do not infer missing letters, essays, faculty fit, course rigor, or motivation. Use independent judgment before comparing with the proposed rule labels.\n\nShare only this folder with reviewers; the parent contains the administrative mapping and proposed labels. This masks assigned labels and original IDs, not observable credentials or familiarity with the old sample. A second reviewer and adjudication of disagreements are recommended.\n", encoding="utf-8")
    write_json(root / "reviewer_id_mapping.json", mapping)
    write_json(root / "report.json", report)
    changed = sum(item["old_strength"] != item["rubric"]["tier"] for item in sidecars if item["retained_in_original_100"])
    transitions = report["original_selected"]["old_to_rubric"]
    lines = ["# Rubric revision audit", "", "Offline audit of the existing sample; no API calls or replacement sample. Proposed labels have not replaced the historical labels. Human review is pending.", "", "## Original CVs under the proposed rubric", "", "| Old label | New weak | New borderline | New strong |", "| --- | ---: | ---: | ---: |"]
    for tier in TIERS:
        lines.append("| " + tier + " | " + " | ".join(str(transitions.get(f"{tier}:{new}", 0)) for new in TIERS) + " |")
    lines.extend(["", f"{changed}/{len(rows)} proposed labels differ. New totals: {report['original_selected']['tiers']}. Source-pool totals: {report['original_pool']['tiers']}.", "", f"All {len(texts)} original CVs match their stored hashes and render exactly from their existing facts/content. All {before['file_count']} source files were unchanged. This supports reusing their wording if their facts are retained, not approval of their merit labels.", "", "## Coverage and threshold sensitivity", "", f"The original pool has {report['original_pool']['academic_by_research'].get('high:low', 0)} high-academic/low-research profiles. Discarded local coverage fixtures contain {coverage['academic_by_research'].get('high:low', 0)} of that combination among {coverage['n']} records. The fixture distribution is an input assumption, not evidence about real applicants.", "", "| Parameter changed alone | Alternative | Existing CV labels changed |", "| --- | ---: | ---: |"])
    for case in report["sensitivity_original_100"]:
        lines.append(f"| {case['parameter']} | {case['value']} | {case['changed']} |")
    lines.extend(["", "Threshold sensitivity is a robustness diagnostic, not an instruction to tune thresholds until desired sample counts appear. Choose counts separately after reviewing the rubric.", "", "## Review next", "", "Share only `blind_review/` for independent ratings. It contains the existing CV prose with randomized IDs and an empty ratings form. Keep `reviewer_id_mapping.json` and `proposed_labels.jsonl` away from blinded reviewers. No reviewer has rated these materials yet.", "", "The sources motivate academic/research dimensions, but the GPA/time thresholds and decision table are provisional. Course rigor, thesis equivalence, faculty fit, recommendations and motivation cannot be assessed here. Publications no longer set a tier, but the rubric still deliberately gives substantive research a central role. The existing prose may influence judgments beyond structured credentials.", "", "See `report.json` for complete cells, tier descriptives, correlations, sensitivity results and hashes; `source_map.json` records method transfers and assumptions.", ""])
    (root / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return report
