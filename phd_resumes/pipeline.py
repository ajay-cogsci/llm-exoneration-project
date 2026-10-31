"""Auditable sampling and resumable, bounded API generation."""

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .api import APIError, request_body, response_json
from .io import digest, implementation_hash, read_json, read_jsonl, write_json, write_jsonl
from .provenance import source_map
from .sampling import check_config, describe, generate_cohort, validate_profile
from .writing import GENERATOR_INSTRUCTIONS, PROMPT_VERSION, REVIEW_INSTRUCTIONS, content_schema, render_cv, review_schema, validate_content


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def inspect_configuration(config):
    """Read-only build review: no RNG, files written, API client or credentials."""
    check_config(config)
    return {
        "configuration_valid": True,
        "parameter_status": config["parameter_status"],
        "planned_cohorts": len(config["seeds"]),
        "planned_pool_records": len(config["seeds"]) * (config["n_per_cohort"] + config["oversample"]),
        "planned_selected_records": len(config["seeds"]) * config["n_per_cohort"],
        "generation_model": config["generation"]["model"],
        "records_generated": 0,
        "api_calls": 0,
        "source_map": source_map(config),
    }


def sample_run(config, root):
    check_config(config)
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Output directory must be empty; choose a new run to preserve existing data")
    root.mkdir(parents=True, exist_ok=True)
    reports, all_selected, all_pool = {}, [], []
    for seed in config["seeds"]:
        pool, selected = generate_cohort(config, seed)
        errors = [(row["profile_id"], validate_profile(row)) for row in pool]
        errors = [(pid, issues) for pid, issues in errors if issues]
        if errors:
            raise ValueError(f"Invalid sampled profiles: {errors[:3]}")
        reports[str(seed)] = {"pool": describe(pool), "selected": describe(selected)}
        all_selected.extend(selected)
        all_pool.extend(pool)
    write_jsonl(root / "pool.jsonl", all_pool)
    write_jsonl(root / "profiles.jsonl", all_selected)
    write_jsonl(root / "evaluator_fields.jsonl", [row["facts"] for row in all_selected])
    write_json(root / "config.json", config)
    evidence = source_map(config)
    write_json(root / "source_map.json", evidence)
    write_json(root / "manifest.json", {"created_at": utc_now(), "implementation_hash": implementation_hash(), "config_hash": digest(config), "profiles_hash": digest(all_selected), "source_map_hash": digest(evidence), "method_reference": "https://arxiv.org/html/2509.16400v1#S3", "reference_code_revision": "5817943ef9509c49494e15408463a51cc82a034e", "profile_count": len(all_selected), "pool_count": len(all_pool), "parameter_status": config["parameter_status"], "dataset_status": "provisional_for_review"})
    write_json(root / "validation.json", {"structural_errors": [], "cohorts": reports, "empirical_phd_calibration": "not_established", "note": "Descriptive checks of the pool and selected sample, not empirical PhD validation. The admissions links do not supply joint-distribution targets. Penn admitted-only GPA means are context, not targets for the applicant pool. Provisional strength labels need human review."})
    with (root / "human_review.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        columns = ["profile_id", "reviewer", "plausible", "academic_preparation", "research_potential", "quantitative_preparation", "fit_evidence", "strength_rating", "factual_issues", "notes"]
        writer.writerow(columns)
        writer.writerows([r["profile_id"]] + [""] * (len(columns) - 1) for r in all_selected)
    # Clearly named structural previews are not presented as model-generated CVs.
    previews = root / "structured_previews"
    previews.mkdir()
    for row in balanced_subset(all_selected, min(3, len(all_selected))):
        (previews / (row["profile_id"] + ".txt")).write_text("STRUCTURED PREVIEW - API prose not generated\n\n" + render_cv(row["facts"]), encoding="utf-8")
    return {"profiles": len(all_selected), "pool": len(all_pool), "strength_counts": dict(Counter(r["strength"] for r in all_selected))}


def balanced_subset(rows, limit):
    """A small generation batch covers all strength groups when available."""
    groups = {strength: iter([r for r in rows if r["strength"] == strength]) for strength in ("weak", "borderline", "strong")}
    result = []
    while len(result) < min(limit, len(rows)):
        changed = False
        for group in groups.values():
            row = next(group, None)
            if row is not None:
                result.append(row)
                changed = True
                if len(result) == limit:
                    break
        if not changed:
            break
    return result


def cached_call(client, body, path):
    fingerprint = digest(body)
    if path.exists():
        record = read_json(path)
        if record["request_hash"] != fingerprint:
            raise ValueError("Cached request differs; use a new generation directory")
    else:
        record = {"created_at": utc_now(), "request_hash": fingerprint, "request": body, "response": client.create(body)}
        write_json(path, record)
    return response_json(record["response"]), record


def generate_run(root, client, model, review_model, limit, batch="generation"):
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not batch.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Batch must be a simple directory name")
    root = Path(root)
    config = read_json(root / "config.json")
    check_config(config)
    if not isinstance(model, str) or not model.strip() or not isinstance(review_model, str) or not review_model.strip():
        raise ValueError("Choose a generation model; optionally choose a separate review model")
    rows = read_jsonl(root / "profiles.jsonl")
    manifest = read_json(root / "manifest.json")
    if digest(config) != manifest["config_hash"] or digest(rows) != manifest["profiles_hash"]:
        raise ValueError("Sampled run has changed; create a new run instead of mixing data versions")
    if digest(read_json(root / "source_map.json")) != manifest["source_map_hash"]:
        raise ValueError("Run source mapping has changed")
    selected = balanced_subset(rows, limit)
    out = root / batch
    out.mkdir(exist_ok=True)
    contract = {"config_hash": manifest["config_hash"], "profiles_hash": manifest["profiles_hash"], "prompt_version": PROMPT_VERSION, "generator_prompt": GENERATOR_INSTRUCTIONS, "review_prompt": REVIEW_INSTRUCTIONS, "content_schema": content_schema(), "review_schema": review_schema(), "model": model, "review_model": review_model, "settings": config["generation"], "implementation_hash": implementation_hash()}
    contract_path = out / "contract.json"
    if contract_path.exists() and read_json(contract_path) != contract:
        raise ValueError("Generation configuration or implementation changed; choose a new --batch")
    write_json(contract_path, contract)
    (out / "raw").mkdir(exist_ok=True)
    (out / "cvs").mkdir(exist_ok=True)
    status = []
    for row in selected:
        pid, facts = row["profile_id"], row["facts"]
        issues = validate_profile(row)
        if issues:
            raise ValueError(f"Invalid source record {pid}: {issues}")
        try:
            body = request_body(model, GENERATOR_INSTRUCTIONS, facts, content_schema(), config["generation"])
            content, generation = cached_call(client, body, out / "raw" / f"{pid}.generation.json")
            issues = validate_content(facts, content)
            write_json(out / f"{pid}.content.json", content)
            review = None
            if not issues:
                body = request_body(review_model, REVIEW_INSTRUCTIONS, {"fixed_record": facts, "cv_entries": content}, review_schema(), config["generation"], review=True)
                review, _ = cached_call(client, body, out / "raw" / f"{pid}.review.json")
                if set(review) != {"passes", "issues"} or type(review["passes"]) is not bool or not isinstance(review["issues"], list) or any(not isinstance(i, str) for i in review["issues"]):
                    raise APIError("Reviewer returned an invalid review object")
                if review["passes"] != (not review["issues"]):
                    raise APIError("Reviewer pass flag contradicts issue list")
                issues.extend(review["issues"])
            record = {"profile_id": pid, "facts_hash": row["facts_hash"], "status": "needs_revision" if issues else "ready_for_human_review", "issues": issues, "model": generation["response"].get("model"), "review": review}
            if not issues:
                cv = render_cv(facts, content)
                (out / "cvs" / f"{pid}.txt").write_text(cv, encoding="utf-8")
                record["cv_hash"] = digest(cv)
            write_json(out / f"{pid}.status.json", record)
            status.append(record)
            print(f"{pid}: {record['status']}", flush=True)
        except APIError as exc:
            record = {"profile_id": pid, "facts_hash": row["facts_hash"], "status": "api_error", "issues": [str(exc)]}
            write_json(out / f"{pid}.status.json", record)
            status.append(record)
            write_summary(out, status)
            raise
    return write_summary(out, status)


def write_summary(out, status):
    usage = Counter()
    for path in (out / "raw").glob("*.json"):
        response = read_json(path)["response"]
        reported_usage = response.get("usage") if isinstance(response, dict) else None
        if not isinstance(reported_usage, dict):
            continue
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = reported_usage.get(key)
            if type(value) is int and value >= 0:
                usage[key] += value
    summary = {"updated_at": utc_now(), "selected_in_this_invocation": len(status), "status_counts": dict(Counter(r["status"] for r in status)), "usage_all_cached_responses_in_batch": dict(usage), "profiles": status, "note": "Automated checks do not replace human review. Cached raw responses are reused; changing a request requires a new batch."}
    write_json(out / "summary.json", summary)
    return summary
