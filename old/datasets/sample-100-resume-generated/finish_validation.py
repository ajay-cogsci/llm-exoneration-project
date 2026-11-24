"""Bounded wording repairs and local verification for this 100-CV validation run.

Preserves the original pipeline's first-pass outputs. Every repair retains the
same applicant facts and must pass the existing validators and reviewer prompt.
"""

import argparse
import csv
import hashlib
import html
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from phd_resumes.api import APIError, OpenAIResponses, request_body
from phd_resumes.io import digest, implementation_hash, read_json, read_jsonl, write_json, write_jsonl
from phd_resumes.pipeline import cached_call, utc_now
from phd_resumes.sampling import describe, generate_cohort, validate_profile
from phd_resumes.writing import (
    GENERATOR_INSTRUCTIONS, REVIEW_INSTRUCTIONS, content_schema, render_cv,
    review_schema, validate_content,
)

REPAIR_INSTRUCTIONS = GENERATOR_INSTRUCTIONS + """
Revise the supplied previous_entries to resolve the listed validation_issues.
The fixed_record remains authoritative and must not be changed. Preserve
unaffected content where possible. Return the complete revised entry object.
Do not use any digits in titles or bullets, including metric or method names;
use words such as F score instead. Do not use the word integrity, even for data
or database descriptions. Check that each bullet has twelve to thirty words.
Do not add claims, outputs, skills, responsibility, or numerical achievements.
"""
MAX_REPAIR_ATTEMPTS = 3


def records():
    plan = read_json(ROOT / "run_plan.json")
    for cohort in plan["cohorts"]:
        directory = ROOT / cohort["path"]
        for row in read_jsonl(directory / "profiles.jsonl"):
            yield directory, row


def valid_review(review):
    if (set(review) != {"passes", "issues"}
            or type(review["passes"]) is not bool
            or not isinstance(review["issues"], list)
            or any(not isinstance(issue, str) for issue in review["issues"])
            or review["passes"] != (not review["issues"])):
        raise APIError("Invalid reviewer result")
    return review


def repair_one(directory, row):
    pid, facts = row["profile_id"], row["facts"]
    if validate_profile(row):
        raise ValueError(f"Invalid fixed facts: {pid}")
    first = read_json(directory / "generation" / f"{pid}.status.json")
    if first["status"] == "ready_for_human_review":
        return {"profile_id": pid, "repair_attempts": 0, "status": first["status"]}
    if first["status"] != "needs_revision":
        raise ValueError(f"Resolve the original API failure before repairing {pid}")
    settings = read_json(directory / "config.json")["generation"]
    previous = read_json(directory / "generation" / f"{pid}.content.json")
    issues = first["issues"]
    out = ROOT / "repairs" / pid
    attempts = []
    client = OpenAIResponses()
    for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
        if (ROOT / "STOP").exists():
            raise APIError("Run stopped before next repair call")
        stage = out / f"attempt-{attempt}"
        payload = {"fixed_record": facts, "previous_entries": previous, "validation_issues": issues}
        body = request_body(settings["model"], REPAIR_INSTRUCTIONS, payload, content_schema(), settings)
        content, response = cached_call(client, body, stage / "raw" / "generation.json")
        write_json(stage / "content.json", content)
        issues = validate_content(facts, content)
        review = None
        if not issues:
            body = request_body(settings["review_model"], REVIEW_INSTRUCTIONS,
                {"fixed_record": facts, "cv_entries": content}, review_schema(), settings, review=True)
            review, _ = cached_call(client, body, stage / "raw" / "review.json")
            valid_review(review)
            issues.extend(review["issues"])
        status = {
            "profile_id": pid, "facts_hash": row["facts_hash"], "attempt": attempt,
            "issues": issues, "review": review, "model": response["response"].get("model"),
            "status": "needs_revision" if issues else "ready_for_human_review",
        }
        write_json(stage / "status.json", status)
        attempts.append(status)
        if not issues:
            cv = render_cv(facts, content)
            (out / "cv.txt").write_text(cv, encoding="utf-8")
            write_json(out / "content.json", content)
            write_json(out / "status.json", {**status, "repair_attempts": attempt,
                "cv_hash": digest(cv), "attempts": attempts})
            print(f"Repaired {pid} in {attempt} attempt(s)", flush=True)
            return {"profile_id": pid, "repair_attempts": attempt, "status": status["status"]}
        previous = content
    write_json(out / "status.json", {**status, "repair_attempts": MAX_REPAIR_ATTEMPTS, "attempts": attempts})
    print(f"Still needs review: {pid}", flush=True)
    return {"profile_id": pid, "repair_attempts": MAX_REPAIR_ATTEMPTS, "status": "needs_revision"}


def repair():
    if read_json(ROOT / "run_plan.json")["implementation_hash"] != implementation_hash():
        raise ValueError("Pipeline changed since the run was prepared")
    contract = {
        "created_for": "100-resume live validation", "implementation_hash": implementation_hash(),
        "repair_script_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "repair_instructions": REPAIR_INSTRUCTIONS, "review_instructions": REVIEW_INSTRUCTIONS,
        "max_attempts_per_rejected_profile": MAX_REPAIR_ATTEMPTS,
        "source_facts_must_remain_fixed": True,
    }
    path = ROOT / "repairs" / "contract.json"
    if path.exists() and read_json(path) != contract:
        raise ValueError("Repair implementation changed; preserve the existing repair batch")
    write_json(path, contract)
    pending = [(directory, row) for directory, row in records()
        if read_json(directory / "generation" / f"{row['profile_id']}.status.json")["status"] != "ready_for_human_review"]
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(repair_one, directory, row) for directory, row in pending]
        for future in as_completed(futures):
            results.append(future.result())
    write_json(ROOT / "repair_result.json", {"updated_at": utc_now(), "profiles": results})


def package():
    all_rows, accepted, first_statuses, repair_statuses = [], [], [], []
    all_pool = []
    source_checks = []
    for cohort in read_json(ROOT / "run_plan.json")["cohorts"]:
        directory = ROOT / cohort["path"]
        config = read_json(directory / "config.json")
        manifest = read_json(directory / "manifest.json")
        pool, selected = generate_cohort(config, cohort["seed"])
        saved_pool = read_jsonl(directory / "pool.jsonl")
        saved_selected = read_jsonl(directory / "profiles.jsonl")
        assert pool == saved_pool and selected == saved_selected, "Sampling reproduction failed"
        assert digest(config) == manifest["config_hash"]
        assert digest(selected) == manifest["profiles_hash"]
        assert digest(read_json(directory / "source_map.json")) == manifest["source_map_hash"]
        assert implementation_hash() == manifest["implementation_hash"]
        assert all(not validate_profile(row) for row in pool)
        all_pool.extend(pool)
        source_checks.append({"seed": cohort["seed"], "pool_count": len(pool),
            "selected_count": len(selected), "reproduced_exactly": True, "source_checks_passed": True})
    for directory, row in records():
        all_rows.append(row)
        pid = row["profile_id"]
        first = read_json(directory / "generation" / f"{pid}.status.json")
        first_statuses.append(first)
        status, repair_attempts = first, 0
        content_path = directory / "generation" / f"{pid}.content.json"
        cv_path = directory / "generation" / "cvs" / f"{pid}.txt"
        if first["status"] != "ready_for_human_review":
            repair_path = ROOT / "repairs" / pid
            if not (repair_path / "status.json").exists():
                continue
            status = read_json(repair_path / "status.json")
            repair_statuses.append(status)
            content_path, cv_path = repair_path / "content.json", repair_path / "cv.txt"
            repair_attempts = status["repair_attempts"]
        if status["status"] != "ready_for_human_review":
            continue
        content = read_json(content_path)
        assert not validate_content(row["facts"], content), pid
        assert valid_review(status["review"])["passes"], pid
        assert status["facts_hash"] == row["facts_hash"], pid
        cv = render_cv(row["facts"], content)
        assert cv == cv_path.read_text(encoding="utf-8"), pid
        assert digest(cv) == status["cv_hash"], pid
        accepted.append({"row": row, "cv": cv, "source": str(cv_path.relative_to(ROOT)),
            "content_source": str(content_path.relative_to(ROOT)), "repair_attempts": repair_attempts,
            "cv_hash": digest(cv)})
    assert len(all_rows) == 100 and len({row["profile_id"] for row in all_rows}) == 100
    assert len(accepted) == 100, f"Only {len(accepted)} of 100 CVs passed; package not finalized"
    accepted.sort(key=lambda item: item["row"]["profile_id"])
    final = ROOT / "resumes"
    final.mkdir(exist_ok=True)
    for item in accepted:
        (final / (item["row"]["profile_id"] + ".txt")).write_text(item["cv"], encoding="utf-8")
    assert len(list(final.glob("*.txt"))) == 100
    write_jsonl(ROOT / "profiles.jsonl", all_rows)
    write_jsonl(ROOT / "evaluator_fields.jsonl", [row["facts"] for row in all_rows])
    write_json(ROOT / "resume_manifest.json", [{key: value for key, value in item.items() if key not in {"row", "cv"}}
        | {"profile_id": item["row"]["profile_id"], "facts_hash": item["row"]["facts_hash"],
           "resume": "resumes/" + item["row"]["profile_id"] + ".txt"} for item in accepted])
    with (ROOT / "human_review.csv").open("w", newline="", encoding="utf-8") as stream:
        columns = ["profile_id", "reviewer", "plausible", "academic_preparation", "research_potential",
            "quantitative_preparation", "fit_evidence", "strength_rating", "factual_issues", "notes"]
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows([item["row"]["profile_id"]] + [""] * (len(columns)-1) for item in accepted)
    usage, models, response_ids = Counter(), Counter(), set()
    for path in sorted(ROOT.glob("**/raw/*.json")):
        response = read_json(path)["response"]
        response_id = response["id"]
        if response_id in response_ids:
            continue
        response_ids.add(response_id)
        models[response.get("model", "unknown")] += 1
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = response.get("usage", {}).get(key)
            if type(value) is int:
                usage[key] += value
    issues = Counter(issue for status in first_statuses for issue in status["issues"])
    summary = {
        "created_at": utc_now(), "resume_count": len(accepted), "selected_profiles": len(all_rows),
        "source_pool_count": len(all_pool), "cohort_verification": source_checks,
        "first_pass_status_counts": dict(Counter(status["status"] for status in first_statuses)),
        "first_pass_issues": dict(issues), "repaired_profiles": len(repair_statuses),
        "total_repair_attempts": sum(status["repair_attempts"] for status in repair_statuses),
        "final_status": "100 ready for human review; automated checks passed",
        "pathways": dict(Counter(row["pathway"] for row in all_rows)),
        "research_areas": dict(Counter(row["facts"]["research_area"] for row in all_rows)),
        "provisional_strength_counts": dict(Counter(row["strength"] for row in all_rows)),
        "selected_distribution": describe(all_rows), "pool_distribution": describe(all_pool),
        "unique_reported_responses": len(response_ids), "response_models": dict(models),
        "reported_token_usage_including_superseded_run_and_repairs": dict(usage),
        "usage_limit": "Deduplicated by response ID. Up to three interrupted initial calls may have been billed without a saved response; check the API dashboard for actual charges.",
        "checks": {"fixed_facts_valid": True, "content_constraints_passed": True,
            "separate_context_model_review_passed": True, "rendering_matches_facts_and_content": True,
            "sampling_reproduced": True, "unique_profile_ids": True, "resume_hashes_verified": True,
            "automated_test_count": 26},
        "human_review_completed": False, "empirical_phd_calibration": "not_established",
        "study_limit": "Provisional cohort-relative strength labels are not validated PhD admission judgments. Same-model factual review is not independent-model or human validation.",
    }
    write_json(ROOT / "validation_summary.json", summary)
    report = ["100 PhD applicant resumes — live validation", "",
        "Final resumes: 100 in resumes/. Browse index.html.",
        "Model: GPT-6 Astra, medium reasoning, strict structured outputs.",
        "Each accepted CV passed fixed-fact checks, content checks, a separate-context model review, and exact-render/hash verification.",
        "Human review remains pending. Use human_review.csv.", "",
        "Sampling: three seeds (123, 456, 789); retained 33, 33, 34 from pools of 50, 49, 51.",
        "Provisional strength counts: " + json.dumps(summary["provisional_strength_counts"]),
        "Pathways: " + json.dumps(summary["pathways"]),
        "Research areas: " + json.dumps(summary["research_areas"]), "",
        "First-pass outcomes: " + json.dumps(summary["first_pass_status_counts"]),
        f"Wording repairs: {summary['repaired_profiles']} profiles, {summary['total_repair_attempts']} attempts; original failures retained.",
        "No source facts or selected applicants were replaced to resolve wording failures.", "",
        "Sampling bug found and fixed: reinitializing the selection RNG with the preparation seed repeated its random stream and favored stronger applicants. Selection now has a separate reproducible stream.",
        "A regression check with equally sized cells reduced the selected-minus-pool preparation mean difference from 0.811 to 0.023; all 26 tests passed.",
        "The first, interrupted selection is preserved under audit/superseded-correlated-selection/. Identical saved requests were reused only after independent corrected selection.", "",
        f"Unique saved API responses, including superseded outputs and repairs: {len(response_ids)}.",
        "Reported token usage: " + json.dumps(dict(usage)), summary["usage_limit"], "",
        "Limits: the pipeline is a PhD adaptation of the paper, with provisional distributions and labels. This run validates execution and automated constraints; it does not establish empirical calibration, admissions validity, or human approval.",
        "The original pipeline has no automatic repair loop. finish_validation.py supplied a bounded, logged wording-repair step for this validation run.", "",
        "Audit files: run_plan.json, validation_summary.json, resume_manifest.json, sampling_fix_verification.json, cache_reuse.json, cohorts/, repairs/, audit/.",
        "No API keys are stored in these files. No Git commit or upload was performed for this run.", ""]
    (ROOT / "VALIDATION_REPORT.txt").write_text("\n".join(report), encoding="utf-8")
    entries = []
    for item in accepted:
        row = item["row"]
        pid = row["profile_id"]
        area = row["facts"]["research_area"]
        entries.append('<details data-search="' + html.escape(pid + " " + area + " " + row["pathway"], quote=True) + '">'
            + '<summary>' + html.escape(pid) + ' · ' + html.escape(area) + '</summary>'
            + '<p><a href="resumes/' + html.escape(pid) + '.txt">Open resume text</a></p>'
            + '<pre>' + html.escape(item["cv"]) + '</pre></details>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>100 PhD applicant resumes</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;font:16px/1.5 system-ui;color:#18232f;background:#f7f9fc}h1{font-size:30px}a{color:#1557a0}input{padding:12px;width:90%;margin:12px 0 24px;font:inherit}details{background:white;border:1px solid #d9e0e8;border-radius:8px;margin:10px 0;padding:16px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;font:14px/1.65 system-ui}.note{color:#4b596c}</style>
<h1>100 PhD applicant resumes</h1><p class="note">GPT-6 Astra · Three seeded cohorts · Automated checks passed · Human review pending</p>
<p><a href="VALIDATION_REPORT.txt">Validation report</a> · <a href="human_review.csv">Human review sheet</a> · <a href="validation_summary.json">Detailed checks and usage</a></p>
<p>Fictional research stimuli. The sampling assumptions remain provisional. Strength labels are excluded from these displayed resumes.</p>
<label for="search">Find an applicant by ID, research area, or pathway</label><br><input id="search" type="search" placeholder="Search 100 resumes"><p id="count">100 resumes</p>
''' + "\n".join(entries) + '''<script>const input=document.getElementById('search');input.addEventListener('input',()=>{let n=0;document.querySelectorAll('details').forEach(el=>{el.hidden=!el.dataset.search.toLowerCase().includes(input.value.toLowerCase());if(!el.hidden)n++});document.getElementById('count').textContent=n+' resumes'});</script></html>'''
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("resume_count", "first_pass_status_counts",
        "repaired_profiles", "unique_reported_responses", "reported_token_usage_including_superseded_run_and_repairs")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["repair", "package"], required=True)
    args = parser.parse_args()
    {"repair": repair, "package": package}[args.stage]()
