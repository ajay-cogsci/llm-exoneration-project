"""Constrained TA wording; credentials and criterion evidence render verbatim."""

import re

from phd_resumes.writing import object_schema


PROMPT_VERSION = "ta-wording-v1"
GENERATOR_INSTRUCTIONS = """Write concise entries for a fictional graduate student's introductory computer science TA application.
This is research stimulus generation. The fixed_record is authoritative. Return only the requested JSON.
Return exactly one entry for each supplied teaching_experience and project, preserving every ID.
Each entry has a short title and exactly two bullets of twelve to thirty words each.
Use only the supplied topic, tasks, tools and scope. You may paraphrase them and give a descriptive title;
do not invent additional work, methods, outputs, skills, grades, achievements, numbers or success claims.
For teaching, describe the assigned activities without claiming that students improved or that the applicant
was an effective teacher. Supervisor feedback is fixed and will be rendered separately. Do not include it
in the bullets, and do not upgrade tutoring/mentoring to an independent course instructor role.
For the project, describe its fixed task scope. Do not claim grading, teaching, deployment, users,
research, publications or awards from a course project. The report/presentation evidence is printed separately.
Do not restate dates, hours, institutions, grades, degrees, availability, interest, or feedback.
Do not add names, demographic information, recommendation letters, integrity history, character praise,
applicant strength labels, selection judgments, or scoring. Do not use digits in titles or bullets.
Maintain the same restrained professional style across all applicants. Empty teaching history means
an empty teaching list. Never fill missing experience. Do not add a narrative introduction or conclusion.
"""

REVIEW_INSTRUCTIONS = """Check the fictional TA application entries against the supplied fixed_record.
Review factual fidelity and internal plausibility only, not applicant merit or hiring likelihood.
Titles and bullets may paraphrase the recorded tasks and topics. Every activity must be supported by
the record. Flag invented duties, skills, methods, credentials, numbers, achievements, outcomes,
research, publications, awards, teaching effectiveness or claims beyond the specified role.
Do not infer teaching experience from a course project or upgrade tutoring to course instruction.
Fixed supervisor feedback and communication observations are synthetic facts rendered separately;
do not demand external proof or require their repetition in bullets. They must not be contradicted.
Do not ask for additional experiences, dates, grades, essays, recommendation letters or personal details.
Return passes=true with issues=[] only when there is no material factual or plausibility problem.
Otherwise return passes=false with concise, specific issues. Never modify the source facts.
"""

REPAIR_INSTRUCTIONS = GENERATOR_INSTRUCTIONS + """
Revise previous_entries to address validation_issues. The fixed_record must remain unchanged.
Return the complete revised JSON, including unaffected entries. Check the two-bullet and word limits.
"""


def content_schema():
    string = {"type": "string"}
    entry = object_schema({"id": string, "title": string, "bullets": {"type": "array", "items": string, "minItems": 2, "maxItems": 2}})
    return object_schema({key: {"type": "array", "items": entry} for key in ("teaching", "projects")})


def validate_content(facts, content):
    errors = []
    if not isinstance(content, dict) or set(content) != {"teaching", "projects"}:
        return ["Expected teaching and projects sections only"]
    for section, source in (("teaching", "teaching_experience"), ("projects", "projects")):
        entries = content[section]
        if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
            errors.append(f"Invalid {section} entries")
            continue
        if sorted(str(e.get("id")) for e in entries) != sorted(e["id"] for e in facts[source]):
            errors.append(f"IDs/counts differ in {section}")
        for entry in entries:
            if set(entry) != {"id", "title", "bullets"} or not isinstance(entry.get("title"), str) or not entry["title"].strip():
                errors.append(f"Invalid fields in {section}")
                continue
            bullets = entry["bullets"]
            if not isinstance(bullets, list) or len(bullets) != 2 or any(not isinstance(b, str) or not 12 <= len(b.split()) <= 30 for b in bullets):
                errors.append(f"Expected two 12-30 word bullets for {entry['id']}")
                continue
            for text in [entry["title"], *bullets]:
                if re.search(r"\d|\n|\r", text) or len(text) > 500:
                    errors.append(f"Unspecified number or invalid text in {entry['id']}")
                if re.search(r"\b(honest|integrity|misconduct|exonerat\w*|accusat\w*|cheating|plagiari\w*|strong applicant|weak applicant|borderline|hiring|admissions|recommendation|publication|published|award\w*)\b", text, re.I):
                    errors.append(f"Treatment, judgment or unsupported credential in {entry['id']}")
    return errors


def render_application(facts, content):
    errors = validate_content(facts, content)
    if errors:
        raise ValueError(str(errors))
    indexes = {key: {entry["id"]: entry for entry in entries} for key, entries in content.items()}
    lines = [f"Applicant {facts['applicant_id']}", "", "EDUCATION"]
    for degree in facts["education"]:
        end_label = "expected completion" if degree["status"] == "enrolled" else "completed"
        lines.append(f"{degree['degree']}, {degree['institution']} | {degree['start']} to {degree['end']} ({end_label})")
    lines.extend([f"Undergraduate GPA: {facts['undergraduate_gpa']:.2f}/{facts['gpa_scale']:.1f}", f"Academic and experience record as of {facts['record_as_of']}.", "Undergraduate relevant coursework: " + "; ".join(f"{c['course']} ({c['grade']})" for c in facts["coursework"]), "", "TECHNICAL SKILLS", ", ".join(facts["technical_skills"]), "", "TEACHING AND TUTORING EXPERIENCE"])
    if not facts["teaching_experience"]:
        lines.append("No previous teaching, tutoring, or TA experience reported.")
    for entry in facts["teaching_experience"]:
        wording = indexes["teaching"][entry["id"]]
        lines.extend([f"{entry['role']}, {entry['organization']} | {entry['start']} to {entry['end']} | {entry['months']} months; {entry['hours_per_week']} hours/week", wording["title"], *["- " + b for b in wording["bullets"]], entry["performance_note"]])
    lines.extend(["", "PROGRAMMING PROJECT"])
    for entry in facts["projects"]:
        wording = indexes["projects"][entry["id"]]
        lines.extend([f"{wording['title']} | {entry['course']}, {entry['date']}", f"Scope: {entry['scope']}.", *["- " + b for b in wording["bullets"]]])
    lines.extend(["", "COMMUNICATION EVIDENCE"])
    for mode in ("written", "oral"):
        evidence = facts["communication_evidence"][mode]
        title = indexes["projects"][evidence["source_project_id"]]["title"]
        lines.append(f"{mode.capitalize()} communication - {evidence['source']} for '{title}': {evidence['observation']}")
    lines.extend(["", "TEACHING INTEREST", facts["teaching_interest"]["statement"], "", "AVAILABILITY FOR THE ADVERTISED DUTIES"])
    names = {"lab_or_discussion_sections": "Lab or discussion sections", "office_hours": "Office hours", "grading_and_feedback": "Grading and feedback", "course_administration": "Course administration"}
    for duty, label in names.items():
        lines.append(f"{label}: {'Available' if facts['availability'][duty] else 'Not available'}.")
    return "\n".join(lines) + "\n"
