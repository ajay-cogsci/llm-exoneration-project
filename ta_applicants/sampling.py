"""Seeded graduate TA facts, an explicit criterion rubric, and quota selection."""

import math
import random
from collections import Counter
from datetime import date

from phd_resumes.io import digest
from phd_resumes.sampling import month_index, month_string


GRADES = {grade: index for index, grade in enumerate(["F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"])}
LEVELS = ("low", "adequate", "high")
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
ROLE_TASKS = {
    "Teaching Assistant": ["assisted introductory programming lab sessions", "answered student questions during office hours", "graded programming exercises using an instructor-provided rubric"],
    "Programming Tutor": ["guided beginning programmers through practice exercises", "discussed debugging approaches during tutoring sessions"],
    "Peer Programming Mentor": ["supported beginner practice sessions", "explained worked examples under a course instructor's supervision"],
}
THEMES = ("library catalogue", "course planner", "expense tracker", "word game", "study-session scheduler", "recipe organiser", "quiz practice tool", "text-file analyser")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_config(config):
    digest(config)
    require(config["version"] == "ta-graduate-v1", "Unsupported TA configuration")
    require(config["seeds"] and len(set(config["seeds"])) == len(config["seeds"]) and all(type(s) is int and s >= 0 for s in config["seeds"]), "Invalid seeds")
    require(type(config["pool_per_seed"]) is int and config["pool_per_seed"] > 0, "Invalid pool size")
    require(type(config["selection_seed"]) is int, "Invalid selection seed")
    require(set(config["graduate_pathways"]) == {"masters", "doctoral"}, "Graduate students only")
    probabilities = [list(config["graduate_pathways"].values()), config["interest_probabilities"]]
    for key in ("academic_given_teaching_probabilities", "evidence_probabilities_by_teaching_level"):
        require(len(config[key]) == 5, f"Expected five levels: {key}")
        width = 5 if key.startswith("academic") else 3
        require(all(len(p) == width for p in config[key]), f"Invalid probability width: {key}")
        probabilities.extend(config[key])
    for weights in probabilities:
        require(all(type(p) in (float, int) and math.isfinite(p) and p >= 0 for p in weights) and math.isclose(sum(weights), 1), "Invalid probabilities")
    require(len(config["interest_probabilities"]) == 3 and 0 <= config["full_availability_probability"] <= 1, "Invalid interest/availability probabilities")
    require(len(config["courses"]) == 4 and len(set(config["courses"])) == 4, "Expected four distinct course anchors")
    for key in ("gpa_ranges_by_academic_level", "grades_by_academic_level", "teaching_month_ranges"):
        require(len(config[key]) == 5, f"Expected five levels: {key}")
    require(all(len(g) == 4 and all(grade in GRADES for grade in g) for g in config["grades_by_academic_level"]), "Invalid course grades")
    require(all(0 <= lo <= hi <= 4 for lo, hi in config["gpa_ranges_by_academic_level"]), "Invalid GPA range")
    require(all(type(lo) is int and type(hi) is int and 0 <= lo <= hi <= 36 for lo, hi in config["teaching_month_ranges"]), "Invalid teaching duration range")
    month_index(config["review_month"])
    require(date.fromisoformat(config["record_as_of"]).isoformat() == config["record_as_of"] and config["record_as_of"][:7] <= config["review_month"], "Invalid record date")
    rubric = config["rubric"]
    require(rubric["technical_high_floor"] in GRADES and 1 <= rubric["technical_high_a_range_count"] <= 4 and 1 <= rubric["technical_low_below_b_count"] <= 4 and rubric["teaching_high_months"] > 0, "Invalid rubric anchors")
    table = rubric["tier_table"]
    require(set(table) == set(LEVELS) and all(set(row) == set(LEVELS) and all(tier in TIERS for tier in row.values()) for row in table.values()), "Incomplete rubric table")
    for i, academic in enumerate(LEVELS):
        for j, teaching in enumerate(LEVELS):
            rank = TIERS.index(table[academic][teaching])
            require(not i or rank >= TIERS.index(table[LEVELS[i-1]][teaching]), "Nonmonotonic technical rubric")
            require(not j or rank >= TIERS.index(table[academic][LEVELS[j-1]]), "Nonmonotonic teaching rubric")
    cells = [(cell["tier"], cell["pattern"]) for cell in config["allocation"]]
    require(len(set(cells)) == len(cells) and all(cell["tier"] in TIERS and type(cell["count"]) is int and cell["count"] >= 0 for cell in config["allocation"]), "Invalid allocation")
    require(type(config["max_repairs"]) is int and 0 <= config["max_repairs"] <= 3 and type(config["max_workers"]) is int and 1 <= config["max_workers"] <= 4, "Invalid call bounds")


def validate_facts(facts, config):
    """Validate the fixed record before any prose or model call."""
    errors = []
    try:
        expected = {"applicant_id", "review_month", "record_as_of", "education", "undergraduate_gpa", "gpa_scale", "coursework", "technical_skills", "projects", "teaching_experience", "communication_evidence", "teaching_interest", "availability"}
        require(set(facts) == expected, "Missing or unexpected fact fields")
        require(facts["review_month"] == config["review_month"] and facts["record_as_of"] == config["record_as_of"], "Snapshot dates changed")
        require(type(facts["undergraduate_gpa"]) in (int, float) and math.isfinite(facts["undergraduate_gpa"]) and 0 <= facts["undergraduate_gpa"] <= 4 and facts["gpa_scale"] == 4, "Invalid GPA")
        degrees = facts["education"]
        require(len(degrees) == 2 and degrees[0]["status"] == "completed" and degrees[0]["degree"] == "BS in Computer Science" and degrees[1]["status"] == "enrolled" and degrees[1]["degree"] in {"MS in Computer Science", "PhD in Computer Science"}, "Expected completed BS and current graduate enrollment")
        for degree in degrees:
            require(month_index(degree["start"]) < month_index(degree["end"]), "Invalid education dates")
        require(degrees[0]["end"] <= degrees[1]["start"] <= facts["record_as_of"][:7] and degrees[1]["end"] > facts["review_month"], "Inconsistent graduate enrollment")
        require(len(facts["coursework"]) == 4 and {c["course"] for c in facts["coursework"]} == set(config["courses"]) and all(c["grade"] in GRADES for c in facts["coursework"]), "Invalid coursework")
        require(facts["technical_skills"] == ["Python", "Git"], "Unexpected skills")
        projects = facts["projects"]
        require(len(projects) == 1 and projects[0]["id"] == "project-1", "Expected one fixed project")
        project = projects[0]
        require(degrees[0]["start"] <= project["date"] <= degrees[0]["end"] and project["course"] == "Data Structures" and project["tasks"] and project["tools"] == facts["technical_skills"], "Project/course/skill mismatch")
        entries = facts["teaching_experience"]
        require(isinstance(entries, list) and len(entries) <= 2 and len({e["id"] for e in entries}) == len(entries), "Invalid teaching records")
        for entry in entries:
            require(month_index(entry["end"]) - month_index(entry["start"]) == entry["months"] > 0 and degrees[0]["start"] <= entry["start"] < entry["end"] <= facts["record_as_of"][:7], "Invalid teaching dates or duration")
            require(type(entry["hours_per_week"]) is int and 1 <= entry["hours_per_week"] <= 20, "Invalid teaching workload")
            require(entry["role"] in ROLE_TASKS and entry["tasks"] == ROLE_TASKS[entry["role"]] and entry["performance"] in EVIDENCE and entry["performance_note"] == PERFORMANCE[entry["performance"]], "Unsupported teaching evidence")
        require(all(left["end"] <= right["start"] for left, right in zip(entries, entries[1:])), "Overlapping teaching periods")
        communication = facts["communication_evidence"]
        require(set(communication) == {"written", "oral"}, "Missing communication evidence")
        for mode, evidence in communication.items():
            require(evidence["source_project_id"] == project["id"] and evidence["rating"] in EVIDENCE and evidence["observation"] == COMMUNICATION[mode][evidence["rating"]], "Communication observation/source mismatch")
            expected_source = "course instructor feedback on the project report" if mode == "written" else "course instructor feedback on the project presentation"
            require(evidence["source"] == expected_source, "Unsupported communication source")
        interest = facts["teaching_interest"]
        require(interest["category"] in INTEREST and interest["statement"] == INTEREST[interest["category"]], "Invalid teaching interest")
        require(set(facts["availability"]) == set(DUTIES) and all(type(value) is bool for value in facts["availability"].values()), "Invalid availability")
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        errors.append(str(exc))
    return errors


def evaluate(facts, config):
    errors = validate_facts(facts, config)
    if errors:
        return {"tier": "unrated", "issues": errors, "selection_pattern": "none"}
    policy = config["rubric"]
    grades = [GRADES[c["grade"]] for c in facts["coursework"]]
    technical = "adequate"
    if sum(g < GRADES["B"] for g in grades) >= policy["technical_low_below_b_count"]:
        technical = "low"
    elif min(grades) >= GRADES[policy["technical_high_floor"]] and sum(g >= GRADES["A-"] for g in grades) >= policy["technical_high_a_range_count"]:
        technical = "high"
    entries = facts["teaching_experience"]
    months = sum(e["months"] for e in entries)
    teaching = "low"
    if entries and all(e["performance"] != "needs_improvement" for e in entries):
        teaching = "adequate"
        if months >= policy["teaching_high_months"] and any(e["performance"] == "effective" for e in entries):
            teaching = "high"
    tier = policy["tier_table"][technical][teaching]
    reasons = [f"Technical coursework evidence: {technical}.", f"Teaching evidence: {teaching}; {months} months with the stated supervisor feedback."]
    communication_gap = any(e["rating"] == "needs_improvement" for e in facts["communication_evidence"].values())
    if communication_gap:
        tier = "weak" if technical == "low" else TIERS[min(TIERS.index(tier), 1)]
        reasons.append("At least one communication observation needs improvement; tier capped at borderline.")
    all_duties = all(facts["availability"].values())
    if not all_duties or facts["teaching_interest"]["category"] == "undecided":
        tier = TIERS[min(TIERS.index(tier), 1)]
        reasons.append("Incomplete duty availability or undecided teaching interest; tier capped at borderline.")
    pattern = "none"
    if tier == "borderline" and technical == "high" and teaching == "high" and not all_duties and not communication_gap:
        pattern = "strong_preparation_limited_availability"
    elif tier == "borderline" and technical == "low" and teaching == "high" and not communication_gap:
        pattern = "technical_gaps_experienced_tutor"
    elif tier == "borderline" and technical == "high" and not entries and not communication_gap and all_duties and facts["teaching_interest"]["category"] != "undecided":
        pattern = "high_academics_no_teaching"
    elif tier == "strong" and facts["undergraduate_gpa"] < policy["lower_gpa_mixed_ceiling"] and teaching == "high":
        pattern = "lower_gpa_effective_teaching"
    return {"tier": tier, "technical": technical, "teaching": teaching, "communication_gap": communication_gap, "all_duties_available": all_duties, "teaching_months": months, "selection_pattern": pattern, "reasons": reasons, "issues": [], "rubric_hash": digest(policy), "facts_hash": digest(facts), "status": "provisional_study_label"}


def make_pool(config):
    check_config(config)
    pool = []
    for seed in config["seeds"]:
        rng = random.Random(seed)
        for index in range(config["pool_per_seed"]):
            teaching_level = rng.randrange(5)
            academic_level = rng.choices(range(5), config["academic_given_teaching_probabilities"][teaching_level])[0]
            pathway = rng.choices(list(config["graduate_pathways"]), list(config["graduate_pathways"].values()))[0]
            bs_end, graduate_start, graduate_end = ("2025-05", "2025-09", "2027-05") if pathway == "masters" else ("2024-05", "2024-09", "2029-05")
            bs_start = month_string(month_index(bs_end) - 44)
            education = [
                {"degree": "BS in Computer Science", "institution": "Fictional University A", "start": bs_start, "end": bs_end, "status": "completed"},
                {"degree": "MS in Computer Science" if pathway == "masters" else "PhD in Computer Science", "institution": "Fictional University B", "start": graduate_start, "end": graduate_end, "status": "enrolled"},
            ]
            project = {"id": "project-1", "course": "Data Structures", "date": month_string(month_index(bs_end) - 5), "topic": rng.choice(THEMES), "tools": ["Python", "Git"], "tasks": ["implemented a small command-line program using functions and collections", "tested example inputs and documented the program's behaviour"], "scope": "individual undergraduate course project", "communication_activities": ["submitted a written project report", "gave an oral project presentation and answered questions"]}
            weights = config["evidence_probabilities_by_teaching_level"][teaching_level]
            communication = {}
            for mode in ("written", "oral"):
                rating = rng.choices(EVIDENCE, weights)[0]
                communication[mode] = {"source_project_id": project["id"], "source": "course instructor feedback on the project report" if mode == "written" else "course instructor feedback on the project presentation", "rating": rating, "observation": COMMUNICATION[mode][rating]}
            months = rng.randint(*config["teaching_month_ranges"][teaching_level])
            entries = []
            if months:
                durations = [months] if months < 8 else [months // 2, months - months // 2]
                end = month_index(config["record_as_of"][:7]) - rng.randint(0, 2)
                start = end - sum(durations) - (len(durations) - 1)
                for i, duration in enumerate(durations):
                    role = rng.choice(list(ROLE_TASKS))
                    rating = rng.choices(EVIDENCE, weights)[0]
                    entries.append({"id": f"teaching-{i+1}", "role": role, "organization": "University Programming Support Programme", "start": month_string(start), "end": month_string(start + duration), "months": duration, "hours_per_week": rng.choice([4, 6, 8, 10]), "topics": rng.sample(["variables and conditionals", "loops", "functions", "lists and dictionaries", "debugging"], 2), "tasks": list(ROLE_TASKS[role]), "performance": rating, "performance_note": PERFORMANCE[rating]})
                    start += duration + 1
            interest = rng.choices(list(INTEREST), config["interest_probabilities"])[0]
            availability = {duty: True for duty in DUTIES}
            if rng.random() > config["full_availability_probability"]:
                availability[rng.choice(DUTIES)] = False
            facts = {"applicant_id": f"TA-v1-{seed}-{index+1:05d}", "review_month": config["review_month"], "record_as_of": config["record_as_of"], "education": education, "undergraduate_gpa": round(rng.uniform(*config["gpa_ranges_by_academic_level"][academic_level]), 2), "gpa_scale": 4.0, "coursework": [{"course": course, "grade": grade} for course, grade in zip(config["courses"], config["grades_by_academic_level"][academic_level])], "technical_skills": ["Python", "Git"], "projects": [project], "teaching_experience": entries, "communication_evidence": communication, "teaching_interest": {"category": interest, "statement": INTEREST[interest]}, "availability": availability}
            require(not validate_facts(facts, config), f"Invalid generated facts: {facts['applicant_id']}: {validate_facts(facts, config)}")
            rubric = evaluate(facts, config)
            pool.append({"profile_id": facts["applicant_id"], "seed": seed, "latent_academic_level": academic_level, "latent_teaching_level": teaching_level, "facts": facts, "facts_hash": digest(facts), "strength": rubric["tier"], "rubric": rubric})
    return pool


def select_allocated(pool, config):
    rng = random.Random(config["selection_seed"])
    selected = []
    for cell in config["allocation"]:
        candidates = sorted([row for row in pool if row["strength"] == cell["tier"] and row["rubric"]["selection_pattern"] == cell["pattern"]], key=lambda row: row["profile_id"])
        require(len(candidates) >= cell["count"], f"Insufficient pool coverage for {cell}: {len(candidates)}")
        selected.extend(rng.sample(candidates, cell["count"]))
    require(len({r["profile_id"] for r in selected}) == len(selected), "Repeated selected profile")
    rng.shuffle(selected)
    return selected


def summarize(rows):
    return {"n": len(rows), "tiers": dict(Counter(r["strength"] for r in rows)), "selection_cells": dict(Counter(f"{r['strength']}:{r['rubric']['selection_pattern']}" for r in rows)), "graduate_degrees": dict(Counter(r["facts"]["education"][1]["degree"] for r in rows)), "technical_by_teaching": dict(Counter(f"{r['rubric']['technical']}:{r['rubric']['teaching']}" for r in rows)), "no_teaching_experience": sum(not r["facts"]["teaching_experience"] for r in rows), "incomplete_availability": sum(not all(r["facts"]["availability"].values()) for r in rows)}
