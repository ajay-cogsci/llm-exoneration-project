"""Fixed evidence vocabulary used by the approved TA sampler."""

GRADES = {grade: index for index, grade in enumerate(["F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"])}

TIERS = ("weak", "borderline", "strong")

EVIDENCE = ("needs_improvement", "satisfactory", "effective")

DUTIES = ("lab_or_discussion_sections", "office_hours", "grading_and_feedback", "course_administration")

INTEREST = {
    "beginner_support": "Interested in helping beginning programmers understand concepts and work through programming difficulties.",
    "general_teaching": "Interested in university teaching; no specific preference for teaching beginning programmers is stated.",
    "undecided": "Undecided about teaching beginning programmers; willing to discuss the responsibilities of the role.",
}

COMMUNICATION = {
    "written": {
        "needs_improvement": "The report required revisions to organize the explanation and clarify terminology.",
        "satisfactory": "The report explained the approach clearly enough to follow, with occasional requests for clarification.",
        "effective": "The report organized the explanation clearly and used examples to explain unfamiliar terminology.",
    },
    "oral": {
        "needs_improvement": "The presentation required prompting to explain the reasoning and respond clearly to questions.",
        "satisfactory": "The presentation explained the approach and addressed questions, with occasional requests for clarification.",
        "effective": "The presentation explained the reasoning clearly and adapted explanations when questions indicated confusion.",
    },
}

PERFORMANCE = {
    "needs_improvement": "Supervisor feedback recorded a need for improvement in explanations and follow-through on assigned teaching tasks.",
    "satisfactory": "Supervisor feedback recorded satisfactory completion of assigned teaching tasks and appropriate responses to student questions.",
    "effective": "Supervisor feedback recorded clear explanations, responsive student support, and effective completion of assigned teaching tasks.",
}

def require(condition, message):
    if not condition:
        raise ValueError(message)
