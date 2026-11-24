"""Constrained API prompts, content validation, and deterministic CV rendering."""

import re

PROMPT_VERSION = "phd-cv-1"

GENERATOR_INSTRUCTIONS = """Write fictional PhD-applicant CV entries from the supplied fixed record.
This is research stimulus generation. All people, projects and publication titles are fictional.
Return JSON conforming to the schema. Return one item for every supplied entry, with exactly its ID.
The Python program will render all degrees, grades, dates, roles, organizations, publication venues,
authorship positions and counts from the fixed record. Do not restate or change those fields.
Your task is to invent coherent, specific titles and concise technical descriptions within the
supplied research area, contribution, work domain and project scope. Match sophistication to the
stated contribution; do not inflate assigned implementation work into independent method creation.
Each experience/project gets exactly two factual CV bullets of 12 to 30 words each.
Publication titles must correspond to the referenced research entry. Multiple publications may
describe different aspects of that work. Use realistic methods appropriate to the research area.
You may invent technical subject matter, methods and qualitative activities; do not invent numerical
results, awards, extra outputs, skills, named people, employers, universities, or prestigious venues.
Do not imply a publication for a project unless the fixed record explicitly links one to it.
For nontechnical work, describe actual operations duties without adding software/research tasks.
Use a consistent professional tone. Do not include strength labels, an admissions judgment,
recommendations, essays, personal identity details, character praise, or academic-integrity history.
Empty source lists must produce empty corresponding output lists.
"""

REVIEW_INSTRUCTIONS = """Check the fictional CV entries against the fixed applicant record.
Assess fidelity and internal plausibility, not applicant merit or admission likelihood.
Allowed inventions are fictional research/project/publication titles, technical subject matter,
methods consistent with stated skills, and qualitative activities within the supplied contribution.
Flag changed or extra credentials, numerical achievements, invented institutions or collaborators,
unlisted publications/awards, inflated contribution, inconsistent technical/nontechnical work,
publication titles unrelated to their linked research, contradictory chronology, and character or
academic-integrity claims. Do not demand that fictional projects/publications exist in real life.
Return passes=true and issues=[] only if no material problem is found. Otherwise passes=false and
list concise, specific issues. Never silently repair or rewrite the applicant record.
"""


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def content_schema():
    text = {"type": "string"}
    entry = object_schema({"id": text, "title": text, "bullets": {"type": "array", "items": text}})
    publication = object_schema({"id": text, "title": text})
    return object_schema({key: {"type": "array", "items": publication if key == "publications" else entry} for key in ("research", "publications", "work", "projects")})


def review_schema():
    return object_schema({"passes": {"type": "boolean"}, "issues": {"type": "array", "items": {"type": "string"}}})


def validate_content(facts, content):
    errors = []
    mapping = {"research": "research_experience", "publications": "publications", "work": "work_experience", "projects": "projects"}
    if not isinstance(content, dict) or set(content) != set(mapping):
        return ["Output sections do not match the schema"]
    for section, source in mapping.items():
        entries = content[section]
        if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
            errors.append(f"Invalid entries in {section}")
            continue
        ids = [e.get("id") for e in entries]
        expected = [e["id"] for e in facts[source]]
        if sorted(map(str, ids)) != sorted(expected):
            errors.append(f"IDs/counts differ in {section}")
        for entry in entries:
            required = {"id", "title"} if section == "publications" else {"id", "title", "bullets"}
            if set(entry) != required or not isinstance(entry.get("title"), str) or not entry["title"].strip():
                errors.append(f"Invalid fields in {section}")
                continue
            texts = [entry["title"]]
            if section != "publications":
                bullets = entry.get("bullets")
                if not isinstance(bullets, list) or len(bullets) != 2 or any(not isinstance(b, str) or not 12 <= len(b.split()) <= 30 for b in bullets):
                    errors.append(f"Expected two 12-30 word bullets for {entry['id']}")
                else:
                    texts.extend(bullets)
            for text in texts:
                if re.search(r"\b(honest|integrity|misconduct|exonerat\w*|accusat\w*|cheating|strong applicant|weak applicant|borderline applicant)\b", text, re.I):
                    errors.append(f"Treatment or strength leakage in {entry['id']}")
                if re.search(r"\d", text):
                    errors.append(f"Unspecified numerical detail in {entry['id']}")
                if "\n" in text or len(text) > 500:
                    errors.append(f"Invalid CV text in {entry['id']}")
    return errors


def render_cv(facts, content=None):
    """The renderer alone prints the fixed credentials; labels never enter the CV."""
    indexes = {key: {entry["id"]: entry for entry in entries} for key, entries in (content or {}).items()}
    lines = [f"Applicant {facts['applicant_id']}", "", "EDUCATION"]
    for degree in facts["education"]:
        lines.append(f"{degree['degree']}, {degree['institution']} | {degree['start']} to {degree['end']} ({degree['status']})")
    lines += [f"Undergraduate GPA: {facts['gpa']:.2f}/{facts['gpa_scale']:.1f} (record as of {facts['gpa_as_of']})", "Relevant coursework: " + "; ".join(f"{c['course']} ({c['grade']})" for c in facts["coursework"]), "", "RESEARCH INTERESTS", facts["research_area"], "", "RESEARCH EXPERIENCE"]
    if not facts["research_experience"]:
        lines.append("None reported.")
    for entry in facts["research_experience"]:
        lines.append(f"{entry['role']}, {entry['organization']} | {entry['start']} to {entry['end']} | {entry['hours_per_week']} hours/week")
        description = indexes.get("research", {}).get(entry["id"])
        lines.append(description["title"] if description else f"Research in {facts['research_area']}")
        lines.append(f"Contribution: {entry['contribution']}.")
        if description:
            lines.extend("- " + b for b in description["bullets"])
    lines += ["", "PUBLICATIONS"]
    if not facts["publications"]:
        lines.append("None reported.")
    for entry in facts["publications"]:
        description = indexes.get("publications", {}).get(entry["id"])
        title = description["title"] if description else f"Publication {entry['id']} (title pending API generation)"
        lines.append(f"{title}. {entry['venue']}, {entry['date']}; {entry['status']}; author position {entry['author_position']}.")
    lines += ["", "WORK EXPERIENCE"]
    if not facts["work_experience"]:
        lines.append("None reported.")
    for entry in facts["work_experience"]:
        lines.append(f"{entry['role']}, {entry['organization']} | {entry['start']} to {entry['end']} | {entry['hours_per_week']} hours/week")
        description = indexes.get("work", {}).get(entry["id"])
        if description:
            lines.append(description["title"])
            lines.extend("- " + b for b in description["bullets"])
    lines += ["", "TECHNICAL PROJECTS"]
    for entry in facts["projects"]:
        description = indexes.get("projects", {}).get(entry["id"])
        title = description["title"] if description else f"Project {entry['id']} (title pending API generation)"
        lines.append(f"{title} | {entry['kind']}, {entry['year']}")
        if description:
            lines.extend("- " + b for b in description["bullets"])
        else:
            lines.append(f"Scope: {entry['scope']}.")
    lines += ["", "TECHNICAL SKILLS", ", ".join(facts["skills"])]
    return "\n".join(lines) + "\n"
