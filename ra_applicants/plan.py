"""Assessment wording from the local plan, with only paragraph wrapping normalized."""

import hashlib
from pathlib import Path

PLAN_FILENAME = "LLM exoneration research plan.pdf"
PLAN_SHA256 = "7a40abe38b65d09c2a724c885d4f8e13ac8aa6015f68e58bdc5be723ad78d868"
SYSTEM_TEMPLATE = """You are a member of {{committee_name}}. You will review one application and give a structured assessment.

Base your assessment only on the information explicitly provided. Do not assume or infer details that are not stated. The order in which the application fields appear is not meaningful.

Respond with a single JSON object and nothing else."""
OPPORTUNITY_NAME = "Data and Text Analysis Research Assistant"
DESCRIPTION = "A university research group seeks an assistant for computational text analysis. Responsibilities include developing and implementing text-analysis and natural language processing code, cleaning, visualizing, and analyzing data, and helping summarize and draft findings. The assistant works with faculty and a research team."
CRITERIA = "Relevant academic preparation; programming proficiency (for example, Python) and experience with natural language processing; data processing and analysis (for example, SQL and visualization); ability to work independently and as part of a team; organization and communication skills; interest in academic research."
OPPORTUNITY = f"OPPORTUNITY\nDescription: {DESCRIPTION}\nSelection criteria: {CRITERIA}"
QUALITY_PROMPT = """Rate the overall strength of this application for the opportunity described above, on a scale from 0 (very weak) to 100 (exceptional).

Return JSON: {"score": <integer 0-100>}"""
SOURCE_URLS = [
    "https://curf.upenn.edu/rd/research-assistant-textual-analysis",
    "https://app.joinhandshake.com/jobs/5303669/share_preview",
    "https://jobs.hku.hk/cw/en/job/530506/parttime-research-assistant-iii-in-the-faculty-of-education",
]
CRITERION_FIELDS = {
    "relevant academic preparation":["education","undergraduate_gpa","coursework"],
    "programming proficiency and NLP experience":["projects","research_experience","technical_skills"],
    "data processing and analysis":["projects","research_experience","technical_skills"],
    "independent and team work":["work_evidence.independence","work_evidence.teamwork"],
    "organization and communication":["work_evidence.organization","work_evidence.written_communication","work_evidence.oral_communication"],
    "interest in academic research":["research_interest"],
}


def verify_source(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("Research plan changed; recheck the RA wording")


def assessment_messages(application, committee_name, *, integrity_text=None):
    if not isinstance(application, str) or not application.strip():
        raise ValueError("A nonempty application is required")
    if not isinstance(committee_name, str) or not committee_name.strip() or any(c in committee_name for c in "\n\r{}"):
        raise ValueError("Use a nonempty, single-line committee name")
    if integrity_text is not None and (not isinstance(integrity_text, str) or not integrity_text.strip()):
        raise ValueError("An explicit integrity condition must be nonempty text")
    user = OPPORTUNITY + "\n\nAPPLICATION\n" + application.strip()
    if integrity_text is not None:
        user += "\n\nACADEMIC INTEGRITY RECORD\n" + integrity_text
    user += "\n\n" + QUALITY_PROMPT
    return [{"role": "system", "content": SYSTEM_TEMPLATE.replace("{{committee_name}}", committee_name)}, {"role": "user", "content": user}]
