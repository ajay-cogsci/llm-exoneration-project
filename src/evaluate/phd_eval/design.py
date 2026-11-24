"""Prompt assembly and the experimental design for the PhD opportunity.

A prompt is fully determined by (applicant, condition, wording, task, format)
and the saved configuration. Across integrity conditions the only text that
differs for an applicant is the record block.
"""

import random
import re
from pathlib import Path

from phd_resumes.io import digest, read_json, read_jsonl

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
ROLES = {"baseline", "primary", "secondary", "exploratory", "control"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fill(text, values):
    def replace(match):
        require(match.group(1) in values, f"Unfilled placeholder: {match.group(1)}")
        return values[match.group(1)]
    return PLACEHOLDER.sub(replace, text)


def check_config(config):
    require(config.get("version") == "phd-eval-v1", "Unsupported evaluation configuration")
    values = config["opportunity"]["placeholders"]
    fill(config["system_message"], values)
    require(config["record_position"] in {"end", "after_cv"}, "record_position must be 'end' or 'after_cv'")
    ids = [c["id"] for c in config["conditions"]]
    require(len(ids) == len(set(ids)) and "clean" in ids, "Conditions need unique ids and a 'clean' baseline")
    for condition in config["conditions"]:
        require(re.fullmatch(r"[a-z_]+", condition["id"]) and condition["role"] in ROLES, f"Invalid condition: {condition['id']}")
        wordings = condition["wordings"]
        require(isinstance(wordings, list) and wordings and all(isinstance(w, str) and w.strip() and "\n" not in w for w in wordings) and len(set(wordings)) == len(wordings), f"Invalid wordings: {condition['id']}")
    require(len({len(c["wordings"]) for c in config["conditions"]}) == 1, "Every condition needs the same number of wordings")
    for name, task in config["tasks"].items():
        prompt = fill(task["prompt"], values)
        require(prompt.count("Return JSON: {") == 1 and f'"{task["score_key"]}"' in prompt, f"Task {name} must state its JSON format once")
        if task["decision_key"]:
            require(f'"{task["decision_key"]}"' in prompt, f"Task {name} must name its decision key")
    for name, style in config["formats"].items():
        require((style["instruction"] is None) == (style["rationale_key"] is None), f"Format {name} is inconsistent")
    require(type(config["order_seed"]) is int, "order_seed must be an integer")
    require(isinstance(config["request_parameters"], dict), "request_parameters must be an object")


def load_applicants(config, root="."):
    """Read packets and the analysis labels. Labels never enter a prompt."""
    root = Path(root)
    packets, cvs = root / config["dataset"], root / config["cv_dataset"]
    manifest = read_json(packets / "manifest.json")
    profiles = {row["profile_id"]: row for row in read_jsonl(cvs / "profiles.jsonl")}
    require({m["applicant_id"] for m in manifest} == set(profiles), "Packet and CV datasets describe different applicants")
    applicants = []
    for item in manifest:
        pid = item["applicant_id"]
        packet = (packets / "applications" / f"{pid}.txt").read_text(encoding="utf-8")
        require(digest(packet) == item["application_hash"], f"Packet changed since export: {pid}")
        row = profiles[pid]
        require(item["facts_hash"] == row["facts_hash"], f"Packet was built from a different CV record: {pid}")
        applicants.append({"applicant_id": pid, "packet": packet, "application_hash": item["application_hash"], "facts": row["facts"], "cv_tier": row["rubric"]["tier"], "pathway": row["pathway"], "research_area": row["facts"]["research_area"]})
    return sorted(applicants, key=lambda a: a["applicant_id"])


def application_text(applicant):
    """Packet without the internal identifier, split into CV and letters."""
    pid = applicant["applicant_id"]
    header = f"Applicant {pid}"
    lines = applicant["packet"].split("\n")
    require(lines.count(header) == 2, f"Expected two identifier lines in {pid}")
    body = "\n".join(line for line in lines if line != header)
    require(pid not in body and "PHDv3" not in body and body.count("RECOMMENDATION SUMMARIES") == 1, f"Identifier leakage in {pid}")
    cv, letters = body.split("RECOMMENDATION SUMMARIES")
    return re.sub(r"\n{3,}", "\n\n", cv).strip(), "RECOMMENDATION SUMMARIES\n\n" + re.sub(r"\n{3,}", "\n\n", letters).strip()


def check_feasible(config, applicant):
    """Every condition places a course-related event in the incident month."""
    month = config["incident_month"]
    require(any(d["start"] <= month <= d["end"] for d in applicant["facts"]["education"]), f"{applicant['applicant_id']} is not enrolled in {month}")


def task_text(config, task, style):
    values = config["opportunity"]["placeholders"]
    prompt = fill(config["tasks"][task]["prompt"], values)
    form = config["formats"][style]
    if form["rationale_key"]:
        prompt = prompt.replace("Return JSON: {", f'Return JSON: {{"{form["rationale_key"]}": "{form["rationale_placeholder"]}", ', 1)
        prompt = form["instruction"] + "\n\n" + prompt
    return prompt


def record_block(config, condition, wording):
    conditions = {c["id"]: c for c in config["conditions"]}
    return config["record_heading"] + "\n" + conditions[condition]["wordings"][wording - 1]


def messages(config, applicant, condition, wording, task, style):
    opportunity = config["opportunity"]
    cv, letters = application_text(applicant)
    record = record_block(config, condition, wording)
    parts = ["OPPORTUNITY\nDescription: " + opportunity["description"] + "\nSelection criteria: " + opportunity["selection_criteria"], "APPLICATION\n\n" + cv]
    parts += [letters, record] if config["record_position"] == "end" else [record, letters]
    parts.append(task_text(config, task, style))
    return [{"role": "system", "content": fill(config["system_message"], opportunity["placeholders"])}, {"role": "user", "content": "\n\n".join(parts)}]


def pilot_subset(applicants, per_tier, seed):
    chosen = []
    for tier in ("weak", "borderline", "strong"):
        group = [a for a in applicants if a["cv_tier"] == tier]
        require(len(group) >= per_tier, f"Only {len(group)} {tier} applicants")
        chosen += random.Random(f"phd-eval-pilot:{seed}:{tier}").sample(group, per_tier)
    return sorted(chosen, key=lambda a: a["applicant_id"])


def build_design(config, applicants, conditions=None, wordings=None, tasks=None, formats=None, repeats=1):
    """Fully crossed within-applicant design, in a seeded random order so that
    provider drift during a run is not aligned with condition."""
    check_config(config)
    known = [c["id"] for c in config["conditions"]]
    roles = {c["id"]: c["role"] for c in config["conditions"]}
    conditions = conditions or known
    wordings = wordings or list(range(1, len(config["conditions"][0]["wordings"]) + 1))
    tasks, formats = tasks or list(config["tasks"]), formats or list(config["formats"])
    require(set(conditions) <= set(known) and "clean" in conditions, "Unknown condition, or the clean baseline was dropped")
    require(set(tasks) <= set(config["tasks"]) and set(formats) <= set(config["formats"]), "Unknown task or format")
    require(all(type(w) is int and 1 <= w <= len(config["conditions"][0]["wordings"]) for w in wordings), "Unknown wording")
    require(type(repeats) is int and repeats >= 1, "repeats must be a positive integer")
    rows = []
    for applicant in applicants:
        check_feasible(config, applicant)
        for condition in conditions:
            for wording in wordings:
                for task in tasks:
                    for style in formats:
                        prompt_hash = digest(messages(config, applicant, condition, wording, task, style))
                        for repeat in range(1, repeats + 1):
                            rows.append({"request_id": f"{applicant['applicant_id']}|{condition}|w{wording}|{task}|{style}|r{repeat}", "applicant_id": applicant["applicant_id"], "cv_tier": applicant["cv_tier"], "pathway": applicant["pathway"], "research_area": applicant["research_area"], "condition": condition, "condition_role": roles[condition], "wording": wording, "task": task, "format": style, "repeat": repeat, "prompt_hash": prompt_hash})
    random.Random(f"phd-eval-order:{config['order_seed']}").shuffle(rows)
    return rows
