"""PhD adaptation of conditional sampling, composite ranks and weighted subsampling.

Method reference: Nghiem et al. (2025), section 3 and Appendix D; public code
revision 5817943ef9509c49494e15408463a51cc82a034e. This implementation uses new
PhD field parameters, not the paper's undergraduate numerical constants.
"""

import math
import random
import re
import statistics
from copy import deepcopy
from collections import Counter, defaultdict
from datetime import date

from .io import digest


def month_index(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise ValueError("Invalid YYYY-MM date")
    year, month = map(int, value.split("-"))
    if year < 1900 or not 1 <= month <= 12:
        raise ValueError("Invalid YYYY-MM date")
    return year * 12 + month - 1


def month_string(value):
    year, month = divmod(value, 12)
    return f"{year:04d}-{month + 1:02d}"


def interval(end, duration):
    return {"start": month_string(end - duration), "end": month_string(end), "months": duration}


def percentile_ranks(values):
    """Average ranks for ties, divided by N, as in pandas rank(pct=True)."""
    positions = defaultdict(list)
    for rank, index in enumerate(sorted(range(len(values)), key=values.__getitem__), start=1):
        positions[values[index]].append(rank)
    ranks = {value: statistics.mean(items) / len(values) for value, items in positions.items()}
    return [ranks[value] for value in values]


def standardized(values):
    sd = statistics.stdev(values) if len(values) > 1 else 0
    mean = statistics.mean(values)
    return [(value - mean) / sd if sd else 0.0 for value in values]


def quintiles(values):
    """Linear empirical quantile cuts, like the reference's pandas.qcut(q=5).

    Include boundary values in the lower interval, preserving ties. Fail on
    duplicate edges instead of silently collapsing the number of intervals.
    """
    ordered = sorted(values)
    if len(ordered) < 5:
        raise ValueError("At least five values are needed for quintiles")
    edges = []
    for i in range(6):
        position = (len(ordered) - 1) * i / 5
        lo, hi = math.floor(position), math.ceil(position)
        edges.append(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo))
    if len(set(edges)) != len(edges):
        raise ValueError("Duplicate performance quantile edges; review feature variation or cohort size")
    return [1 + sum(value > edge for edge in edges[1:-1]) for value in values]


def check_config(config):
    try:
        digest(config)
    except (TypeError, ValueError) as exc:
        raise ValueError("Configuration must contain finite, JSON-serializable values") from exc
    if config.get("version") != "phd-v2-provisional":
        raise ValueError("Use the current PhD configuration; earlier prototype runs must not be reused as calibrated study data")
    if len(set(config["seeds"])) != len(config["seeds"]) or not config["seeds"]:
        raise ValueError("Seeds must be nonempty and unique")
    if any(type(seed) is not int or seed < 0 for seed in config["seeds"]):
        raise ValueError("Seeds must be nonnegative integers")
    if type(config["n_per_cohort"]) is not int or config["n_per_cohort"] < 10:
        raise ValueError("n_per_cohort must be an integer >= 10")
    if type(config["oversample"]) is not int or config["oversample"] < 0:
        raise ValueError("oversample must be a nonnegative integer")
    month_index(config["review_month"])
    if not isinstance(config["gpa_as_of"], str) or date.fromisoformat(config["gpa_as_of"]).isoformat() != config["gpa_as_of"]:
        raise ValueError("GPA reporting date must use YYYY-MM-DD")
    if config["gpa_as_of"][:7] > config["review_month"]:
        raise ValueError("GPA reporting date cannot follow review")
    for probabilities in [list(config["pathways"].values()), config["gpa_bin_probabilities"], config["preparation_probabilities"]]:
        if any(p < 0 for p in probabilities) or not math.isclose(sum(probabilities), 1.0):
            raise ValueError("Sampling probabilities must sum to one and be nonnegative")
    if set(config["pathways"]) != {"bachelors", "masters", "recent_graduate", "industry_returner"}:
        raise ValueError("Pathways must contain the four supported enrollment timelines")
    if len(config["preparation_probabilities"]) != 5:
        raise ValueError("Supply probabilities for all five provisional preparation levels")
    if len(config["gpa_bins"]) != len(config["gpa_bin_probabilities"]):
        raise ValueError("Each GPA bin needs a probability")
    if any(not 0 <= lo <= hi <= 4 for lo, hi in config["gpa_bins"]):
        raise ValueError("GPA bins must be ordered intervals within 0..4")
    if any(left[1] >= right[0] for left, right in zip(config["gpa_bins"], config["gpa_bins"][1:])):
        raise ValueError("GPA bins must be increasing and nonoverlapping")
    if not -1 <= config["gpa_latent_rank_coefficient"] <= 1:
        raise ValueError("Rank coefficient must be between -1 and 1")
    for key in ("research_month_ranges_by_preparation", "publication_probability_per_six_months", "main_conference_probability_by_preparation", "internship_count_ranges_by_preparation", "technical_project_count_ranges_by_preparation", "technical_work_probability_by_preparation", "contribution_by_preparation"):
        if len(config[key]) != 5:
            raise ValueError(f"{key} must have five entries")
    for key in ("publication_probability_per_six_months", "main_conference_probability_by_preparation", "technical_work_probability_by_preparation"):
        if any(not 0 <= p <= 1 for p in config[key]):
            raise ValueError(f"Invalid probabilities in {key}")
    if not 0 <= config["first_author_probability"] <= 1:
        raise ValueError("Invalid first-author probability")
    for key in ("research_month_ranges_by_preparation", "internship_count_ranges_by_preparation", "technical_project_count_ranges_by_preparation"):
        if any(type(lo) is not int or type(hi) is not int or not 0 <= lo <= hi for lo, hi in config[key]):
            raise ValueError(f"Invalid count intervals in {key}")
    if not config["research_areas"] or type(config["max_publications"]) is not int or config["max_publications"] < 0:
        raise ValueError("Research areas and publication cap are invalid")
    expected = {"gpa", "research_months", "publication_count", "research_internships", "technical_projects"}
    if set(config["performance_weights"]) != expected or any(v < 0 for v in config["performance_weights"].values()) or not sum(config["performance_weights"].values()):
        raise ValueError("Invalid performance weights")
    if set(config["performance_normalization"]) != expected or any(v not in {"percentile", "zscore"} for v in config["performance_normalization"].values()):
        raise ValueError("Each performance feature needs percentile or zscore normalization")
    courses = config["coursework_by_preparation"]
    if len(courses) != 5 or any(not level for level in courses):
        raise ValueError("Supply coursework patterns for all five preparation levels")
    grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"}
    for level in courses:
        if any(set(c) != {"course", "grade"} or not isinstance(c["course"], str) or not c["course"].strip() or c["grade"] not in grades for c in level):
            raise ValueError("Invalid course/grade pattern")
        if len({c["course"] for c in level}) != len(level):
            raise ValueError("Duplicate relevant course")
    if set(config["strength_by_quintile"]) != set("12345") or set(config["strength_by_quintile"].values()) != {"weak", "borderline", "strong"}:
        raise ValueError("Map all five quintiles to the three strength groups")
    if config["subsample_cells"] != ["pathway", "perf_quintile"]:
        raise ValueError("This adaptation stratifies by pathway and performance quintile")


def education(pathway, end):
    year = end // 12
    if pathway == "bachelors":
        return [{"degree": "BS in Computer Science", "institution": "University A", "start": f"{year-3}-09", "end": f"{year+1}-05", "status": "in progress"}]
    if pathway == "recent_graduate":
        return [{"degree": "BS in Computer Science", "institution": "University A", "start": f"{year-4}-09", "end": f"{year}-05", "status": "completed"}]
    bs_end = year - (6 if pathway == "industry_returner" else 1)
    return [
        {"degree": "BS in Computer Science", "institution": "University A", "start": f"{bs_end-4}-09", "end": f"{bs_end}-05", "status": "completed"},
        {"degree": "MS in Computer Science", "institution": "University B", "start": f"{year-1}-09", "end": f"{year+1}-05", "status": "in progress"},
    ]


def make_profile(config, rng, seed, index, latent, gpa):
    end = month_index(config["review_month"])
    level = latent - 1
    pathway = rng.choices(list(config["pathways"]), list(config["pathways"].values()))[0]
    degrees = education(pathway, end)
    earliest = month_index(degrees[0]["start"])
    months = min(rng.randint(*config["research_month_ranges_by_preparation"][level]), end - earliest)
    internships = min(rng.randint(*config["internship_count_ranges_by_preparation"][level]), months // 3)
    pub_count = min(config["max_publications"], sum(rng.random() < config["publication_probability_per_six_months"][level] for _ in range(months // 6)))
    project_count = rng.randint(*config["technical_project_count_ranges_by_preparation"][level])
    research = []
    cursor = end
    # Internships are a subset of total research time, never added twice.
    for i in range(internships):
        research.append({"id": f"R{len(research)+1}", "role": "Research intern", "organization": f"Research Lab {i+1}", **interval(cursor, 3), "hours_per_week": 15, "contribution": config["contribution_by_preparation"][level]})
        cursor -= 3
    remainder = months - internships * 3
    if remainder:
        research.append({"id": f"R{len(research)+1}", "role": "Research assistant", "organization": "University Research Group", **interval(cursor, remainder), "hours_per_week": 10, "contribution": config["contribution_by_preparation"][level]})
    publications = []
    for i in range(pub_count):
        major = rng.random() < config["main_conference_probability_by_preparation"][level]
        publications.append({"id": f"P{i+1}", "venue": "Peer-reviewed ML conference" if major else "Regional applied computing conference", "status": "published", "author_position": 1 if rng.random() < config["first_author_probability"] else rng.randint(2, 4), "date": month_string(rng.randint(end - months + 6, end)), "research_id": research[-1]["id"]})
    work = []
    if pathway == "industry_returner":
        work_end = month_index(degrees[-1]["start"])
        work_months = rng.randint(12, 36)
    else:
        work_end = end - months
        work_months = min(rng.choice([0, 3, 6, 9, 12]), max(0, work_end - earliest))
    technical = rng.random() < config["technical_work_probability_by_preparation"][level]
    if work_months:
        work.append({"id": "W1", "organization": "Company A", "domain": "technical" if technical else "nontechnical", "role": "Software engineer" if technical else "Operations assistant", **interval(work_end, work_months), "hours_per_week": 40 if pathway == "industry_returner" else 10})
    projects = [{"id": f"T{i+1}", "kind": "technical course project", "year": end // 12, "scope": "baseline implementation" if latent <= 2 else "implementation and comparative evaluation"} for i in range(project_count)]
    coursework = deepcopy(config["coursework_by_preparation"][level])
    facts = {"applicant_id": f"PHD-{seed}-{index:05d}", "review_month": config["review_month"], "education": degrees, "gpa": gpa, "gpa_scale": 4.0, "gpa_as_of": config["gpa_as_of"], "gpa_degree": "BS in Computer Science", "coursework": coursework, "research_area": rng.choice(config["research_areas"]), "research_experience": research, "publications": publications, "work_experience": work, "projects": projects, "skills": ["Python", "NumPy", "scikit-learn"] + (["PyTorch"] if latent >= 3 else [])}
    return {"profile_id": facts["applicant_id"], "cohort_seed": seed, "pool_index": index, "latent_preparation_quintile": latent, "pathway": pathway, "features": {"gpa": gpa, "research_months": months, "publication_count": pub_count, "research_internships": internships, "technical_projects": project_count}, "facts": facts}


def generate_cohort(config, seed):
    check_config(config)
    rng = random.Random(seed)
    size = config["n_per_cohort"] + config["oversample"]
    latent = rng.choices(range(1, 6), weights=config["preparation_probabilities"], k=size)
    preliminary = []
    for _ in range(size):
        b = rng.choices(config["gpa_bins"], config["gpa_bin_probabilities"])[0]
        preliminary.append(round(rng.uniform(*b), 2))
    z = standardized(latent)
    noise = standardized([rng.gauss(0, 1) for _ in range(size)])
    rho = config["gpa_latent_rank_coefficient"]
    order = sorted(range(size), key=lambda i: rho * z[i] + math.sqrt(1 - rho**2) * noise[i])
    gpas = [0.0] * size
    for i, gpa in zip(order, sorted(preliminary)):
        gpas[i] = gpa
    pool = [make_profile(config, rng, seed, i, latent[i], gpas[i]) for i in range(size)]
    columns = {key: [row["features"][key] for row in pool] for key in config["performance_weights"]}
    scaled = {key: (percentile_ranks(values) if config["performance_normalization"][key] == "percentile" else standardized(values)) for key, values in columns.items()}
    scores = [sum(config["performance_weights"][key] * values[i] for key, values in scaled.items()) for i in range(size)]
    groups = quintiles(scores)
    for i, row in enumerate(pool):
        row["performance_index"] = round(scores[i], 8)
        row["perf_quintile"] = groups[i]
        row["strength"] = config["strength_by_quintile"][str(row["perf_quintile"])]
        row["strength_status"] = "provisional_cohort_label_for_human_review"
        row["facts_hash"] = digest(row["facts"])
    counts = Counter((row["pathway"], row["perf_quintile"]) for row in pool)
    # Exponential-race weighted sampling without replacement. Every member of a
    # cell has weight 1/cell_size, matching the paper's inverse-frequency rule.
    # A fresh Random(seed) repeats the uniforms used above for latent
    # preparation. That would couple inclusion to applicant strength. Give
    # selection its own reproducible stream instead of restarting that stream.
    selection_rng = random.Random(f"phd-selection:{seed}")
    ranked = sorted(pool, key=lambda row: -math.log(max(selection_rng.random(), 1e-300)) * counts[(row["pathway"], row["perf_quintile"])])
    return pool, ranked[:config["n_per_cohort"]]


def validate_profile(row):
    errors = []
    f, x = row["facts"], row["features"]
    if digest(f) != row["facts_hash"]:
        errors.append("facts_hash mismatch")
    if not 0 <= f["gpa"] <= f["gpa_scale"] or f["gpa"] != x["gpa"]:
        errors.append("GPA mismatch")
    research = f["research_experience"]
    if sum(r["months"] for r in research) != x["research_months"]:
        errors.append("Research time mismatch")
    if sum(r["role"] == "Research intern" for r in research) != x["research_internships"]:
        errors.append("Research internship mismatch")
    if len(f["publications"]) != x["publication_count"] or len(f["projects"]) != x["technical_projects"]:
        errors.append("Output/project counts mismatch")
    for r in research + f["work_experience"]:
        if month_index(r["end"]) - month_index(r["start"]) != r["months"] or r["months"] <= 0 or r["end"] > f["review_month"]:
            errors.append(f"Invalid dates for {r['id']}")
    ordered = sorted(research, key=lambda r: r["start"])
    if any(a["end"] > b["start"] for a, b in zip(ordered, ordered[1:])):
        errors.append("Overlapping research intervals")
    for p in f["publications"]:
        if p["research_id"] not in {r["id"] for r in research} or p["date"] > f["review_month"]:
            errors.append("Publication without research or after review")
        linked = next((r for r in research if r["id"] == p["research_id"]), None)
        if linked and p["date"] < linked["start"]:
            errors.append("Publication predates its linked research")
    for degree in f["education"]:
        if degree["start"] >= degree["end"] or (degree["status"] == "completed" and degree["end"] > f["review_month"]):
            errors.append("Invalid degree chronology")
    incident_month = f["review_month"][:4] + "-02"
    if not any(d["start"] <= incident_month <= d["end"] for d in f["education"]):
        errors.append("No enrollment in the incident year")
    return errors


def pearson(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    numerator = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    denominator = math.sqrt(sum((x - ma)**2 for x in a) * sum((y - mb)**2 for y in b))
    return round(numerator / denominator, 5) if denominator else None


def describe(rows):
    keys = list(rows[0]["features"])
    values = {key: [row["features"][key] for row in rows] for key in keys}
    return {"n": len(rows), "strength_counts": dict(Counter(r["strength"] for r in rows)), "pathway_counts": dict(Counter(r["pathway"] for r in rows)), "quintile_counts": dict(Counter(r["perf_quintile"] for r in rows)), "cell_counts": dict(Counter(f"{r['pathway']}:{r['perf_quintile']}" for r in rows)), "features": {key: {"mean": round(statistics.mean(v), 4), "sd": round(statistics.stdev(v), 4) if len(v) > 1 else 0, "min": min(v), "max": max(v), "frequencies": dict(Counter(str(x) for x in v))} for key, v in values.items()}, "pearson_correlations": {a: {b: pearson(values[a], values[b]) for b in keys} for a in keys}, "observed_latent_gpa_correlation": pearson([r["latent_preparation_quintile"] for r in rows], values["gpa"])}
