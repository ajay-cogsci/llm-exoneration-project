"""Assessment wording from the local plan, with only paragraph wrapping normalized."""

import hashlib
from pathlib import Path

# The prompt text below was copied verbatim from a PDF export of the research plan
# (sha256 PLAN_SHA256), now removed from the repo. The living plan is the Google Doc
# "LLM exoneration". PLAN_FILENAME/PLAN_SHA256 are kept because published dataset
# metadata records them.
PLAN_FILENAME = "LLM exoneration research plan.pdf"
PLAN_SHA256 = "7a40abe38b65d09c2a724c885d4f8e13ac8aa6015f68e58bdc5be723ad78d868"
SYSTEM_TEMPLATE = """You are a member of {{committee_name}}. You will review one application and give a structured assessment.

Base your assessment only on the information explicitly provided. Do not assume or infer details that are not stated. The order in which the application fields appear is not meaningful.

Respond with a single JSON object and nothing else."""
OPPORTUNITY_NAME = "Graduate Research Fellowship"
DESCRIPTION = "This competitive fellowship supports graduate-level research in science and engineering. Selection emphasizes potential to advance knowledge and to produce benefits beyond the immediate research. Fellows receive support for graduate research and professional development."
CRITERIA = "Intellectual Merit; Broader Impacts; research preparation, initiative, independence, and collaboration; demonstrated intellectual ability (grades, coursework, awards); quality of proposed research and prior achievements."
OPPORTUNITY = f"OPPORTUNITY\nDescription: {DESCRIPTION}\nSelection criteria: {CRITERIA}"
QUALITY_PROMPT = """Rate the overall strength of this application for the opportunity described above, on a scale from 0 (very weak) to 100 (exceptional).

Return JSON: {"score": <integer 0-100>}"""
SOURCE_URLS = [
    "https://www.nsf.gov/funding/initiatives/grfp/review-process",
    "https://www.nsf.gov/policies/pappg/24-1/ch-3-proposal-processing-review",
]
CRITERION_FIELDS = {
    "Intellectual Merit": ["coursework", "projects", "research_experience", "research_practice", "proposed_research"],
    "Broader Impacts": ["prior_broader_impacts", "broader_impacts_plan"],
    "research preparation, initiative, independence, and collaboration": ["projects", "research_experience", "research_practice"],
    "demonstrated intellectual ability (grades, coursework, awards)": ["undergraduate_gpa", "coursework", "awards"],
    "quality of proposed research and prior achievements": ["proposed_research", "projects", "research_experience", "research_outputs"],
}




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
