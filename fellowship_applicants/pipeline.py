"""Bounded model wording and portable, verifiable fellowship application exports."""

import hashlib
import html
import json
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Event

from phd_resumes.api import APIError, OpenAIResponses, request_body
from phd_resumes.io import implementation_hash as shared_hash
from phd_resumes.io import digest, read_json, read_jsonl, write_json, write_jsonl
from phd_resumes.pipeline import cached_call, utc_now
from phd_resumes.writing import review_schema
from .plan import CRITERION_FIELDS, OPPORTUNITY, PLAN_FILENAME, PLAN_SHA256, SOURCE_URLS, SYSTEM_TEMPLATE, assessment_messages, verify_source
from .sampling import check_config, evaluate, make_pool, require, select_allocated, summarize, validate_facts
from .writing import GENERATOR_INSTRUCTIONS, PROMPT_VERSION, REPAIR_INSTRUCTIONS, REVIEW_INSTRUCTIONS, content_schema, render_application, validate_content

PROJECT = Path(__file__).resolve().parents[1]


def implementation_hash():
    return digest({"fellowship": {p.name: p.read_text(encoding="utf-8") for p in sorted(Path(__file__).parent.glob("*.py"))}, "shared": shared_hash()})


def contract(config):
    return {"prompt_version": PROMPT_VERSION, "generator_instructions": GENERATOR_INSTRUCTIONS, "repair_instructions": REPAIR_INSTRUCTIONS, "review_instructions": REVIEW_INSTRUCTIONS, "content_schema": content_schema(), "review_schema": review_schema(), "settings": config["generation"], "max_repairs": config["max_repairs"]}


def prepare(config, root):
    check_config(config)
    verify_source(PROJECT / PLAN_FILENAME)
    root = Path(root)
    require(not root.exists(), "Choose a new run directory; existing runs are preserved")
    pool = make_pool(config)
    rows = select_allocated(pool, config)
    require(bool(rows), "Select at least one applicant")
    root.mkdir(parents=True)
    write_json(root / "config.json", config)
    write_jsonl(root / "pool.jsonl", pool)
    write_jsonl(root / "profiles.jsonl", rows)
    write_json(root / "contract.json", contract(config))
    write_json(root / "manifest.json", {"created_at": utc_now(), "implementation_hash": implementation_hash(), "config_hash": digest(config), "profiles_hash": digest(rows), "pool_hash": digest(pool), "contract_hash": digest(contract(config)), "plan_sha256": PLAN_SHA256})
    for package in ("fellowship_applicants", "phd_resumes"):
        snapshot = root / "implementation" / package
        snapshot.mkdir(parents=True)
        for path in (PROJECT / package).glob("*.py"):
            shutil.copyfile(path, snapshot / path.name)
    report = {"pool": summarize(pool), "selected": summarize(rows), "api_calls": 0, "parameter_status": config["parameter_status"]}
    write_json(root / "sampling_report.json", report)
    return report


def load_run(root):
    root = Path(root)
    config, manifest, rows = read_json(root / "config.json"), read_json(root / "manifest.json"), read_jsonl(root / "profiles.jsonl")
    check_config(config)
    require(implementation_hash() == manifest["implementation_hash"], "Implementation changed after facts were frozen; use a new run")
    require(digest(config) == manifest["config_hash"] and digest(rows) == manifest["profiles_hash"], "Frozen config/profiles changed")
    require(read_json(root / "contract.json") == contract(config) and digest(contract(config)) == manifest["contract_hash"], "Generation contract changed")
    require(digest(read_jsonl(root / "pool.jsonl")) == manifest["pool_hash"], "Frozen source pool changed")
    for row in rows:
        require(not validate_facts(row["facts"], config), "Invalid frozen facts")
        require(row["profile_id"] == row["facts"]["applicant_id"] and row["facts_hash"] == digest(row["facts"]) and row["rubric"] == evaluate(row["facts"], config) and row["strength"] == row["rubric"]["tier"], "Source facts and label metadata disagree")
    return config, rows


def valid_review(review):
    require(isinstance(review, dict) and set(review) == {"passes", "issues"} and type(review["passes"]) is bool and isinstance(review["issues"], list) and all(isinstance(i, str) for i in review["issues"]) and review["passes"] == (not review["issues"]), "Invalid factual-review response")
    return review


def body_for(config, instructions, payload, *, review=False):
    settings = config["generation"]
    body = request_body(settings["review_model" if review else "model"], instructions, payload, review_schema() if review else content_schema(), settings, review=review)
    body["text"]["format"]["name"] = "fellowship_factual_review" if review else "fellowship_entries"
    return body


def verify_accepted(root, row):
    folder = Path(root) / "generation" / row["profile_id"]
    require((folder / "status.json").is_file(), f"Applicant has no completed generation: {row['profile_id']}")
    status = read_json(folder / "status.json")
    require(status["status"] == "passed_automated_checks", f"Applicant has not passed factual checks: {row['profile_id']}")
    require((folder / "content.json").is_file(), f"Accepted content missing: {row['profile_id']}")
    content = read_json(folder / "content.json")
    require(status["status"] == "passed_automated_checks" and status["facts_hash"] == row["facts_hash"] and status["content_hash"] == digest(content), "Unaccepted or changed content")
    require(not validate_content(row["facts"], content) and valid_review(status["review"])["passes"], "Accepted content fails validation")
    application = render_application(row["facts"], content)
    require(digest(application) == status["application_hash"], "Application hash mismatch")
    return status, content, application


def generate_one(root, row, config, client, stop):
    root = Path(root)
    folder = root / "generation" / row["profile_id"]
    if (folder / "status.json").exists() and read_json(folder / "status.json")["status"] == "passed_automated_checks":
        return verify_accepted(root, row)[0]
    previous, issues = None, []
    for attempt in range(config["max_repairs"] + 1):
        if stop.is_set() or (root / "STOP").exists():
            raise APIError("Stopped before the next model call")
        stage = folder / f"attempt-{attempt}"
        payload = {"fixed_record": row["facts"]}
        if attempt:
            payload.update(previous_entries=previous, validation_issues=issues)
        body = body_for(config, REPAIR_INSTRUCTIONS if attempt else GENERATOR_INSTRUCTIONS, payload)
        content, response = cached_call(client, body, stage / "generation.json")
        write_json(stage / "content.json", content)
        issues = validate_content(row["facts"], content)
        review, review_response = None, None
        if not issues:
            if stop.is_set() or (root / "STOP").exists():
                raise APIError("Stopped before factual review")
            body = body_for(config, REVIEW_INSTRUCTIONS, {"fixed_record": row["facts"], "entries": content, "application_text": render_application(row["facts"], content)}, review=True)
            review, review_response = cached_call(client, body, stage / "review.json")
            issues = valid_review(review)["issues"]
        status = {"profile_id": row["profile_id"], "facts_hash": row["facts_hash"], "content_hash": digest(content), "status": "needs_revision" if issues else "passed_automated_checks", "repair_attempts": attempt, "issues": issues, "review": review, "generation_model": response["response"].get("model"), "review_model": review_response["response"].get("model") if review_response else None}
        if not issues:
            application = render_application(row["facts"], content)
            status["application_hash"] = digest(application)
            write_json(folder / "content.json", content)
            write_json(folder / "status.json", status)
            return status
        write_json(folder / "status.json", status)
        previous = content
    return status


def run_summary(root, rows):
    counts, usage, repairs = Counter(), Counter(), Counter()
    responses = 0
    for row in rows:
        path = Path(root) / "generation" / row["profile_id"] / "status.json"
        status = read_json(path) if path.exists() else {"status": "pending"}
        counts[status["status"]] += 1
        if status["status"] == "passed_automated_checks":
            repairs[str(status["repair_attempts"])] += 1
    for path in sorted((Path(root) / "generation").glob("*/attempt-*/*.json")):
        if path.name not in {"generation.json", "review.json"}:
            continue
        response = read_json(path)["response"]
        responses += 1
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = response.get("usage", {}).get(key)
            if type(value) is int and value >= 0:
                usage[key] += value
    return {"applicant_count": len(rows), "status_counts": dict(counts), "accepted_by_repair_attempt": dict(repairs), "saved_api_responses": responses, "reported_usage": dict(usage), "independent_human_validation_completed": False, "calibration_against_real_fellowship_selection": "not_established"}


def generate(root, *, limit=None, client=None):
    root = Path(root)
    config, rows = load_run(root)
    if limit is not None:
        require(type(limit) is int and limit > 0, "limit must be positive")
    # Interleave tiers so a short pilot covers all three groups.
    groups = [[r for r in rows if r["strength"] == tier] for tier in ("weak", "borderline", "strong")]
    ordered = [group[i] for i in range(max(map(len, groups))) for group in groups if i < len(group)]
    selected = ordered[:limit] if limit else ordered
    client = client if client is not None else OpenAIResponses()
    stop = Event()
    failures = []
    with ThreadPoolExecutor(max_workers=config["max_workers"]) as executor:
        futures = {executor.submit(generate_one, root, row, config, client, stop): row["profile_id"] for row in selected}
        for future in as_completed(futures):
            if future.cancelled():
                continue
            pid = futures[future]
            try:
                status = future.result()
                require(status["status"] == "passed_automated_checks", f"Factual checks exhausted for {pid}; stopping rather than continuing an invalid batch")
                print(f"{pid}: {status['status']} (repairs={status['repair_attempts']})", flush=True)
            except Exception as exc:
                stop.set()
                failures.append({"profile_id": pid, "type": type(exc).__name__, "error": str(exc)})
                for pending in futures:
                    pending.cancel()
    summary = run_summary(root, rows)
    summary["failures"] = failures
    write_json(root / "generation_summary.json", summary)
    require(not failures, f"Model run stopped; see {root / 'generation_summary.json'}")
    return summary


def file_checksums(root):
    root = Path(root)
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.rglob("*")) if path.is_file() and path.name != "checksums.json"}


def export(root, out):
    root, out = Path(root).resolve(), Path(out).resolve()
    config, rows = load_run(root)
    require(not out.exists() and out != root and root not in out.parents, "Choose a new export outside the working run")
    accepted = [(row, *verify_accepted(root, row)) for row in rows]
    summary = run_summary(root, rows)
    out.mkdir(parents=True)
    for name, value in (("config.json", config), ("generation_contract.json", contract(config)), ("validation.json", summary), ("sampling_report.json", read_json(root / "sampling_report.json"))):
        write_json(out / name, value)
    write_jsonl(out / "profiles.jsonl", rows)
    write_jsonl(out / "evaluator_fields.jsonl", [row["facts"] for row in rows])
    write_json(out / "source_map.json", {"plan_file": PLAN_FILENAME, "plan_sha256": PLAN_SHA256, "opportunity_sources_as_listed_in_plan": SOURCE_URLS, "criterion_fields": CRITERION_FIELDS, "method": "Structured sampling with separate preparation, proposal and impact streams; criterion labels and allocated sampling adapted from the revised PhD/TA pipelines.", "assumptions": "All numerical settings, evidence templates, graduate pathway frequencies and rubric rules are provisional study choices, not supplied by the plan or empirical fellowship population data."})
    prompts = out / "prompts"
    prompts.mkdir()
    (prompts / "system_template.txt").write_text(SYSTEM_TEMPLATE + "\n", encoding="utf-8")
    (prompts / "system_resolved.txt").write_text(assessment_messages("placeholder", config["committee_name"])[0]["content"] + "\n", encoding="utf-8")
    (prompts / "opportunity.txt").write_text(OPPORTUNITY + "\n", encoding="utf-8")
    manifest, messages, cards = [], [], []
    for row, status, content, application in accepted:
        pid = row["profile_id"]
        path = out / "applications" / f"{pid}.txt"
        path.parent.mkdir(exist_ok=True)
        path.write_text(application, encoding="utf-8")
        write_json(out / "generation" / f"{pid}.content.json", content)
        write_json(out / "generation" / f"{pid}.status.json", status)
        manifest.append({"profile_id": pid, "application": str(path.relative_to(out)), "facts_hash": row["facts_hash"], "application_hash": digest(application), "content_hash": digest(content)})
        messages.append({"profile_id": pid, "condition": None, "assessment": "overall_quality", "messages": assessment_messages(application, config["committee_name"])})
        cards.append(f'<article data-tier="{row["strength"]}"><h2>{html.escape(pid)}</h2><p class="meta">Provisional study tier: {row["strength"]} · Pattern: {html.escape(row["designated_mixed_pattern"].replace("_", " "))}</p><p><a href="applications/{pid}.txt">Open application text</a></p><pre>{html.escape(application)}</pre></article>')
    write_json(out / "application_manifest.json", manifest)
    write_jsonl(out / "evaluator_inputs.jsonl", messages)
    write_json(out / "dataset.json", {"version": config["version"], "publication_status": "pending_user_approval", "created_at": utc_now(), "source_implementation_hash": implementation_hash(), "profiles_hash": digest(rows), "config_hash": digest(config), "plan_sha256": PLAN_SHA256, "application_count": len(rows), "selection": summarize(rows), "evaluation_calls": 0, "integrity_conditions_assigned": False})
    (out / "index.html").write_text(viewer_html("\n".join(cards), len(rows)), encoding="utf-8")
    (out / "README.md").write_text(dataset_readme(summary, config), encoding="utf-8")
    write_json(out / "checksums.json", file_checksums(out))
    return verify_export(out)


def viewer_html(cards, count):
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Graduate fellowship applicant sample</title><style>body{{margin:0;background:#f4f5f7;color:#182331;font:16px system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:36px 24px}}h1{{font-size:32px}}article{{background:white;border:1px solid #d8dfe5;border-radius:10px;padding:24px;margin:24px 0}}h2{{font-size:20px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.65 ui-monospace,monospace}}.meta{{color:#566477}}select{{font:inherit;padding:8px}}a{{color:#164c88}}[hidden]{{display:none}}</style><main><h1>Graduate fellowship applicant sample</h1><p>{count} fictional applicants for the research plan’s fictional graduate research fellowship.</p><p>Research view: provisional tier labels appear here, but are excluded from application files and evaluator inputs.</p><p><a href="README.md">Dataset documentation</a> · <label>Show <select id="tier"><option value="all">All applicants</option><option>weak</option><option>borderline</option><option>strong</option></select></label> · <span id="count">{count}</span> shown</p>{cards}</main><script>document.getElementById('tier').addEventListener('change',function(){{let n=0;document.querySelectorAll('article').forEach(a=>{{a.hidden=this.value!=='all'&&a.dataset.tier!==this.value;if(!a.hidden)n++;}});document.getElementById('count').textContent=n;}});</script></html>'''


def dataset_readme(summary, config):
    return f"""# Graduate Research Fellowship applicants

{summary['applicant_count']} fictional early-stage CS graduate applicants.
Study allocation: {config['allocation']}. Mixed-case allocation:
{config['mixed_allocation']}.

This local dataset is pending user review and publication approval.
The fellowship is fictional. Actual NSF eligibility, award amounts, award duration,
reference-letter requirements and essay formats are not imposed.

## Contents

- `applications/`: complete CV-style records, supervisor observations, structured
  research proposals and broader-impact plans.
- `profiles.jsonl`: source facts plus provisional tier and sampling metadata.
- `evaluator_fields.jsonl`: facts without tier or sampling metadata.
- `evaluator_inputs.jsonl`: exact shared system and fellowship opportunity wording
  with the overall-quality question. `condition: null` means untreated base input,
  not an assigned clean-record treatment. No evaluation calls were made.
- `generation/`: accepted experience wording and separate-context factual checks.
- `config.json`, `source_map.json`, `generation_contract.json`: assumptions,
  parameters and frozen generation instructions.
- `sampling_report.json`, `validation.json`, `checksums.json`: diagnostic and
  reproducibility records. `index.html` is a local review viewer.

The underlying facts, proposal components and impact-plan components are generated
before wording. Models paraphrase only completed project/research tasks. The
fixed renderer preserves grades, chronology, outputs, observations and all
proposal/impact components. Proposed results are never counted as achievements.

Tiers use provisional academic, completed-research, proposal and broader-impact
rules. They are assigned before allocation and do not depend on cohort percentiles.
Neither publications nor past outreach is required for a strong tier. Ten mixed
cases are deliberately selected; other naturally mixed records may also appear.
Complete proposal and impact bundles are distinct. Non-designated candidates may
be replaced by same-tier pool candidates before wording to keep estimated tier
mean lengths within 4%; no model outcomes enter selection. Actual lengths and
evidence-removal sensitivity are reported in the audit.

The numerical distributions, course-credit assumption, fixed templates and rubric
are study choices, not NSF thresholds or measured fellowship-population estimates.
There are eight CS topic families, four impact-plan families, generic institutions
and a finite catalogue of varied project and research episodes. Full proposal and
impact bundles are unique in the selected sample, but shared template components
remain. This bounds realism and diversity.
Supervisor observations are synthetic application evidence, not real letters.
Automated checks cannot validate whether a real selection committee would agree
with these tiers. This export has not received independent human validation.

Model usage: {summary['saved_api_responses']} saved responses;
{summary['reported_usage'].get('total_tokens', 0)} reported tokens.
Generation model: {config['generation']['model']}.
Factual review model: {config['generation']['review_model']}.
A separate call to the same model is a consistency check, not an independent judge.

Verify offline from the project root:

```sh
python3 -m fellowship_applicants verify --out <this-directory>
```

The original structured-profile method is described in
[Nghiem et al., Section 3 and Appendix D](https://arxiv.org/html/2509.16400v1).
The paper addresses undergraduate admissions; fellowship criteria, rubric labels,
fixed proposal templates and optional model wording are adaptations.
The plan's source for fellowship criteria is the
[NSF review process](https://www.nsf.gov/funding/initiatives/grfp/review-process).
"""


def verify_export(out):
    out = Path(out)
    require(read_json(out / "checksums.json") == file_checksums(out), "Export inventory/checksum mismatch")
    config = read_json(out / "config.json")
    pool = make_pool(config)
    rows = read_jsonl(out / "profiles.jsonl")
    require(select_allocated(pool, config) == rows, "Structured sample does not reproduce")
    metadata = read_json(out / "dataset.json")
    require(metadata["version"] == config["version"] and metadata["config_hash"] == digest(config) and metadata["profiles_hash"] == digest(rows) and metadata["application_count"] == len(rows) and metadata["selection"] == summarize(rows) and metadata["plan_sha256"] == PLAN_SHA256, "Dataset metadata differs")
    report = read_json(out / "sampling_report.json")
    require(report["pool"] == summarize(pool) and report["selected"] == summarize(rows), "Saved sampling diagnostics differ")
    require(read_jsonl(out / "evaluator_fields.jsonl") == [row["facts"] for row in rows], "Evaluator facts differ")
    require((out / "prompts/system_template.txt").read_text() == SYSTEM_TEMPLATE + "\n" and (out / "prompts/opportunity.txt").read_text() == OPPORTUNITY + "\n", "Plan wording changed")
    require((out / "prompts/system_resolved.txt").read_text() == assessment_messages("placeholder", config["committee_name"])[0]["content"] + "\n", "Resolved system message changed")
    expected_messages, expected_manifest = [], []
    for row in rows:
        pid = row["profile_id"]
        content = read_json(out / "generation" / f"{pid}.content.json")
        status = read_json(out / "generation" / f"{pid}.status.json")
        application = render_application(row["facts"], content)
        require(status["status"] == "passed_automated_checks" and valid_review(status["review"])["passes"] and status["facts_hash"] == row["facts_hash"] and status["content_hash"] == digest(content) and status["application_hash"] == digest(application), "Accepted export differs from source checks")
        require((out / "applications" / f"{pid}.txt").read_text(encoding="utf-8") == application, "Application render differs")
        expected_messages.append({"profile_id": pid, "condition": None, "assessment": "overall_quality", "messages": assessment_messages(application, config["committee_name"])})
        expected_manifest.append({"profile_id": pid, "application": f"applications/{pid}.txt", "facts_hash": row["facts_hash"], "application_hash": digest(application), "content_hash": digest(content)})
    require(read_jsonl(out / "evaluator_inputs.jsonl") == expected_messages and read_json(out / "application_manifest.json") == expected_manifest, "Evaluator inputs/manifest differ")
    require(read_json(out / "generation_contract.json") == contract(config), "Generation contract differs")
    return {"verified_applications": len(rows), "selection": summarize(rows), "pool_reproduced": len(pool), "checksums_verified": True, "application_rendering_verified": True, "plan_messages_verified": True, "api_calls": 0}
