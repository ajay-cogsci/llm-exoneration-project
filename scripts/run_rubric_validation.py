"""Bounded live-run orchestration for the revised PhD sampler.

Uses the existing sampler and generator. Three disjoint processing shards enable
concurrency; they are not new sampling cohorts or independently selected samples.
All selected facts are frozen before any model call. Repairs change wording only.
"""

import argparse
import csv
import hashlib
import html
import json
import random
import shutil
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from phd_resumes.api import APIError, OpenAIResponses, request_body, response_json
from phd_resumes.io import digest, implementation_hash, read_json, read_jsonl, write_json, write_jsonl
from phd_resumes.pipeline import balanced_subset, cached_call, generate_run, utc_now
from phd_resumes.rubric import evaluate, summarize
from phd_resumes.rubric_pipeline import make_pool, sample_revision, select_allocated, tree_hash
from phd_resumes.sampling import validate_profile
from phd_resumes.writing import GENERATOR_INSTRUCTIONS, REVIEW_INSTRUCTIONS, content_schema, render_cv, review_schema, validate_content

MODEL = "gpt-6-astra"
MAX_REPAIRS = 3
REPAIR_INSTRUCTIONS = GENERATOR_INSTRUCTIONS + """
Revise the supplied previous_entries to resolve the listed validation_issues.
The fixed_record remains authoritative and must not be changed. Preserve
unaffected content where possible. Return the complete revised entry object.
Do not use digits in titles or bullets, including metric or method names;
use words such as F score instead. Do not use the word integrity, even for data
or database descriptions. Check that each bullet has twelve to thirty words.
Do not add credentials, outputs, skills, responsibility, or numerical achievements.
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def runner_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def prepare(root, weak, borderline, strong):
    require(weak + borderline + strong == 100 and weak >= 0 and borderline >= 5 and strong >= 5, "Allocation must total 100 and support ten mixed profiles")
    cfg = read_json(PROJECT / "configs/phd.json")
    cfg["generation"].update(model=MODEL, review_model=MODEL)
    rubric = read_json(PROJECT / "configs/phd_rubric_v1.json")
    sampling = read_json(PROJECT / "configs/phd_sampling_v3.json")
    sampling["status"] = "User-authorized validation run; quotas are experimental design choices, not applicant population frequencies."
    sampling["allocation"] = {"seed": 20261111, "cells": [
        {"tier": "weak", "pattern": "none", "count": weak},
        {"tier": "borderline", "pattern": "none", "count": borderline - 5},
        {"tier": "strong", "pattern": "none", "count": strong - 5},
        {"tier": "strong", "pattern": "lower_gpa_strong_research", "count": 3},
        {"tier": "borderline", "pattern": "high_academics_limited_research", "count": 3},
        {"tier": "borderline", "pattern": "academic_gaps_strong_research", "count": 2},
        {"tier": "strong", "pattern": "strong_research_without_publications", "count": 2},
    ]}
    original_tree = tree_hash(PROJECT / "sample-100-resume-generated")
    report = sample_revision(cfg, rubric, sampling, root)
    rows = read_jsonl(root / "profiles.jsonl")
    manifest = read_json(root / "manifest.json")
    shards = []
    ordered = balanced_subset(rows, len(rows))
    for i in range(3):
        directory = root / "shards" / f"part-{i+1}"
        directory.mkdir(parents=True)
        subset = ordered[i::3]
        for name in ("config.json", "rubric.json", "sampling_policy.json", "source_map.json"):
            shutil.copyfile(root / name, directory / name)
        write_jsonl(directory / "profiles.jsonl", subset)
        write_json(directory / "manifest.json", {**manifest, "profiles_hash": digest(subset), "profile_count": len(subset), "parent_profiles_hash": manifest["profiles_hash"], "partition_only": True})
        shards.append({"path": str(directory.relative_to(root)), "profiles": len(subset), "profiles_hash": digest(subset)})
    snapshot = root / "audit" / "implementation-used" / "phd_resumes"
    snapshot.mkdir(parents=True)
    for path in (PROJECT / "phd_resumes").glob("*.py"):
        shutil.copyfile(path, snapshot / path.name)
    shutil.copyfile(__file__, snapshot.parent / "run_rubric_validation.py")
    write_json(root / "run_plan.json", {
        "created_at": utc_now(), "purpose": "Authorized 100-CV validation of the revised PhD rubric/sampler", "model": MODEL, "review_model": MODEL,
        "model_source": "https://developers.openai.com/api/docs/models/gpt-6-astra", "model_access_verified": True,
        "implementation_hash": implementation_hash(), "runner_hash": runner_hash(),
        "expected_profiles": 100, "expected_pool": report["pool"]["n"], "max_parallel_shards": 3, "max_repair_attempts": MAX_REPAIRS,
        "repair_instructions": REPAIR_INSTRUCTIONS, "allocation": sampling["allocation"], "shards": shards,
        "original_sample_tree": original_tree, "human_review_completed": False,
        "limits": ["Provisional rubric and joint distribution; no admissions calibration", "Same-model review is not independent human validation", "Rubric/mixed tags never enter model inputs or CVs", "No source facts or selected profiles may change during repairs"]})
    print(json.dumps({"prepared": 100, "tiers": report["selected"]["tiers"], "mixed_patterns": report["selected"]["selection_cells"]}, indent=2))


def load_run(root):
    plan, manifest = read_json(root / "run_plan.json"), read_json(root / "manifest.json")
    require(plan["implementation_hash"] == implementation_hash() == manifest["implementation_hash"], "Pipeline changed after preparation")
    require(plan["runner_hash"] == runner_hash(), "Run helper changed after preparation")
    require(digest(read_json(root / "config.json")) == manifest["config_hash"], "Config changed")
    require(digest(read_json(root / "source_map.json")) == manifest["source_map_hash"], "Provenance changed")
    for name, fingerprint in manifest["policy_hashes"].items():
        require(digest(read_json(root / name)) == fingerprint, "Rubric/sampling policy changed")
    rows = read_jsonl(root / "profiles.jsonl")
    require(digest(rows) == manifest["profiles_hash"], "Selected facts/labels changed")
    records = []
    for shard in plan["shards"]:
        directory = root / shard["path"]
        subset = read_jsonl(directory / "profiles.jsonl")
        require(digest(subset) == shard["profiles_hash"], "Shard changed")
        require(read_json(directory / "manifest.json")["parent_profiles_hash"] == manifest["profiles_hash"], "Shard parent changed")
        for name in ("config.json", "rubric.json", "sampling_policy.json", "source_map.json"):
            require(read_json(directory / name) == read_json(root / name), "Shard policy/config mismatch")
        records.extend((directory, row) for row in subset)
    require(len(records) == len(rows) and sorted((r for _, r in records), key=lambda r: r["profile_id"]) == sorted(rows, key=lambda r: r["profile_id"]), "Shards do not exactly partition the selected sample")
    return plan, rows, records


class StoppableClient(OpenAIResponses):
    def __init__(self, root):
        super().__init__()
        self.root = root

    def create(self, body):
        if (self.root / "STOP").exists():
            raise APIError("Run stopped before next model call")
        return super().create(body)


def generate(root, pilot=False):
    plan, _, _ = load_run(root)
    results, failures = {}, {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = {executor.submit(generate_run, root / shard["path"], StoppableClient(root), plan["model"], plan["review_model"], 1 if pilot else shard["profiles"]): shard["path"] for shard in plan["shards"]}
        for job in as_completed(jobs):
            name = jobs[job]
            try:
                result = job.result()
                results[name] = {"status_counts": result["status_counts"], "usage": result["usage_all_cached_responses_in_batch"]}
            except Exception as exc:
                failures[name] = {"type": type(exc).__name__, "message": str(exc)}
    output = {"updated_at": utc_now(), "shards": results, "failed_shards": failures}
    write_json(root / ("pilot_result.json" if pilot else "first_pass_result.json"), output)
    print(json.dumps(output, indent=2), flush=True)
    require(not failures, "Model errors retained; inspect before resuming")


def valid_review(review):
    require(isinstance(review, dict) and set(review) == {"passes", "issues"} and type(review["passes"]) is bool and isinstance(review["issues"], list) and all(isinstance(i, str) for i in review["issues"]) and review["passes"] == (not review["issues"]), "Invalid reviewer result")
    return review


def repair_one(root, directory, row, client):
    pid, facts = row["profile_id"], row["facts"]
    require(not validate_profile(row), "Invalid fixed facts")
    first = read_json(directory / "generation" / f"{pid}.status.json")
    if first["status"] == "ready_for_human_review":
        return {"profile_id": pid, "repair_attempts": 0, "status": first["status"]}
    require(first["status"] == "needs_revision", "Resolve API errors before wording repair")
    previous = read_json(directory / "generation" / f"{pid}.content.json")
    issues, settings = first["issues"], read_json(root / "config.json")["generation"]
    out, attempts = root / "repairs" / pid, []
    for attempt in range(1, MAX_REPAIRS + 1):
        stage = out / f"attempt-{attempt}"
        payload = {"fixed_record": facts, "previous_entries": previous, "validation_issues": issues}
        body = request_body(settings["model"], REPAIR_INSTRUCTIONS, payload, content_schema(), settings)
        content, raw = cached_call(client, body, stage / "raw" / "generation.json")
        write_json(stage / "content.json", content)
        issues, review = validate_content(facts, content), None
        if not issues:
            body = request_body(settings["review_model"], REVIEW_INSTRUCTIONS, {"fixed_record": facts, "cv_entries": content}, review_schema(), settings, review=True)
            review, _ = cached_call(client, body, stage / "raw" / "review.json")
            valid_review(review)
            issues.extend(review["issues"])
        status = {"profile_id": pid, "facts_hash": row["facts_hash"], "attempt": attempt, "issues": issues, "review": review, "model": raw["response"].get("model"), "status": "needs_revision" if issues else "ready_for_human_review"}
        write_json(stage / "status.json", status)
        attempts.append(status)
        if not issues:
            cv = render_cv(facts, content)
            (out / "cv.txt").write_text(cv, encoding="utf-8")
            write_json(out / "content.json", content)
            write_json(out / "status.json", {**status, "repair_attempts": attempt, "cv_hash": digest(cv), "attempts": attempts})
            print(f"Repaired {pid}: attempt {attempt}", flush=True)
            return {"profile_id": pid, "repair_attempts": attempt, "status": status["status"]}
        previous = content
    write_json(out / "status.json", {**status, "repair_attempts": MAX_REPAIRS, "attempts": attempts})
    return {"profile_id": pid, "repair_attempts": MAX_REPAIRS, "status": "needs_revision"}


def repair(root):
    _, _, records = load_run(root)
    pending = [(directory, row) for directory, row in records if read_json(directory / "generation" / f"{row['profile_id']}.status.json")["status"] != "ready_for_human_review"]
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = [executor.submit(repair_one, root, directory, row, StoppableClient(root)) for directory, row in pending]
        for job in as_completed(jobs):
            results.append(job.result())
    write_json(root / "repair_result.json", {"updated_at": utc_now(), "profiles": results})
    require(all(r["status"] == "ready_for_human_review" for r in results), "Repair limit reached; rejected records retained and no replacements sampled")


def verify_raw(path, facts, content, review=False):
    raw = read_json(path)
    require(digest(raw["request"]) == raw["request_hash"], "Raw request hash mismatch")
    payload = json.loads(raw["request"]["input"][1]["content"])
    require(payload.get("fixed_record", payload) == facts, "Raw request uses different fixed facts")
    if review:
        require(payload["cv_entries"] == content, "Review examined different prose")
        require(valid_review(response_json(raw["response"]))["passes"], "Final review failed")
    else:
        require(response_json(raw["response"]) == content, "Raw generation differs from saved prose")


def package(root):
    plan, rows, records = load_run(root)
    cfg, rubric, sampling = (read_json(root / name) for name in ("config.json", "rubric.json", "sampling_policy.json"))
    pool = [row for seed in cfg["seeds"] for row in make_pool(cfg, rubric, sampling, seed)]
    require(pool == read_jsonl(root / "pool.jsonl"), "Pool reproduction failed")
    require(select_allocated(pool, rubric, sampling["allocation"]) == rows, "Selection reproduction failed")
    require(read_jsonl(root / "evaluator_fields.jsonl") == [row["facts"] for row in rows], "Evaluator facts changed")
    accepted, statuses, content_hashes = [], [], []
    for directory, row in records:
        pid = row["profile_id"]
        require(not validate_profile(row) and evaluate(row["facts"], rubric) == row["rubric"], "Facts or rubric label invalid")
        first = read_json(directory / "generation" / f"{pid}.status.json")
        statuses.append(first)
        status, attempts = first, 0
        base = directory / "generation"
        content_path, cv_path = base / f"{pid}.content.json", base / "cvs" / f"{pid}.txt"
        generation_raw, review_raw = base / "raw" / f"{pid}.generation.json", base / "raw" / f"{pid}.review.json"
        if first["status"] != "ready_for_human_review":
            base = root / "repairs" / pid
            status = read_json(base / "status.json")
            attempts = status["repair_attempts"]
            content_path, cv_path = base / "content.json", base / "cv.txt"
            generation_raw, review_raw = base / f"attempt-{attempts}" / "raw" / "generation.json", base / f"attempt-{attempts}" / "raw" / "review.json"
        require(status["status"] == "ready_for_human_review", f"Rejected applicant still unresolved: {pid}")
        content = read_json(content_path)
        require(not validate_content(row["facts"], content) and valid_review(status["review"])["passes"], f"Final prose/review failed: {pid}")
        require(status["facts_hash"] == row["facts_hash"], "Status uses different facts")
        cv = render_cv(row["facts"], content)
        require(cv == cv_path.read_text(encoding="utf-8") and digest(cv) == status["cv_hash"], "CV render/hash mismatch")
        verify_raw(generation_raw, row["facts"], content)
        verify_raw(review_raw, row["facts"], content, review=True)
        content_hashes.append(digest(content))
        accepted.append({"profile_id": pid, "facts_hash": row["facts_hash"], "cv_hash": digest(cv), "repair_attempts": attempts, "content_source": str(content_path.relative_to(root)), "source": str(cv_path.relative_to(root)), "resume": f"resumes/{pid}.txt", "cv": cv})
    require(len(accepted) == plan["expected_profiles"] == len({item["profile_id"] for item in accepted}), "Final count/uniqueness failure")
    require(tree_hash(PROJECT / "sample-100-resume-generated") == plan["original_sample_tree"], "Historical sample changed")
    final = root / "resumes"
    final.mkdir(exist_ok=True)
    accepted.sort(key=lambda item: item["profile_id"])
    for item in accepted:
        (root / item["resume"]).write_text(item["cv"], encoding="utf-8")
    require(len(list(final.glob("*.txt"))) == 100, "Unexpected exported CV count")
    write_json(root / "resume_manifest.json", [{k: v for k, v in item.items() if k != "cv"} for item in accepted])
    usage, models, ids = Counter(), Counter(), set()
    for path in root.glob("**/raw/*.json"):
        response = read_json(path)["response"]
        require(response.get("id"), "Saved response lacks ID")
        if response["id"] in ids:
            continue
        ids.add(response["id"])
        models[response.get("model", "unknown")] += 1
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            require(type(response.get("usage", {}).get(key)) is int, "Response usage missing; cannot report a complete saved-response total")
            usage[key] += response["usage"][key]
    summary = {"created_at": utc_now(), "resume_count": 100, "first_pass_status_counts": dict(Counter(s["status"] for s in statuses)), "first_pass_issues": dict(Counter(issue for s in statuses for issue in s["issues"])), "repaired_profiles": sum(item["repair_attempts"] > 0 for item in accepted), "total_repair_attempts": sum(item["repair_attempts"] for item in accepted), "unique_prose_objects": len(set(content_hashes)), "rubric_version": rubric["version"], "sampling_version": sampling["version"], "selected_distribution": summarize(rows, rubric), "unique_saved_api_responses": len(ids), "response_models": dict(models), "reported_token_usage": dict(usage), "usage_limit": "Usage of saved responses, deduplicated by ID. Actual billing may include any server-side calls without a saved response.", "checks": {"pool_and_selection_reproduced": True, "facts_and_rubric_labels_valid": True, "raw_requests_responses_match_final_facts_and_prose": True, "final_model_reviews_passed": True, "exact_render_and_hashes_match": True, "original_sample_unchanged": True}, "human_review_completed": False, "empirical_phd_calibration": "not_established", "limit": "Automated factual checks do not establish human agreement with strength labels or preservation of perceived merit by invented prose."}
    write_json(root / "validation_summary.json", summary)
    build_review_pack(root, rows, accepted)
    build_index(root, rows, accepted, summary)
    print(json.dumps({k: summary[k] for k in ("resume_count", "first_pass_status_counts", "repaired_profiles", "total_repair_attempts", "unique_saved_api_responses", "reported_token_usage")}, indent=2))


def build_review_pack(root, rows, accepted):
    review = root / "blind_review"
    review.mkdir(exist_ok=True)
    shuffled = list(accepted)
    random.Random("phd-v2-rubric-blind-review").shuffle(shuffled)
    mapping = []
    with (review / "ratings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        columns = ["review_id", "reviewer", "academic_rating", "research_rating", "overall_tier", "plausible", "confidence", "prose_inflates_evidence", "notes"]
        writer.writerow(columns)
        for i, item in enumerate(shuffled, 1):
            rid = f"REVIEW-{i:03d}"
            (review / f"{rid}.txt").write_text(item["cv"].replace(item["profile_id"], rid), encoding="utf-8")
            writer.writerow([rid] + [""] * (len(columns)-1))
            mapping.append({"review_id": rid, "profile_id": item["profile_id"]})
    write_json(root / "reviewer_id_mapping.json", mapping)
    opportunity = read_json(root / "config.json")["opportunity"]
    (review / "README.txt").write_text("BLIND HUMAN REVIEW — PENDING\n\n" + opportunity + "\n\nRate academic/research evidence low, adequate, high, or unrated; overall weak, borderline, strong, or unrated. Record confidence, plausibility and prose inflation. Do not infer absent letters, faculty fit, course rigor or motivation. Assigned labels and mixed-profile categories are hidden. Share only this folder; the parent contains administrative labels and the ID mapping.\n", encoding="utf-8")


def build_index(root, rows, accepted, summary):
    by_id = {row["profile_id"]: row for row in rows}
    entries = []
    for item in accepted:
        row = by_id[item["profile_id"]]
        pid, area = row["profile_id"], row["facts"]["research_area"]
        entries.append('<details data-search="' + html.escape(pid + " " + area + " " + row["pathway"], quote=True) + '"><summary>' + html.escape(pid + " · " + area) + '</summary><p><a href="' + html.escape(item["resume"], quote=True) + '">Open resume text</a></p><pre>' + html.escape(item["cv"]) + '</pre></details>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PhD resumes · Version 2</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;font:16px/1.5 system-ui;color:#18232f;background:#f7f9fc}h1{font-size:30px}a{color:#1557a0}input{padding:12px;width:90%;margin:12px 0 24px;font:inherit}details{background:white;border:1px solid #d9e0e8;border-radius:8px;margin:10px 0;padding:16px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;font:14px/1.65 system-ui}.note{color:#4b596c}</style><h1>100 PhD applicant resumes · Version 2</h1><p class="note">Rubric v1 · GPT-6 Astra · Automated checks passed · Human review pending</p><p>Fictional research stimuli. Strength labels are excluded from the displayed CVs. For independent ratings, share only the blind_review folder.</p><p><a href="VALIDATION_REPORT.md">Validation report (contains group totals)</a> · <a href="blind_review/README.txt">Blind review instructions</a> · <a href="blind_review/ratings.csv">Blank ratings sheet</a></p><label for="search">Find an applicant by ID, research area or pathway</label><br><input id="search" type="search" placeholder="Search 100 resumes"><p id="count">100 resumes</p>'''
    page += "\n".join(entries) + '''<script>const input=document.getElementById('search');input.addEventListener('input',()=>{let n=0;document.querySelectorAll('details').forEach(el=>{el.hidden=!el.dataset.search.toLowerCase().includes(input.value.toLowerCase());if(!el.hidden)n++});document.getElementById('count').textContent=n+' resumes'});</script></html>'''
    (root / "index.html").write_text(page, encoding="utf-8")
    lines = ["# Version 2 — rubric-based PhD CV validation", "", "100 new CVs generated with GPT-6 Astra, medium reasoning; rubric v1 and conditional sampler v3. The original sample is unchanged.", "", f"Provisional tiers: {summary['selected_distribution']['tiers']}", f"Exclusive allocation cells: {summary['selected_distribution']['selection_cells']}", "", f"First-pass results: {summary['first_pass_status_counts']}", f"Repaired profiles: {summary['repaired_profiles']}; total wording repair attempts: {summary['total_repair_attempts']}.", "", "The 6,000-record pool and exact selection reproduce from saved settings. Fixed facts, rubric labels, final raw requests/responses, content constraints, separate-context reviews, rendered CVs and hashes all match. No facts or selected applicants were replaced to solve prose failures.", "", f"Saved API responses: {summary['unique_saved_api_responses']}; reported token usage: {summary['reported_token_usage']}. These are saved-response totals, not an invoice.", "", "## Limits", "", "The thresholds and joint distribution remain provisional. Same-model factual review is not independent human assessment. Generated technical prose can affect perceived merit beyond the structured fields. Research-side dependencies and course templates remain. Human review and empirical calibration are not complete.", "", "Share only `blind_review/` for independent ratings. Administrative labels, the ID mapping, original/rejected outputs, repairs, settings and source provenance remain in the parent directory.", ""]
    (root / "VALIDATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--stage", choices=["prepare", "pilot", "generate", "repair", "package"], required=True)
    parser.add_argument("--weak", type=int, default=30)
    parser.add_argument("--borderline", type=int, default=40)
    parser.add_argument("--strong", type=int, default=30)
    args = parser.parse_args()
    root = Path(args.out).resolve()
    if args.stage == "prepare":
        prepare(root, args.weak, args.borderline, args.strong)
    elif args.stage == "pilot":
        generate(root, pilot=True)
    else:
        {"generate": generate, "repair": repair, "package": package}[args.stage](root)
