"""Validate and render draft materials locally. Never instantiates an API client.

python3 scripts/check_phd_followup.py --write-review
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.phd_followup_spec import (  # noqa: E402
    ACKNOWLEDGMENT, CONDITIONS, MODELS, SCENARIOS, SOURCE_CONDITIONS, TASKS, load_manifest,
)
from phd_eval.design import build_design, check_config, load_applicants, messages  # noqa: E402
from phd_resumes.io import digest  # noqa: E402


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_materials(config, original, manifest, root=ROOT):
    check_config(config)
    require(set(manifest) == set(CONDITIONS), "Unexpected manifest")
    require(config["followup"]["review_status"] == "draft_pending_user_review", "This validator is for the draft review stage")
    require(config["followup"]["api_run_authorized"] is False, "Draft must not declare launch approval")
    for field in ("version", "system_message", "dataset", "cv_dataset", "opportunity",
                  "record_heading", "record_position", "incident_month", "order_seed"):
        require(config[field] == original[field], f"Preserved field changed: {field}")
    require(config["tasks"] == {t: original["tasks"][t] for t in TASKS}, "Selected task definitions changed")
    require(config["formats"] == {"answer_only": original["formats"]["answer_only"]}, "Selected format changed")
    require(config["request_parameters"] == {}, "Request parameters must remain empty")
    require(len(config["models"]) == 4 and {m["label"]: m["api_model"] for m in config["models"]} == MODELS,
            "Models differ from the agreed selection")
    conditions = {c["id"]: c for c in config["conditions"]}
    require(set(conditions) == set(CONDITIONS), "Expected exactly 20 condition IDs")
    require(all(len(c["wordings"]) == 2 for c in conditions.values()), "Expected two wordings each")
    old = {c["id"]: c for c in original["conditions"]}
    for condition, source in SOURCE_CONDITIONS.items():
        require(conditions[condition]["wordings"] == old[source]["wordings"], f"Reused text changed: {condition}")
    for scenario in SCENARIOS:
        for i in range(2):
            require(conditions[f"{scenario}_acknowledged"]["wordings"][i] ==
                    conditions[f"{scenario}_appeal"]["wordings"][i] + ACKNOWLEDGMENT[i],
                    f"Acknowledgment is not a one-sentence addition: {scenario}, wording {i + 1}")
    applicants = load_applicants(config, root)
    require(len(applicants) == 100, "Expected the same 100 applicants")
    design = build_design(config, applicants)  # In memory only; no plan directory.
    require(len(design) == 8000 and len({r["request_id"] for r in design}) == 8000,
            "Unexpected or duplicate design cells")
    require(all(v == 400 for v in Counter(r["condition"] for r in design).values()), "Unbalanced conditions")
    require(all(r["format"] == "answer_only" and r["repeat"] == 1 for r in design), "Unexpected format or repeat")
    require({r["task"] for r in design} == set(TASKS), "Unexpected task")
    require({r["wording"] for r in design} == {1, 2}, "Unexpected wording")
    by_applicant = {a["applicant_id"]: a for a in applicants}
    remainders = {}
    reuse_checks = 0
    for row in design:
        applicant = by_applicant[row["applicant_id"]]
        condition, wording, task = row["condition"], row["wording"], row["task"]
        chat = messages(config, applicant, condition, wording, task, "answer_only")
        record = config["record_heading"] + "\n" + conditions[condition]["wordings"][wording - 1]
        require(chat[1]["content"].count(record) == 1, "Record is missing or duplicated")
        remainder = (chat[0]["content"], chat[1]["content"].replace(record, "<RECORD>"))
        key = (row["applicant_id"], task)
        require(remainders.setdefault(key, remainder) == remainder, "A prompt changed outside the record block")
        require(row["applicant_id"] not in chat[1]["content"], "Internal applicant identifier leaked")
        if condition in SOURCE_CONDITIONS:
            expected = messages(original, applicant, SOURCE_CONDITIONS[condition], wording, task, "answer_only")
            require(chat == expected, f"Reused assembled prompt changed: {row['request_id']}")
            reuse_checks += 1
    return {
        "status": "OFFLINE DRAFT CHECKS PASSED; WORDING APPROVAL STILL REQUIRED",
        "api_requests_sent": 0, "plan_directory_created": False,
        "config_hash": digest(config), "design_hash": digest(design),
        "applicants": len(applicants), "applicants_by_tier": dict(Counter(a["cv_tier"] for a in applicants)),
        "conditions": len(conditions), "wordings": 40, "requests_per_model": len(design),
        "models": len(MODELS), "requests_total": len(design) * len(MODELS),
        "prompts_checked_for_record_only_changes": len(design), "exact_reused_prompt_checks": reuse_checks,
        "acknowledgment_pairs_checked": 6,
        "limitations": ["Mechanical validation does not establish equal severity or semantic equivalence.",
                        "No live model availability, prices, credentials, or budget checks were performed."],
        "record_word_counts": {c: [len(w.split()) for w in conditions[c]["wordings"]] for c in CONDITIONS},
    }


def render_wordings(config, manifest):
    lines = ["# Exact PhD follow-up wording — DRAFT", "",
             "Review pending. No API run is authorized. Generated from `configs/phd_eval_followup_v1.json`.", "",
             "The 40 blocks below are the exact record text, without abbreviations or placeholders. Each appears under the existing `INSTITUTIONAL RECORD` heading. Model prompts do not contain the IDs, state labels, or the review notes below.", "",
             "## Design", "",
             "Three scenarios × six states + two shared controls = 20 conditions. Each has two wordings. The same 100 applicants receive quality and advance prompts in answer-only format, with one repeat: 8,000 requests per model. Four models are planned. No requests have been sent.", "",
             "## Points requiring human review", "",
             "- Routine verification supplies favorable evidence without accusation history. It is not the same as the short clean baseline.",
             "- The original AI-use texts are copied exactly. They use the academic integrity office; the two new scenarios use a university review panel.",
             "- Fabrication and technical-error records share coursework, evidence sources, a review panel, and a zero assignment grade after an adverse finding. This does not establish equal perceived severity.",
             "- Every technical-error record explicitly says no dishonesty or academic misconduct was alleged. This prevents an integrity interpretation, but also adds text and may itself reassure the evaluator.",
             "- The original clean record rules out integrity allegations; it does not explicitly rule out competence concerns. Therefore technical-error versus clean is descriptive. Technical-error versus its routine-verification control is the primary comparison.",
             "- The verified and cleared records match the favorable factual conclusion within scenario. They are not exactly equal in length. Original AI appeal text also says additional/conclusive evidence; that wording is preserved for replication.",
             "- No record names a CV project or letter writer. The model can still infer a connection; this follow-up does not experimentally remove that possibility.",
             "- These are new descriptions on the existing applicant bank, not new applicants or a staged belief-updating experiment.", "",
             "## Record meanings", "",
             "| State | What is established | Finding / grade consequence |",
             "|---|---|---|",
             "| verified | Favorable evidence from routine review; no prior allegation/concern | No adverse finding or penalty |",
             "| pending | Concern unresolved | No finding or penalty yet |",
             "| confirmed | Misconduct or honest error established | Zero on the assignment |",
             "| cleared | Alleged conduct/error did not occur | No adverse finding or penalty |",
             "| appeal | Initial adverse finding was factually wrong | Finding reversed; zero and record consequences corrected |",
             "| acknowledged | Same as appeal plus written institutional acknowledgment | Same correction as appeal |", ""]
    for condition in config["conditions"]:
        cid = condition["id"]
        source = manifest[cid]["source_condition"]
        lines += [f"## {cid}", "", f"**{condition['label']}**", "",
                  f"Provenance: {'verbatim from original ' + source if source else 'new draft wording'}.", ""]
        for i, text in enumerate(condition["wordings"], 1):
            lines += [f"### Wording {i}", "", text, ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true", help="Regenerate the repository wording review file")
    parser.add_argument("--report", type=Path, help="Optional local JSON report path")
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/phd_eval_followup_v1.json").read_text())
    original = json.loads((ROOT / "configs/phd_eval_v1.json").read_text())
    manifest = load_manifest()
    report = validate_materials(config, original, manifest)
    if args.write_review:
        path = ROOT / "docs/phd_followup/WORDINGS.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_wordings(config, manifest), encoding="utf-8")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
