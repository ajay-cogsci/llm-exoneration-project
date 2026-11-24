"""Build the corrected portable datasets from the published ones.

Inputs are the published version 2 CVs and two policy files. Outputs are a
corrected CV dataset and a regenerated application-packet dataset. Everything
here is deterministic and makes no model or network calls.
"""

import hashlib
import html
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from phd_resumes.io import digest, read_json, read_jsonl, write_json, write_jsonl
from phd_resumes.writing import render_cv
from phd_recommendations.pipeline import distributions, generate, render_letters

from .gpa_consistency import revise_all

SOURCE_CVS = "phd-cvs-v2-rubric-v1"
SOURCE_PACKETS = "phd-applications-v3-recommendations-v1"
CVS = "phd-cvs-v3-gpa-consistency-v1"
PACKETS = "phd-applications-v4-recommendations-v2"
RELEASE_DATE = "2026-11-11"

STYLE = "body{font:16px/1.55 system-ui;max-width:1050px;margin:40px auto;padding:0 24px;color:#18232d}details{border:1px solid #ccd4dd;border-radius:8px;margin:12px 0;padding:16px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui}a{color:#145a96}"


def write_checksums(root):
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file() and p.name != "checksums.json"}
    write_json(root / "checksums.json", files)


def page(title, cards):
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><h1>{html.escape(title)}</h1><p><a href="README.md">Dataset documentation</a> · <a href="dataset.json">Dataset metadata</a></p>' + "".join(cards) + "</html>\n"


def build_cvs(source, out, policy):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ValueError(f"{out} already exists; datasets are never overwritten")
    config, rubric, sampling = (read_json(source / name) for name in ("config.json", "rubric.json", "sampling_policy.json"))
    rows = read_jsonl(source / "profiles.jsonl")
    manifest = {entry["profile_id"]: entry for entry in read_json(source / "resume_manifest.json")}
    revised, changes = revise_all(rows, config, sampling, rubric, policy)
    changed = {change["profile_id"]: change for change in changes}
    out.mkdir(parents=True)
    for name in ("config.json", "rubric.json", "sampling_policy.json"):
        shutil.copyfile(source / name, out / name)
    write_json(out / "gpa_consistency_policy.json", policy)
    write_json(out / "gpa_consistency_changes.json", changes)
    write_jsonl(out / "profiles.jsonl", revised)
    write_jsonl(out / "evaluator_fields.jsonl", [row["facts"] for row in revised])
    (out / "generation").mkdir()
    (out / "resumes").mkdir()
    new_manifest, cards = [], []
    for row in revised:
        pid, facts = row["profile_id"], row["facts"]
        entry = dict(manifest[pid])
        content_path = source / entry["content_source"]
        status_path = content_path.with_name(content_path.name.replace(".content.json", ".status.json"))
        shutil.copyfile(content_path, out / entry["content_source"])
        cv = render_cv(facts, read_json(content_path))
        if pid in changed:
            status = read_json(status_path)
            # The accepted prose is unchanged and never mentions the GPA. The
            # model review recorded here was run against the original record.
            status.update(facts_hash=row["facts_hash"], cv_hash=digest(cv), revision={"policy_version": policy["version"], "field": "gpa", "original_facts_hash": changed[pid]["original_facts_hash"], "original_cv_hash": entry["cv_hash"], "model_review_rerun": False})
            write_json(out / "generation" / status_path.name, status)
            entry.update(facts_hash=row["facts_hash"], cv_hash=digest(cv))
        else:
            shutil.copyfile(status_path, out / "generation" / status_path.name)
            if cv != (source / entry["resume"]).read_text(encoding="utf-8"):
                raise ValueError(f"Unchanged applicant {pid} no longer renders identically")
        (out / entry["resume"]).write_text(cv, encoding="utf-8")
        new_manifest.append(entry)
        cards.append(f'<details><summary>{html.escape(pid)} · {html.escape(facts["research_area"])}</summary><p><a href="{entry["resume"]}">CV text</a></p><pre>{html.escape(cv)}</pre></details>')
    write_json(out / "resume_manifest.json", new_manifest)
    (out / "index.html").write_text(page("PhD applicant CVs — version 3", cards), encoding="utf-8")
    source_meta = read_json(source / "dataset.json")
    tiers = Counter(row["strength"] for row in revised)
    write_json(out / "dataset.json", {
        "version": CVS, "release_date": RELEASE_DATE, "source_cv_dataset": f"../{SOURCE_CVS}", "applicants": len(revised),
        "cv_tiers": {tier: tiers[tier] for tier in ("weak", "borderline", "strong")},
        "gpa_consistency_policy": policy["version"], "gpa_values_changed": len(changes),
        "tier_changes": [{k: c[k] for k in ("profile_id", "original_tier", "revised_tier")} for c in changes if c["original_tier"] != c["revised_tier"]],
        "selection_pattern_changes": [{k: c[k] for k in ("profile_id", "original_selection_pattern", "revised_selection_pattern")} for c in changes if c["original_selection_pattern"] != c["revised_selection_pattern"]],
        "prose": f"Accepted version 2 prose reused unchanged ({source_meta['generation_model']}, {source_meta['reasoning_effort']} reasoning effort). No model calls were made for this version.",
        "validation": "Deterministic reproduction from the version 2 dataset and the saved policy; structural and rubric checks passed. Model factual review was not rerun for the changed GPA lines. Tier calibration against real admissions outcomes is not established.",
    })
    (out / "README.md").write_text(cv_readme(len(revised), changes, tiers, policy), encoding="utf-8")
    write_checksums(out)
    return changes


def letter_changes(old_records, new_records):
    old = {record["applicant_id"]: record for record in old_records}
    rows = []
    for record in new_records:
        for before, after in zip(old[record["applicant_id"]]["letters"], record["letters"]):
            if before["summary"] != after["summary"] or before["strength_level"] != after["strength_level"]:
                rows.append({"applicant_id": record["applicant_id"], "letter_id": after["letter_id"], "assignment_category": after["assignment_category"], "relationship": after["relationship"]["description"], "original_strength_level": before["strength_level"], "revised_strength_level": after["strength_level"]})
    return rows


def build_packets(cvs, previous, out, policy):
    cvs, previous, out = Path(cvs), Path(previous), Path(out)
    if out.exists():
        raise ValueError(f"{out} already exists; datasets are never overwritten")
    with tempfile.TemporaryDirectory() as scratch:
        run = Path(scratch) / "run"
        generate(cvs, run, policy)
        out.mkdir(parents=True)
        for name in ("policy.json", "recommendations.jsonl", "manifest.json"):
            shutil.copyfile(run / name, out / name)
        for folder in ("inputs", "resumes", "recommendations", "applications"):
            shutil.copytree(run / folder, out / folder)
    applicants, records = read_jsonl(out / "inputs" / "applicants.jsonl"), read_jsonl(out / "recommendations.jsonl")
    changes = letter_changes(read_jsonl(previous / "recommendations.jsonl"), records)
    write_json(out / "letter_changes.json", changes)
    cards = []
    for applicant, record in zip(applicants, records):
        pid = record["applicant_id"]
        cards.append(f'<details><summary>{html.escape(pid)} · {html.escape(applicant["facts"]["research_area"])}</summary><p><a href="applications/{pid}.txt">Complete application</a> · <a href="recommendations/{pid}.txt">Recommendation summaries</a> · <a href="resumes/{pid}.txt">CV</a></p><h3>CV</h3><pre>{html.escape(applicant["cv"])}</pre><h3>Recommendations</h3><pre>{html.escape(render_letters(record))}</pre></details>')
    (out / "index.html").write_text(page("PhD applications with recommendation summaries — version 4", cards), encoding="utf-8")
    spread = distributions(records)
    write_json(out / "dataset.json", {
        "version": PACKETS, "release_date": RELEASE_DATE, "source_cv_dataset": f"../{CVS}", "previous_packet_dataset": f"../{SOURCE_PACKETS}",
        "applicants": len(records), "recommendation_summaries": 3 * len(records), "complete_packets": len(records),
        "letter_fields": ["writer_type", "strength_level", "compares_with_other_students", "gives_specific_example"],
        "generation": "Fixed templates; zero model calls.", "recommendation_policy": policy["version"],
        "letters_changed_from_previous_version": len(changes), "distribution": spread,
        "validation": "Consistency and deterministic-reproduction checks passed; letter-strength probabilities are provisional.",
        "cv_labels": "CV-only tiers from the version 3 CV dataset; recommendations do not relabel applicants.",
    })
    (out / "README.md").write_text(packet_readme(len(records), changes, spread), encoding="utf-8")
    write_checksums(out)
    return changes


def build(datasets, gpa_policy, recommendation_policy):
    datasets = Path(datasets)
    gpa_changes = build_cvs(datasets / SOURCE_CVS, datasets / CVS, gpa_policy)
    changes = build_packets(datasets / CVS, datasets / SOURCE_PACKETS, datasets / PACKETS, recommendation_policy)
    return {"cv_dataset": CVS, "packet_dataset": PACKETS, "gpa_values_changed": len(gpa_changes), "letters_changed": len(changes), "api_calls": 0}


def cv_readme(count, changes, tiers, policy):
    moved = [c for c in changes if c["original_tier"] != c["revised_tier"]]
    relabeled = [c for c in changes if c["original_selection_pattern"] != c["revised_selection_pattern"]]
    table = "\n".join(f"| {c['profile_id']} | {c['coursework_grade_point_mean']:.3f} | {c['original_gpa']:.2f} | {c['revised_gpa']:.2f} | {c['original_tier']} | {c['revised_tier']} |" for c in changes)
    return f"""# PhD applicant CVs — version 3 (GPA consistency)

The same {count} applicants as [version 2](../{SOURCE_CVS}/), with one correction:
{len(changes)} CVs printed a cumulative GPA that contradicted the course grades on
the same page (for example a 3.94 GPA beside B, B, B+, B). Those GPA values were
redrawn. Nothing else changed: applicants, coursework, dates, research,
publications, work, projects and all accepted CV prose are identical, and the
other {count - len(changes)} CV files are byte-identical to version 2. No model calls were made.

## Rule and correction

A CV is consistent when its GPA lies within {policy['max_abs_gap']} grade points of the unweighted
grade-point mean of its four listed courses. A violating CV receives a new GPA
drawn from the sampler's own GPA distribution for that applicant's academic
level, restricted to consistent values. The draw is also restricted to values
that keep the rubric's academic rating, when such a value exists. The seed and
settings are in [gpa_consistency_policy.json](gpa_consistency_policy.json); the
tolerance is a plausibility bound chosen for this study, not an empirical
relationship between course grades and GPA.

| Applicant | Course mean | GPA v2 | GPA v3 | Tier v2 | Tier v3 |
| --- | ---: | ---: | ---: | --- | --- |
{table}

## Consequences to know about

- The allocation is now {tiers['weak']} weak, {tiers['borderline']} borderline and {tiers['strong']} strong. {len(moved)} applicant
  changed tier ({', '.join(c['profile_id'] for c in moved) or 'none'}), because no consistent GPA could keep its
  previous academic rating. The allocation no longer equals the 30/40/30 quota
  in `sampling_policy.json`, which describes how the version 2 sample was drawn.
- {len(relabeled)} applicants ({', '.join(c['profile_id'] for c in relabeled) or 'none'}) keep their tier but now match the
  `lower_gpa_strong_research` descriptive pattern first.
- `legacy_diagnostic` in a changed record still describes the original draw.
- The model factual review recorded in `generation/*.status.json` was run on
  the version 2 record. It was not rerun; the changed line is rendered by code
  and the reviewed prose never mentions the GPA. Each changed status file says so.
- Human review of the CVs is still pending, as in version 2.

## Files

| Location | Contents |
| --- | --- |
| [resumes/](resumes/) | {count} final CV text files |
| [index.html](index.html) | Local HTML browser for all CVs |
| [profiles.jsonl](profiles.jsonl) | Structured records and internal rubric labels; changed records carry `gpa_consistency` |
| [evaluator_fields.jsonl](evaluator_fields.jsonl) | Applicant facts without analysis labels |
| [gpa_consistency_changes.json](gpa_consistency_changes.json) | Every changed value with before/after hashes and labels |
| [generation/](generation/) | Accepted CV descriptions and check statuses |
| [resume_manifest.json](resume_manifest.json) | CV/content paths and source hashes |
| [config.json](config.json), [rubric.json](rubric.json), [sampling_policy.json](sampling_policy.json) | Version 2 construction settings, copied unchanged |
| [checksums.json](checksums.json) | SHA-256 of every other file in this directory |

Use the packets in [version 4](../{PACKETS}/) for evaluation. Do not send internal
labels or latent fields to an evaluator. From the repository root,
`python3 scripts/verify_datasets.py` rebuilds this dataset from version 2 and the
saved policy and compares every file.
"""


def packet_readme(count, changes, spread):
    table = "\n".join(f"| {c['applicant_id']} | {c['letter_id']} | {c['relationship'].split(' in ', 1)[-1].rstrip('.').replace(', for which the recorded grade is ', ': ')} | {c['original_strength_level']} | {c['revised_strength_level']} |" for c in changes)
    levels = spread["strength_levels"]
    return f"""# PhD application packets — version 4

{count} corrected CVs from [CV version 3](../{CVS}/), each with three recommendation
summaries written from fixed templates. This version replaces
[packet version 3](../{SOURCE_PACKETS}/) for evaluation. It made no model calls.

## What changed from version 3

1. **CVs.** The GPA line changed in the CVs listed in the CV dataset's README.
2. **Letters.** A grade-only course letter can no longer contradict the grade it
   cites. A grade of A- or better has no limited endorsement, and a grade of B
   or B+ has no strong endorsement; the removed probability moved to moderate.
   The seed and random streams are unchanged, so only letters whose original
   draw fell in a removed cell changed. That is {len(changes)} of {3 * count} letters:

| Applicant | Letter | Course and grade | Strength v3 | Strength v4 |
| --- | --- | --- | --- | --- |
{table}

Every other letter is word-for-word identical to version 3. The full list is in
[letter_changes.json](letter_changes.json) and the settings are in
[policy.json](policy.json).

## Contents

| Location | Contents |
| --- | --- |
| [applications/](applications/) | {count} complete CV-plus-recommendation text packets |
| [recommendations/](recommendations/) | Three summaries per applicant |
| [resumes/](resumes/) | Byte-identical copies of the version 3 CVs |
| [index.html](index.html) | Local browser showing CVs and summaries |
| [recommendations.jsonl](recommendations.jsonl) | All {3 * count} letters, fields and evidence links |
| [inputs/applicants.jsonl](inputs/applicants.jsonl) | Facts, accepted CV descriptions and CV text |
| [manifest.json](manifest.json) | Source and complete-packet hashes |
| [checksums.json](checksums.json) | SHA-256 of every other file in this directory |

The output contains {levels.get('limited', 0)} limited, {levels.get('moderate', 0)} moderate and {levels.get('strong', 0)} strong
recommendations. Letter strength is separate from the applicant's CV tier.
Sampling probabilities remain provisional study settings; see
[RECOMMENDATIONS.md](../../RECOMMENDATIONS.md).

## Using the packets

Keep each applicant's packet identical across integrity conditions. The packet
files still begin with the internal applicant identifier, which encodes the
sampling seed. `phd_eval` removes that line and adds the integrity record when it
assembles a prompt; see [EVALUATION.md](../../EVALUATION.md). Do not paste these
files into a prompt by hand.
"""
