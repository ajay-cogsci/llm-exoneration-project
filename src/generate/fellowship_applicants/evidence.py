"""Recorded experience and activity evidence, separate from applicant tier labels."""

RESPONSIBILITY = (
    "Implemented the assigned procedure using a supervisor-provided specification and submitted the working files.",
    "Completed the assigned comparison, interpreted error cases and documented the analysis choices with periodic supervision.",
    "Formulated a diagnostic question, justified a comparison and investigated alternative explanations with periodic supervisory review.",
)
ARTIFACTS = (
    "Working code and a brief implementation note",
    "Reproducible analysis files and a comparative technical report",
    "Reproducible investigation, diagnostic experiments and a report explaining the evidence and limitations",
)
PRACTICE = {
    "initiative": (
        "Worked on the assigned question; the supervisor proposed the next diagnostic step.",
        "Suggested an additional diagnostic check and implemented it after discussing the approach with the supervisor.",
        "Proposed a diagnostic comparison, explained its purpose and recorded what evidence would distinguish alternative explanations.",
    ),
    "independence": (
        "Used step-by-step supervisory guidance to diagnose implementation errors and organize the analysis.",
        "Completed routine implementation independently and sought advice on interpretation and design choices.",
        "Diagnosed implementation problems and justified analysis choices before bringing the results to supervisory review.",
    ),
    "collaboration": (
        "Shared working files for review; collaborators requested additional explanation before they could use the contribution.",
        "Shared code and progress notes, discussed the review comments and incorporated agreed revisions.",
        "Coordinated review of the analysis, resolved integration questions and documented revisions so collaborators could reproduce the work.",
    ),
}

PROJECT_TYPES = {
    "Undergraduate course project": ("undergraduate", (2, 3, 4)),
    "Undergraduate capstone": ("undergraduate", (5, 6, 8)),
    "Undergraduate independent study": ("undergraduate", (3, 4, 6)),
    "Graduate course project": ("graduate", (2, 3)),
}

IMPACT_EVIDENCE = (
    "Prepared a single activity resource and shared it with the organizing group.",
    "Delivered the planned activity, retained the materials and recorded participant questions for revision.",
    "Delivered a sequence of activities, reviewed participant task responses and revised the materials using that feedback.",
)
