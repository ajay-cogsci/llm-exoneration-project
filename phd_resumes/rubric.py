"""Fixed, facts-only CV rubric. Neither cohort ranks nor latent levels are inputs.

All numeric anchors and the decision table are study assumptions. See RUBRIC.md.
Unknown evidence is unrated, never silently treated as weak evidence.
"""

import math
import statistics
from collections import Counter

from .io import digest
from .sampling import month_index, pearson

GRADES = {g: i for i, g in enumerate(["F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"])}
LEVELS = ("low", "adequate", "high")
TIERS = ("weak", "borderline", "strong")
PATTERNS = ("lower_gpa_strong_research", "high_academics_limited_research", "academic_gaps_strong_research", "strong_research_without_publications", "none")
NOT_ASSESSED = ["faculty fit", "letters", "essays/writing", "motivation or character", "course difficulty", "thesis equivalence", "publication quality or venue prestige"]


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def check_rubric(policy):
    digest(policy)
    if policy.get("version") != "phd-cv-rubric-v1":
        raise ValueError("Unsupported rubric version")
    a, r = policy["academic"], policy["research"]
    courses = a["required_courses"]
    if not courses or len(set(courses)) != len(courses) or any(not isinstance(c, str) or not c for c in courses):
        raise ValueError("Required courses must be unique names")
    if not a["quantitative_courses"] or not set(a["quantitative_courses"]) <= set(courses):
        raise ValueError("Quantitative courses must be a nonempty subset of required courses")
    if not all(number(a[k]) for k in ("adequate_gpa_min", "high_gpa_min")) or not 0 <= a["adequate_gpa_min"] <= a["high_gpa_min"] <= 4:
        raise ValueError("Invalid academic GPA thresholds")
    for k in ("high_course_floor", "low_grade_ceiling"):
        if a[k] not in GRADES:
            raise ValueError("Unrecognized rubric grade")
    if GRADES[a["low_grade_ceiling"]] >= GRADES["B"] or GRADES[a["high_course_floor"]] < GRADES["B"]:
        raise ValueError("Academic grade anchors must be ordered")
    for k in ("high_a_range_count_min", "low_below_b_count_min"):
        if type(a[k]) is not int or not 1 <= a[k] <= len(courses):
            raise ValueError("Invalid course count threshold")
    for k in ("full_time_hours_per_week", "adequate_months_min", "adequate_fte_months_min", "high_months_min", "high_fte_months_min", "high_intellectual_months_min"):
        if not number(r[k]) or r[k] <= 0:
            raise ValueError("Research thresholds must be positive finite numbers")
    if r["adequate_months_min"] > r["high_months_min"] or r["adequate_fte_months_min"] > r["high_fte_months_min"] or r["high_intellectual_months_min"] > r["high_months_min"]:
        raise ValueError("Research thresholds must be ordered")
    if not r["contribution_levels"] or any(not isinstance(k, str) or not k or v not in {"routine", "guided", "intellectual"} for k, v in r["contribution_levels"].items()):
        raise ValueError("Invalid contribution vocabulary")
    table = policy["tier_table"]
    if set(table) != set(LEVELS) or any(set(row) != set(LEVELS) or any(v not in TIERS for v in row.values()) for row in table.values()):
        raise ValueError("Tier table must cover the three by three academic/research cells")
    # Improving either dimension may not make the overall tier worse.
    for i, a_level in enumerate(LEVELS):
        for j, r_level in enumerate(LEVELS):
            rank = TIERS.index(table[a_level][r_level])
            if (i and rank < TIERS.index(table[LEVELS[i-1]][r_level])) or (j and rank < TIERS.index(table[a_level][LEVELS[j-1]])):
                raise ValueError("Tier table is nonmonotonic")
    if not number(policy["mixed_lower_gpa_max_exclusive"]) or not 0 <= policy["mixed_lower_gpa_max_exclusive"] <= 4:
        raise ValueError("Invalid mixed-profile GPA boundary")


def evaluate(facts, policy):
    """Score observable structured evidence, returning reasons and explicit gaps."""
    check_rubric(policy)
    a, r = policy["academic"], policy["research"]
    issues, reasons = [], []
    result = {"rubric_version": policy["version"], "rubric_hash": digest(policy), "facts_hash": digest(facts), "status": "provisional_pending_human_review", "not_assessed": list(NOT_ASSESSED), "issues": issues, "reasons": reasons}
    academic = research = "unrated"
    evidence = {}
    courses = facts.get("coursework")
    if not isinstance(courses, list) or any(not isinstance(c, dict) or not isinstance(c.get("grade"), str) or c["grade"] not in GRADES or not isinstance(c.get("course"), str) for c in courses):
        issues.append("Missing or unrecognized coursework/grades")
    else:
        names = [c["course"] for c in courses]
        missing = set(a["required_courses"]) - set(names)
        gpa = facts.get("gpa")
        if missing or len(set(names)) != len(names):
            issues.append("Missing required courses or duplicate course names")
        elif not number(gpa) or not 0 <= gpa <= 4 or facts.get("gpa_scale") != 4:
            issues.append("Missing or unsupported GPA (requires a 4.0 scale)")
        else:
            grades = {c["course"]: GRADES[c["grade"]] for c in courses}
            relevant = [grades[c] for c in a["required_courses"]]
            below_b = sum(g < GRADES["B"] for g in relevant)
            a_count = sum(g >= GRADES["A-"] for g in relevant)
            quant_below_b = [c for c in a["quantitative_courses"] if grades[c] < GRADES["B"]]
            academic = "adequate"
            if gpa < a["adequate_gpa_min"] or below_b >= a["low_below_b_count_min"] or min(relevant) <= GRADES[a["low_grade_ceiling"]]:
                academic = "low"
            elif gpa >= a["high_gpa_min"] and min(relevant) >= GRADES[a["high_course_floor"]] and a_count >= a["high_a_range_count_min"]:
                academic = "high"
            evidence.update(gpa=gpa, relevant_courses_below_b=below_b, relevant_courses_in_a_range=a_count, quantitative_courses_below_b=quant_below_b)
            reasons.append(f"Academic {academic}: GPA {gpa:.2f}; {a_count}/{len(relevant)} relevant grades in A range; {below_b} below B. Course difficulty and explanations for grades are unavailable.")
    entries = facts.get("research_experience")
    research_issues = []
    if not isinstance(entries, list):
        research_issues.append("Missing research history (an explicit empty list means none)")
    else:
        for e in entries:
            if not isinstance(e, dict) or not number(e.get("months")) or e["months"] <= 0 or not number(e.get("hours_per_week")) or not 0 < e["hours_per_week"] <= 80:
                research_issues.append("Missing/invalid research duration or hours")
                continue
            if not isinstance(e.get("contribution"), str) or e["contribution"] not in r["contribution_levels"]:
                research_issues.append("Unknown research contribution: human mapping required")
            try:
                if month_index(e["end"]) - month_index(e["start"]) != e["months"] or month_index(e["end"]) > month_index(facts["review_month"]):
                    research_issues.append("Invalid research dates")
            except (KeyError, ValueError, TypeError):
                research_issues.append("Missing/invalid research dates")
        if not research_issues:
            ordered = sorted(entries, key=lambda e: e["start"])
            if any(x["end"] > y["start"] for x, y in zip(ordered, ordered[1:])):
                research_issues.append("Overlapping research intervals require explicit exposure reconciliation")
        if not research_issues:
            months = sum(e["months"] for e in entries)
            fte = sum(e["months"] * e["hours_per_week"] / r["full_time_hours_per_week"] for e in entries)
            intellectual = sum(e["months"] for e in entries if r["contribution_levels"][e["contribution"]] == "intellectual")
            research = "low"
            if months >= r["adequate_months_min"] and fte >= r["adequate_fte_months_min"]:
                research = "adequate"
            if months >= r["high_months_min"] and fte >= r["high_fte_months_min"] and intellectual >= r["high_intellectual_months_min"]:
                research = "high"
            evidence.update(research_months=months, research_fte_months=round(fte, 4), intellectual_contribution_months=intellectual)
            reasons.append(f"Research {research}: {months} calendar months, {fte:.2f} full-time-equivalent months, {intellectual} months with stated intellectual contribution. Exposure is not a thesis-equivalence or quality measure.")
    issues.extend(research_issues)
    pubs = facts.get("publications")
    if not isinstance(pubs, list):
        issues.append("Missing publication history (an explicit empty list means none)")
    else:
        evidence["publication_count"] = len(pubs)
        reasons.append(f"{len(pubs)} listed publications recorded as supporting evidence; count and venue do not determine the tier.")
    tier = policy["tier_table"][academic][research] if not issues else "unrated"
    if issues:
        result["status"] = "needs_evidence_review"
    tags = []
    if not issues:
        if research == "high" and facts["gpa"] < policy["mixed_lower_gpa_max_exclusive"]:
            tags.append(PATTERNS[0])
        if academic == "high" and research == "low":
            tags.append(PATTERNS[1])
        if academic == "low" and research == "high":
            tags.append(PATTERNS[2])
        if research == "high" and not pubs:
            tags.append(PATTERNS[3])
        reasons.append(f"Decision-table cell academic={academic}, research={research} gives {tier}; no cohort ranks or sample quotas enter this decision.")
    result.update(academic=academic, research=research, tier=tier, evidence=evidence, mixed_tags=tags, selection_pattern=tags[0] if tags else "none")
    return result


def summarize(rows, policy):
    rated = [evaluate(row["facts"], policy) for row in rows]
    descriptive = {}
    for tier in (*TIERS, "unrated"):
        members = [r for r in rated if r["tier"] == tier]
        if not members:
            continue
        stats = {}
        for key in ("gpa", "research_months", "research_fte_months", "intellectual_contribution_months", "publication_count"):
            values = [r["evidence"][key] for r in members if key in r["evidence"]]
            stats[key] = {"observed": len(values), "mean": round(statistics.mean(values), 4), "min": min(values), "max": max(values)} if values else {"observed": 0}
        stats["n"] = len(members)
        stats["with_publications"] = sum(r["evidence"].get("publication_count", 0) > 0 for r in members)
        descriptive[tier] = stats
    keys = ("gpa", "research_months", "research_fte_months", "publication_count")
    complete = [r["evidence"] for r in rated if all(k in r["evidence"] for k in keys)]
    correlations = {a: {b: pearson([e[a] for e in complete], [e[b] for e in complete]) for b in keys} for a in keys} if complete else {}
    return {
        "n": len(rows), "tiers": dict(Counter(r["tier"] for r in rated)),
        "academic_by_research": dict(Counter(f"{r['academic']}:{r['research']}" for r in rated)),
        "selection_cells": dict(Counter(f"{r['tier']}:{r['selection_pattern']}" for r in rated)),
        "mixed_tags_nonexclusive": dict(Counter(t for r in rated for t in r["mixed_tags"])),
        "old_to_rubric": dict(Counter(f"{row.get('legacy_diagnostic', row).get('strength', 'unknown')}:{r['tier']}" for row, r in zip(rows, rated))),
        "tier_descriptives": descriptive, "observable_correlations": correlations,
        "unrated_ids": [row["profile_id"] for row, r in zip(rows, rated) if r["tier"] == "unrated"],
    }
