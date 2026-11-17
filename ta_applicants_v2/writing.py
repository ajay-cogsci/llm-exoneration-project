"""Version 2 wording contract and deterministic application rendering."""

from ta_applicants.writing import (
    GENERATOR_INSTRUCTIONS as BASE_GENERATOR,
    REVIEW_INSTRUCTIONS as BASE_REVIEW,
    content_schema, validate_content,
)

PROMPT_VERSION = "ta-wording-v2"
GENERATOR_INSTRUCTIONS = BASE_GENERATOR + """
Applicants may have multiple projects with different courses, levels, tools and scopes.
Use the tools and duties of the particular entry, not tools from another project.
For team projects describe only the applicant's specified tasks, not sole ownership
or leadership of the team's work. Cover the recorded tasks across the two bullets.
Course level and a degree title do not authorize inflating project sophistication.
"""
REVIEW_INSTRUCTIONS = BASE_REVIEW + """
Check each project against its own tools, course level, task list and individual/team scope.
Do not transfer tools or accomplishments between entries. Check that the specified
tasks are represented without adding technical activities not supported by the record.
"""
REPAIR_INSTRUCTIONS = GENERATOR_INSTRUCTIONS + """
Revise previous_entries to address validation_issues. Preserve every fixed fact.
Return the complete object, including unchanged entries. Check all word limits.
"""


def render_application(facts, content):
    errors = validate_content(facts, content)
    if errors:
        raise ValueError(str(errors))
    indexes = {key:{entry["id"]:entry for entry in entries} for key,entries in content.items()}
    lines = [f"Applicant {facts['applicant_id']}", "", "EDUCATION"]
    for degree in facts["education"]:
        status = "enrolled; expected completion" if degree["status"] == "enrolled" else "completed"
        lines.append(f"{degree['degree']}, {degree['institution']} | {degree['start']} to {degree['end']} ({status})")
    lines += [f"Undergraduate GPA: {facts['undergraduate_gpa']:.2f}/{facts['gpa_scale']:.1f}",f"Academic and experience record as of {facts['record_as_of']}.","", "RELEVANT COURSEWORK"]
    for course in facts["coursework"]:
        lines.append(f"{course['course']}: {course['grade']} | {course['level']}, {course['date']}")
    lines += ["", "TECHNICAL SKILLS", ", ".join(facts["technical_skills"]), "", "TEACHING AND TUTORING EXPERIENCE"]
    if not facts["teaching_experience"]:
        lines.append("No previous teaching, tutoring, or TA experience reported.")
    for entry in facts["teaching_experience"]:
        wording = indexes["teaching"][entry["id"]]
        lines += [f"{entry['role']}, {entry['organization']} | {entry['start']} to {entry['end']} | {entry['months']} months; {entry['hours_per_week']} hours/week",wording["title"],*["- " + b for b in wording["bullets"]]]
    lines += ["", "PROGRAMMING AND COURSE PROJECTS"]
    for entry in facts["projects"]:
        wording = indexes["projects"][entry["id"]]
        lines += [f"{wording['title']} | {entry['course']}, {entry['date']}",f"Scope: {entry['scope']}.","Project tools: " + ", ".join(entry["tools"]),*["- " + b for b in wording["bullets"]]]
    lines += ["", "SUPPORTING APPLICATION EVIDENCE", "", "COMMUNICATION EVIDENCE"]
    for mode in ("written","oral"):
        evidence = facts["communication_evidence"][mode]
        title = indexes["projects"][evidence["source_project_id"]]["title"]
        lines.append(f"{mode.capitalize()} communication - {evidence['source']} for '{title}': {evidence['observation']}")
    lines += ["", "TEACHING PERFORMANCE EVIDENCE"]
    if not facts["teaching_experience"]:
        lines.append("Not applicable: no previous teaching, tutoring, or TA appointment reported.")
    for entry in facts["teaching_experience"]:
        lines.append(f"{entry['role']}, {entry['start']} to {entry['end']} - feedback from {entry['feedback_source']}: {entry['performance_note']}")
    lines += ["", "TEACHING INTEREST", facts["teaching_interest"]["statement"], "", "AVAILABILITY FOR THE ADVERTISED DUTIES"]
    for duty,label in {"lab_or_discussion_sections":"Lab or discussion sections","office_hours":"Office hours","grading_and_feedback":"Grading and feedback","course_administration":"Course administration"}.items():
        lines.append(f"{label}: {'Available' if facts['availability'][duty] else 'Not available'}.")
    return "\n".join(lines) + "\n"
