"""Offline fellowship loading, prompt assembly and balanced design."""

import hashlib
import random
import re
from pathlib import Path

from fellowship_applicants.plan import CRITERIA, DESCRIPTION, SYSTEM_TEMPLATE
from phd_eval.design import check_config as check_shared_schema
from phd_eval.design import fill, record_block, require, task_text
from phd_resumes.io import digest, read_json, read_jsonl

from phd_resumes.io import PROJECT as ROOT  # noqa: E402
DATASET = "data/fellowship"
SHARED = ("system_message", "conditions", "tasks", "formats", "record_heading",
          "record_position", "incident_month", "order_seed", "request_parameters")
PLACEHOLDERS = {
    "committee_name": "the Graduate Research Fellowship Selection Committee",
    "next_stage": "final fellowship selection review",
    "offer_verb": "award this applicant the fellowship",
    "yes_word": "award", "no_word": "decline",
}


def check_config(config):
    require(config.get("version") == "fellowship-eval-v1", "Unsupported fellowship config")
    # Reuse validation of the shared schema, without changing the frozen PhD code.
    check_shared_schema({**config, "version": "phd-eval-v1"})
    reference = read_json(ROOT / "configs/phd_eval_v1.json")
    require(all(config[k] == reference[k] for k in SHARED), "Shared PhD experiment text/settings changed")
    require(config["system_message"] == SYSTEM_TEMPLATE, "Fellowship system template differs")
    require(config["dataset"] == DATASET, "Use the published fellowship v2 bank")
    opportunity = config["opportunity"]
    require(opportunity["id"] == "graduate_research_fellowship", "Wrong opportunity")
    require(opportunity["description"] == DESCRIPTION and opportunity["selection_criteria"] == CRITERIA,
            "Fellowship opportunity text changed")
    require(opportunity["placeholders"] == PLACEHOLDERS, "Fellowship role substitutions changed")
    require(config["review_month"] == "2026-11", "Unexpected review month")


def application_text(applicant):
    """Remove one exact internal-ID line; preserve every other character."""
    pid = applicant["applicant_id"]
    lines = applicant["packet"].splitlines(keepends=True)
    header = f"Applicant {pid}"
    require(sum(line.rstrip("\r\n") == header for line in lines) == 1,
            f"Expected one applicant identifier line: {pid}")
    body = "".join(line for line in lines if line.rstrip("\r\n") != header)
    require(not re.search(r"FEL-v2-|PHDv3-|designated_mixed_pattern|rubric_hash|latent_academic_level|Provisional study tier", body),
            f"Research metadata leaked into application: {pid}")
    return body


def load_applicants(config, root=ROOT):
    check_config(config)
    folder = Path(root) / config["dataset"]
    checksums = read_json(folder / "checksums.json")
    actual = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in folder.rglob("*") if p.is_file() and p.name != "checksums.json"}
    require(actual == checksums, "Published fellowship inventory/checksum mismatch")
    profiles = read_jsonl(folder / "profiles.jsonl")
    manifest = read_json(folder / "application_manifest.json")
    by_id = {r["profile_id"]: r for r in profiles}
    require(len(by_id) == len(profiles) == len(manifest) == 100, "Expected 100 unique fellowship applicants")
    require({r["profile_id"] for r in manifest} == set(by_id), "Manifest/profile IDs differ")
    applicants = []
    for item in manifest:
        pid = item["profile_id"]
        require(item["application"] == f"applications/{pid}.txt", "Unexpected application path")
        row = by_id[pid]
        packet = (folder / item["application"]).read_text(encoding="utf-8")
        require(digest(packet) == item["application_hash"], f"Application changed: {pid}")
        require(item["facts_hash"] == row["facts_hash"] == digest(row["facts"]), f"Facts changed: {pid}")
        require(row["strength"] == row["rubric"]["tier"], f"Tier metadata differs: {pid}")
        graduate = [d for d in row["facts"]["education"] if d["degree"].startswith(("MS ", "PhD "))]
        for month in (config["incident_month"], config["review_month"]):
            require(any(d["start"] <= month <= d["end"] for d in graduate), f"Not enrolled in {month}: {pid}")
        applicant = {"applicant_id": pid, "packet": packet, "application_hash": digest(packet),
                     "facts": row["facts"], "facts_hash": row["facts_hash"],
                     "cv_tier": row["strength"], "pathway": graduate[-1]["degree"],
                     "research_area": row["facts"]["proposed_research"]["area"]}
        applicant["evaluator_text_hash"] = digest(application_text(applicant))
        applicants.append(applicant)
    return sorted(applicants, key=lambda a: a["applicant_id"])


def messages(config, applicant, condition, wording, task, style):
    conditions = {c["id"]: c for c in config["conditions"]}
    require(condition in conditions, "Unknown condition")
    require(type(wording) is int and 1 <= wording <= len(conditions[condition]["wordings"]), "Unknown wording")
    require(task in config["tasks"] and style in config["formats"], "Unknown task or format")
    opportunity = config["opportunity"]
    parts = ["OPPORTUNITY\nDescription: " + opportunity["description"] +
             "\nSelection criteria: " + opportunity["selection_criteria"],
             "APPLICATION\n\n" + application_text(applicant),
             record_block(config, condition, wording), task_text(config, task, style)]
    return [{"role": "system", "content": fill(config["system_message"], opportunity["placeholders"])},
            {"role": "user", "content": "\n\n".join(parts)}]


def pilot_subset(applicants, per_tier, seed):
    require(type(per_tier) is int and per_tier > 0, "per-tier must be positive")
    chosen = []
    for tier in ("weak", "borderline", "strong"):
        group = [a for a in applicants if a["cv_tier"] == tier]
        require(len(group) >= per_tier, f"Too few {tier} applicants")
        chosen.extend(random.Random(f"fellowship-eval-pilot:{seed}:{tier}").sample(group, per_tier))
    return sorted(chosen, key=lambda a: a["applicant_id"])


def build_design(config, applicants, conditions=None, wordings=None, tasks=None, formats=None, repeats=1):
    check_config(config)
    roles = {c["id"]: c["role"] for c in config["conditions"]}
    conditions = list(roles) if conditions is None else conditions
    wordings = [1, 2] if wordings is None else wordings
    tasks = list(config["tasks"]) if tasks is None else tasks
    formats = list(config["formats"]) if formats is None else formats
    require("clean" in conditions and set(conditions) <= roles.keys(), "Unknown condition or missing clean")
    require(set(wordings) <= {1, 2} and all(type(w) is int for w in wordings), "Unknown wording")
    require(set(tasks) <= config["tasks"].keys() and set(formats) <= config["formats"].keys(), "Unknown task or format")
    require(all(x and len(x) == len(set(x)) for x in (conditions, wordings, tasks, formats)), "Empty or duplicate design dimension")
    require(type(repeats) is int and repeats > 0, "repeats must be positive")
    rows = []
    for a in applicants:
        for condition in conditions:
            for wording in wordings:
                for task in tasks:
                    for style in formats:
                        phash = digest(messages(config, a, condition, wording, task, style))
                        for repeat in range(1, repeats + 1):
                            rows.append({"request_id": f"{a['applicant_id']}|{condition}|w{wording}|{task}|{style}|r{repeat}",
                                         **{k: a[k] for k in ("applicant_id", "cv_tier", "pathway", "research_area")},
                                         "condition": condition, "condition_role": roles[condition], "wording": wording,
                                         "task": task, "format": style, "repeat": repeat, "prompt_hash": phash})
    random.Random(f"phd-eval-order:{config['order_seed']}").shuffle(rows)
    return rows
