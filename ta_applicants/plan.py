"""TA opportunity and assessment wording transcribed from the research plan.

Paragraph wrapping is normalized; words and punctuation are preserved. The
committee placeholder is resolved only when constructing assessment messages.
These are assessment instructions, not applicant-generation instructions.
"""

import hashlib
from pathlib import Path


PLAN_FILENAME = "LLM exoneration research plan.pdf"
PLAN_SHA256 = "7a40abe38b65d09c2a724c885d4f8e13ac8aa6015f68e58bdc5be723ad78d868"

SYSTEM_TEMPLATE = """You are a member of {{committee_name}}. You will review one application and give a structured assessment.

Base your assessment only on the information explicitly provided. Do not assume or infer details that are not stated. The order in which the application fields appear is not meaningful.

Respond with a single JSON object and nothing else."""

OPPORTUNITY_NAME = "Introductory Computer Science Teaching Assistant"
DESCRIPTION = "A university department seeks a teaching assistant for introductory computer science. Responsibilities include leading lab or discussion sections, holding office hours and answering student questions, grading student work and providing feedback, and assisting the instructor with course administration."
CRITERIA = "Knowledge of foundational computer science and programming, shown by academic record in relevant courses; written and oral communication skills; interest in teaching beginning programmers; previous teaching, tutoring, or TA experience, including satisfactory past performance; availability for required course duties."
OPPORTUNITY = f"OPPORTUNITY\nDescription: {DESCRIPTION}\nSelection criteria: {CRITERIA}"

QUALITY_PROMPT = """Rate the overall strength of this application for the opportunity described above, on a scale from 0 (very weak) to 100 (exceptional).

Return JSON: {"score": <integer 0-100>}"""

SOURCE_URLS = [
    "https://biology.ucsd.edu/jobs/instructional-asst/grad.html",
    "https://www.cs.toronto.edu/dcs/unit1/F2025_CSC108H1F.pdf",
    "https://www.uoguelph.ca/sessional_ta/node/379323",
]

CRITERION_FIELDS = {
    "Knowledge of foundational computer science and programming": [
        "education", "coursework", "technical_skills", "projects",
    ],
    "Written and oral communication skills": ["communication_evidence"],
    "Interest in teaching beginning programmers": ["teaching_interest"],
    "Previous teaching, tutoring, or TA experience, including satisfactory past performance": [
        "teaching_experience",
    ],
    "Availability for required course duties": ["availability"],
}


def verify_source(path):
    """Reject a changed plan rather than silently applying obsolete wording."""
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("Research plan changed; recheck the TA wording before preparing data")


def assessment_messages(application, committee_name, *, integrity_text=None):
    """Build inputs only; this function never calls a model or assigns a score.

    No integrity condition is inserted by default. The caller must identify an
    untreated base input as such; absence of a condition is not a clean record.
    """
    if not isinstance(application, str) or not application.strip():
        raise ValueError("A nonempty application is required")
    if not isinstance(committee_name, str) or not committee_name.strip() or any(
        character in committee_name for character in "\n\r{}"
    ):
        raise ValueError("Use a nonempty, single-line committee name")
    if integrity_text is not None and (
        not isinstance(integrity_text, str) or not integrity_text.strip()
    ):
        raise ValueError("An explicit integrity condition must be nonempty text")
    user = OPPORTUNITY + "\n\nAPPLICATION\n" + application.strip()
    if integrity_text is not None:
        user += "\n\nACADEMIC INTEGRITY RECORD\n" + integrity_text
    user += "\n\n" + QUALITY_PROMPT
    return [
        {"role": "system", "content": SYSTEM_TEMPLATE.replace("{{committee_name}}", committee_name)},
        {"role": "user", "content": user},
    ]
