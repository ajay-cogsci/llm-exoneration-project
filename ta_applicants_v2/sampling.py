"""Versioned TA facts with separate evidence draws and an explicit merit rubric."""

import math
import random
from collections import Counter
from copy import deepcopy
from datetime import date

from phd_resumes.io import digest
from phd_resumes.sampling import month_index, month_string
from ta_applicants.sampling import COMMUNICATION, DUTIES, EVIDENCE, GRADES, INTEREST, PERFORMANCE, TIERS, require
from .catalog import FEEDBACK_CONTEXT, PROJECTS, ROLE_TASKS

ANCHORS = ("Introduction to Programming", "Data Structures", "Discrete Mathematics")
MAJORS = ("Computer Science", "Software Engineering", "Computer Engineering", "Mathematics")
PATTERNS = ("capable_first_time_ta", "technical_gaps_effective_teaching", "lower_gpa_effective_teaching", "high_technical_communication_gap")
GRADE_POINTS = {"F":0.0,"D":1.0,"C-":1.7,"C":2.0,"C+":2.3,"B-":2.7,"B":3.0,"B+":3.3,"A-":3.7,"A":4.0,"A+":4.0}


def gpa_ceiling(courses, config):
    undergraduate = [c for c in courses if c["level"] == "undergraduate"]
    total = config["gpa_compatibility_course_count"]
    return (sum(GRADE_POINTS[c["grade"]] for c in undergraduate) + 4 * (total-len(undergraduate))) / total


def stream(seed, index, purpose):
    return random.Random(f"ta-v2:{seed}:{index}:{purpose}")


def check_config(config):
    digest(config)
    require(config["version"] == "ta-graduate-v2", "Unsupported TA configuration")
    require(config["seeds"] and len(set(config["seeds"])) == len(config["seeds"]) and all(type(s) is int and s >= 0 for s in config["seeds"]), "Invalid seeds")
    require(type(config["pool_per_seed"]) is int and config["pool_per_seed"] > 0 and type(config["selection_seed"]) is int, "Invalid pool/selection settings")
    require(set(config["graduate_pathways"]) == {"masters", "doctoral"}, "Graduate students only")
    probabilities = [list(config["graduate_pathways"].values()), config["academic_level_probabilities"], config["project_count_probabilities"], config["teaching_count_probabilities"], config["performance_probabilities"], config["interest_probabilities"], [p["probability"] for p in config["communication_pairs"]], *config["grade_probabilities_by_academic_level"]]
    for weights in probabilities:
        require(weights and all(type(p) in (int,float) and math.isfinite(p) and p >= 0 for p in weights) and math.isclose(sum(weights), 1), "Invalid probability distribution")
    require(len(config["academic_level_probabilities"]) == len(config["grade_probabilities_by_academic_level"]) == len(config["gpa_ranges_by_academic_level"]) == 5, "Expected five academic levels")
    require(all(len(p) == len(config["grade_values"]) for p in config["grade_probabilities_by_academic_level"]) and all(g in GRADES for g in config["grade_values"]), "Invalid grade distributions")
    require(all(len(config[k]) == 3 for k in ("project_count_probabilities", "teaching_count_probabilities", "performance_probabilities", "interest_probabilities")), "Invalid evidence distribution widths")
    require(all(0 <= lo <= hi <= 4 for lo,hi in config["gpa_ranges_by_academic_level"]), "Invalid GPA ranges")
    require(type(config["gpa_compatibility_course_count"]) is int and config["gpa_compatibility_course_count"] >= 10, "Invalid GPA compatibility assumption")
    require(len(config["communication_pairs"]) == 9 and {(p["written"],p["oral"]) for p in config["communication_pairs"]} == {(a,b) for a in EVIDENCE for b in EVIDENCE}, "Communication distribution must cover all nine pairs")
    require(config["availability_policy"] == "all_required_duties_available", "This version samples applicants available for every required duty")
    require(config["teaching_timeline_policy"] == "enrolled_university_terms", "Unsupported campus appointment timeline")
    month_index(config["review_month"])
    require(date.fromisoformat(config["record_as_of"]).isoformat() == config["record_as_of"] and config["record_as_of"][:7] <= config["review_month"], "Invalid snapshot")
    rubric = config["rubric"]
    require(rubric["version"] == "ta-evidence-rubric-v2-provisional" and tuple(rubric["anchor_courses"]) == ANCHORS, "Invalid rubric version/anchors")
    require(rubric["technical_high_floor"] in GRADES and type(rubric["technical_high_a_range_count"]) is int and 1 <= rubric["technical_high_a_range_count"] <= 3 and type(rubric["technical_low_below_b_count"]) is int and 1 <= rubric["technical_low_below_b_count"] <= 3, "Invalid grade anchors")
    require(rubric["no_experience_policy"] == "neutral_no_prior_performance_evidence" and rubric["unavailable_policy"] == "separate_eligibility_failure_not_a_merit_tier", "Unsupported evidence/eligibility policy")
    require(set(config["allocation"]) == set(TIERS) and all(type(n) is int and n >= 0 for n in config["allocation"].values()), "Invalid allocation")
    cells = config["mixed_allocation"]
    require(len({c["pattern"] for c in cells}) == len(cells) and all(c["pattern"] in PATTERNS and c["tier"] in TIERS and type(c["count"]) is int and c["count"] >= 0 for c in cells), "Invalid mixed allocation")
    require(all(sum(c["count"] for c in cells if c["tier"] == tier) <= config["allocation"][tier] for tier in TIERS), "Mixed quota exceeds tier allocation")
    require(type(config["max_repairs"]) is int and 0 <= config["max_repairs"] <= 3 and type(config["max_workers"]) is int and 1 <= config["max_workers"] <= 4, "Invalid call bounds")


def validate_facts(facts, config):
    errors = []
    try:
        expected = {"applicant_id", "review_month", "record_as_of", "education", "undergraduate_gpa", "gpa_scale", "coursework", "technical_skills", "projects", "teaching_experience", "communication_evidence", "teaching_interest", "availability"}
        require(set(facts) == expected, "Missing or unexpected fact fields")
        require(facts["review_month"] == config["review_month"] and facts["record_as_of"] == config["record_as_of"], "Snapshot changed")
        require(type(facts["undergraduate_gpa"]) in (int,float) and math.isfinite(facts["undergraduate_gpa"]) and 0 <= facts["undergraduate_gpa"] <= 4 and facts["gpa_scale"] == 4, "Invalid GPA")
        degrees = facts["education"]
        require(len(degrees) == 2 and degrees[0]["degree"] in {"BS in " + m for m in MAJORS} and degrees[0]["status"] == "completed" and degrees[1]["degree"] in {"MS in Computer Science","PhD in Computer Science"} and degrees[1]["status"] == "enrolled", "Expected a completed bachelor's and current graduate enrollment")
        for degree in degrees:
            require(month_index(degree["start"]) < month_index(degree["end"]), "Invalid education dates")
        require(degrees[0]["end"] <= degrees[1]["start"] <= facts["record_as_of"][:7] <= facts["review_month"] < degrees[1]["end"], "Inconsistent graduate chronology")
        courses = facts["coursework"]
        require(isinstance(courses,list) and len(courses) >= 4 and len({(c["course"],c["level"]) for c in courses}) == len(courses), "Invalid course records")
        course_map = {(c["course"],c["level"]):c for c in courses}
        require(all((name,"undergraduate") in course_map for name in ANCHORS), "Missing foundational course evidence")
        for course in courses:
            require(course["grade"] in GRADES and course["level"] in {"undergraduate","graduate"}, "Invalid course grade/level")
            degree = degrees[course["level"] == "graduate"]
            require(degree["start"] <= course["date"] <= min(degree["end"],facts["record_as_of"][:7]), "Course outside enrollment/snapshot")
        require(facts["undergraduate_gpa"] <= round(gpa_ceiling(courses,config),2), "GPA incompatible with listed grades under the declared credit assumption")
        skills = facts["technical_skills"]
        require(isinstance(skills,list) and bool(skills) and len(set(skills)) == len(skills) and all(isinstance(s,str) and s for s in skills), "Invalid technical skills")
        projects = facts["projects"]
        require(1 <= len(projects) <= 3 and [p["id"] for p in projects] == [f"project-{i+1}" for i in range(len(projects))] and len({p["catalog_family"] for p in projects}) == len(projects), "Invalid project identities")
        for project in projects:
            family = PROJECTS[project["catalog_family"]]
            require(project["topic"] in family["topics"] and 2 <= len(project["tasks"]) <= 3 and len(set(project["tasks"])) == len(project["tasks"]) and set(project["tasks"]) <= set(family["tasks"]), "Unsupported project tasks/topic")
            require(project["course"] == family["course"] and (project["course"],project["level"]) in course_map and project["date"] == course_map[(project["course"],project["level"])]["date"], "Project/course/date mismatch")
            require(project["tools"] and set(project["tools"]) <= set(skills), "Project tools absent from skills")
            allowed_tools = set(family["tools"]) - {"{language}"}
            if "{language}" in family["tools"]:
                require(allowed_tools <= set(project["tools"]) and set(project["tools"]) - allowed_tools in ({"Python"},{"Java"},{"C++"}), "Unsupported project language/tools")
            else:
                require(set(project["tools"]) == allowed_tools, "Unsupported project tools")
            require(project["scope"] in {f"individual {project['level']} course project",f"team {project['level']} course project; listed tasks are the applicant's contribution"}, "Unknown project scope")
            require(project["communication_activities"] == ["submitted a written project report","gave an oral project presentation and answered questions"], "Unsupported communication activity")
        entries = facts["teaching_experience"]
        require(isinstance(entries,list) and len(entries) <= 2 and len({e["id"] for e in entries}) == len(entries), "Invalid teaching records")
        intro_date = course_map[(ANCHORS[0],"undergraduate")]["date"]
        for entry in entries:
            require(month_index(entry["end"]) - month_index(entry["start"]) == entry["months"] > 0 and intro_date < entry["start"] < entry["end"] <= facts["record_as_of"][:7], "Teaching precedes preparation or has invalid dates/duration")
            require(any(d["start"] <= entry["start"] < entry["end"] <= d["end"] for d in degrees), "Campus teaching appointment outside enrolled study")
            require(type(entry["hours_per_week"]) is int and 1 <= entry["hours_per_week"] <= 20, "Invalid teaching workload")
            require(entry["role"] in ROLE_TASKS and 2 <= len(entry["tasks"]) <= 3 and len(set(entry["tasks"])) == len(entry["tasks"]) and set(entry["tasks"]) <= set(ROLE_TASKS[entry["role"]]), "Unsupported teaching duties")
            require(entry["performance"] in EVIDENCE and entry["performance_note"] == PERFORMANCE[entry["performance"]] and entry["feedback_source"] == FEEDBACK_CONTEXT[entry["role"]], "Unsupported performance evidence")
        require(all(a["end"] <= b["start"] for a,b in zip(entries,entries[1:])), "Teaching intervals overlap")
        communication = facts["communication_evidence"]
        require(set(communication) == {"written","oral"}, "Missing communication evidence")
        for mode,evidence in communication.items():
            require(evidence["source_project_id"] in {p["id"] for p in projects} and evidence["rating"] in EVIDENCE and evidence["observation"] == COMMUNICATION[mode][evidence["rating"]], "Communication evidence mismatch")
            source = "course instructor feedback on the project report" if mode == "written" else "course instructor feedback on the project presentation"
            require(evidence["source"] == source, "Unsupported communication source")
        interest = facts["teaching_interest"]
        require(interest["category"] in INTEREST and interest["statement"] == INTEREST[interest["category"]], "Interest mismatch")
        require(set(facts["availability"]) == set(DUTIES) and all(type(x) is bool for x in facts["availability"].values()), "Invalid duty availability")
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        errors.append(str(exc))
    return errors


def evaluate(facts, config):
    errors = validate_facts(facts,config)
    if errors:
        return {"tier":"unrated","eligibility":"unknown","issues":errors,"mixed_tags":[]}
    policy = config["rubric"]
    grades = [GRADES[c["grade"]] for c in facts["coursework"] if c["level"] == "undergraduate" and c["course"] in ANCHORS]
    technical = "adequate"
    if sum(g < GRADES["B"] for g in grades) >= policy["technical_low_below_b_count"]:
        technical = "low"
    elif min(grades) >= GRADES[policy["technical_high_floor"]] and sum(g >= GRADES["A-"] for g in grades) >= policy["technical_high_a_range_count"]:
        technical = "high"
    entries = facts["teaching_experience"]
    performance = "no_prior_evidence" if not entries else "concern" if any(e["performance"] == "needs_improvement" for e in entries) else "effective" if any(e["performance"] == "effective" for e in entries) else "satisfactory"
    ratings = [e["rating"] for e in facts["communication_evidence"].values()]
    concerns = ratings.count("needs_improvement")
    communication = "concern" if concerns else "effective" if all(r == "effective" for r in ratings) else "satisfactory"
    interest = facts["teaching_interest"]["category"]
    tier = "borderline"
    if concerns == 2 or (technical == "low" and not (performance == "effective" and concerns == 0)):
        tier = "weak"
    elif technical != "low" and concerns == 0 and interest == "beginner_support" and performance != "concern":
        if technical == "high" or communication == "effective" or performance == "effective":
            tier = "strong"
    eligibility = "available_for_required_duties" if all(facts["availability"].values()) else "unavailable_for_required_duties"
    reasons = [f"Foundational coursework: {technical}.",f"Communication evidence: {communication}; {concerns} concerns.",f"Prior teaching performance: {performance}. No history is neutral, not adverse evidence.",f"Beginner-teaching interest: {interest}."]
    if eligibility != "available_for_required_duties":
        tier = "unrated"
        reasons.append("Required duty unavailable: separate eligibility failure, outside the merit-tier sample.")
    tags = []
    if tier == "strong" and not entries:
        tags.append("capable_first_time_ta")
    if tier == "borderline" and technical == "low" and performance == "effective" and not concerns:
        tags.append("technical_gaps_effective_teaching")
    if tier == "strong" and performance == "effective" and facts["undergraduate_gpa"] < policy["lower_gpa_mixed_ceiling"]:
        tags.append("lower_gpa_effective_teaching")
    if tier == "borderline" and technical == "high" and concerns == 1:
        tags.append("high_technical_communication_gap")
    return {"tier":tier,"eligibility":eligibility,"technical":technical,"teaching_performance":performance,"communication":communication,"communication_concerns":concerns,"teaching_months":sum(e["months"] for e in entries),"mixed_tags":tags,"reasons":reasons,"issues":[],"rubric_hash":digest(policy),"facts_hash":digest(facts),"status":"provisional_study_label"}


def make_facts(config, seed, index):
    education_rng, academic_rng, project_rng = (stream(seed,index,name) for name in ("education","academic","projects"))
    pathway = education_rng.choices(list(config["graduate_pathways"]),list(config["graduate_pathways"].values()))[0]
    if pathway == "masters":
        grad_start, grad_end = education_rng.choice([("2025-01","2026-12"),("2025-08","2027-08"),("2025-09","2027-05")])
    else:
        start_year = education_rng.choice([2023,2024,2025])
        grad_start,grad_end = f"{start_year}-09", f"{start_year + education_rng.choice([5,6])}-05"
    bs_year = int(grad_start[:4]) - (grad_start[5:] == "01") - education_rng.choice([0,0,1,2,3])
    bs_end = f"{bs_year}-05"
    bs_start = month_string(month_index(bs_end) - education_rng.choice([44,44,56]))
    education = [
        {"degree":"BS in " + education_rng.choice(MAJORS),"institution":"Fictional University A","start":bs_start,"end":bs_end,"status":"completed"},
        {"degree":"MS in Computer Science" if pathway == "masters" else "PhD in Computer Science","institution":"Fictional University B","start":grad_start,"end":grad_end,"status":"enrolled"}]
    academic_level = academic_rng.choices(range(5),config["academic_level_probabilities"])[0]
    def grade():
        return academic_rng.choices(config["grade_values"],config["grade_probabilities_by_academic_level"][academic_level])[0]
    courses = [{"course":name,"level":"undergraduate","date":month_string(month_index(bs_start)+offset),"grade":grade()} for name,offset in zip(ANCHORS,[8,20,14])]
    language = project_rng.choice(["Python","Python","Java","C++"])
    n_projects = project_rng.choices([1,2,3],config["project_count_probabilities"])[0]
    projects = []
    for i,family_id in enumerate(project_rng.sample(list(PROJECTS),n_projects)):
        family = PROJECTS[family_id]
        level = "graduate" if i > 0 and family_id in {"software_testing","graph_algorithms","database","systems"} and project_rng.random() < 0.5 else "undergraduate"
        existing = next((c for c in courses if c["course"] == family["course"] and c["level"] == level),None)
        if existing:
            completion = existing["date"]
        else:
            lo = month_index(grad_start)+3 if level == "graduate" else month_index(bs_start)+24
            hi = month_index(config["record_as_of"][:7]) if level == "graduate" else month_index(bs_end)
            completion = month_string(project_rng.randint(lo,hi))
            courses.append({"course":family["course"],"level":level,"date":completion,"grade":grade()})
        projects.append({"id":f"project-{i+1}","catalog_family":family_id,"course":family["course"],"level":level,"date":completion,"topic":project_rng.choice(family["topics"]),"tools":[language if tool == "{language}" else tool for tool in family["tools"]],"tasks":project_rng.sample(family["tasks"],project_rng.choice([2,3])),"scope":f"individual {level} course project" if project_rng.random()<0.7 else f"team {level} course project; listed tasks are the applicant's contribution","communication_activities":["submitted a written project report","gave an oral project presentation and answered questions"]})
    if len(courses) < 4:
        name = next(name for name in ["Computer Systems","Software Engineering","Algorithms"] if name not in [c["course"] for c in courses])
        courses.append({"course":name,"level":"undergraduate","date":month_string(month_index(bs_end)-7),"grade":grade()})
    experience_rng, performance_rng = stream(seed,index,"experience"),stream(seed,index,"performance")
    count = experience_rng.choices([0,1,2],config["teaching_count_probabilities"])[0]
    intro_end = courses[0]["date"]
    periods = [(f"{year}-{start}",f"{year}-{end}") for year in range(max(int(intro_end[:4]),2021),2026) for start,end in [("01","05"),("06","08"),("09","12")] if f"{year}-{start}" > intro_end and f"{year}-{end}" <= config["record_as_of"][:7]]
    periods = [(start,end) for start,end in periods if any(d["start"] <= start < end <= d["end"] for d in education)]
    entries = []
    for i,(start,end) in enumerate(sorted(experience_rng.sample(periods,count))):
        role = experience_rng.choice(list(ROLE_TASKS))
        performance = performance_rng.choices(EVIDENCE,config["performance_probabilities"])[0]
        entries.append({"id":f"teaching-{i+1}","role":role,"organization":"University Programming Support Programme","start":start,"end":end,"months":month_index(end)-month_index(start),"hours_per_week":experience_rng.choice([6,10,15,20] if role == "Teaching Assistant" else [3,4,6,8]),"topics":experience_rng.sample(["variables and conditionals","loops","functions","lists and arrays","debugging"],2),"tasks":experience_rng.sample(ROLE_TASKS[role],experience_rng.choice([2,3])),"performance":performance,"performance_note":PERFORMANCE[performance],"feedback_source":FEEDBACK_CONTEXT[role]})
    communication_rng = stream(seed,index,"communication")
    pair = communication_rng.choices(config["communication_pairs"],[p["probability"] for p in config["communication_pairs"]])[0]
    communication = {}
    for mode in ("written","oral"):
        rating = pair[mode]
        communication[mode] = {"source_project_id":communication_rng.choice(projects)["id"],"source":"course instructor feedback on the project report" if mode == "written" else "course instructor feedback on the project presentation","rating":rating,"observation":COMMUNICATION[mode][rating]}
    interest = stream(seed,index,"interest").choices(list(INTEREST),config["interest_probabilities"])[0]
    low_gpa,high_gpa = config["gpa_ranges_by_academic_level"][academic_level]
    gpa = round(academic_rng.uniform(low_gpa,min(high_gpa,gpa_ceiling(courses,config))),2)
    facts = {"applicant_id":f"TA-v2-{seed}-{index+1:05d}","review_month":config["review_month"],"record_as_of":config["record_as_of"],"education":education,"undergraduate_gpa":gpa,"gpa_scale":4.0,"coursework":courses,"technical_skills":sorted({language,*[tool for p in projects for tool in p["tools"]]}),"projects":projects,"teaching_experience":entries,"communication_evidence":communication,"teaching_interest":{"category":interest,"statement":INTEREST[interest]},"availability":{d:True for d in DUTIES}}
    return facts,academic_level


def make_pool(config):
    check_config(config)
    pool = []
    for seed in config["seeds"]:
        for index in range(config["pool_per_seed"]):
            facts,academic_level = make_facts(config,seed,index)
            errors = validate_facts(facts,config)
            require(not errors,f"Invalid generated facts for {facts['applicant_id']}: {errors}")
            rubric = evaluate(facts,config)
            pool.append({"profile_id":facts["applicant_id"],"seed":seed,"latent_academic_level":academic_level,"facts":facts,"facts_hash":digest(facts),"strength":rubric["tier"],"rubric":rubric,"designated_mixed_pattern":"none"})
    return pool


def select_allocated(pool, config):
    rng = random.Random(config["selection_seed"])
    selected,used = [],set()
    for cell in config["mixed_allocation"]:
        candidates = sorted([r for r in pool if r["profile_id"] not in used and r["strength"] == cell["tier"] and cell["pattern"] in r["rubric"]["mixed_tags"]],key=lambda r:r["profile_id"])
        require(len(candidates)>=cell["count"],f"Insufficient coverage for {cell['pattern']}")
        for row in rng.sample(candidates,cell["count"]):
            copied = deepcopy(row)
            copied["designated_mixed_pattern"] = cell["pattern"]
            selected.append(copied);used.add(row["profile_id"])
    for tier in TIERS:
        count = config["allocation"][tier] - sum(r["strength"] == tier for r in selected)
        candidates = sorted([r for r in pool if r["profile_id"] not in used and r["strength"] == tier],key=lambda r:r["profile_id"])
        require(len(candidates)>=count,f"Insufficient coverage for {tier}")
        for row in rng.sample(candidates,count):
            selected.append(deepcopy(row));used.add(row["profile_id"])
    rng.shuffle(selected)
    return selected


def summarize(rows):
    facts = [r["facts"] for r in rows]
    communication = {}
    for prior in (False,True):
        group = [f for f in facts if bool(f["teaching_experience"]) == prior]
        concerns = sum(any(e["rating"] == "needs_improvement" for e in f["communication_evidence"].values()) for f in group)
        communication["experienced" if prior else "first_time"] = {"n":len(group),"with_concern":concerns,"fraction":round(concerns/len(group),4) if group else None}
    return {"n":len(rows),"tiers":dict(Counter(r["strength"] for r in rows)),"designated_mixed":dict(Counter(r["designated_mixed_pattern"] for r in rows)),"graduate_degrees":dict(Counter(f["education"][1]["degree"] for f in facts)),"first_time_by_tier":dict(Counter(r["strength"] for r in rows if not r["facts"]["teaching_experience"])),"unavailable":sum(not all(f["availability"].values()) for f in facts),"communication_by_experience":communication,"unique_education_histories":len({digest(f["education"]) for f in facts}),"unique_grade_vectors":len({tuple(c["grade"] for c in f["coursework"] if c["course"] in ANCHORS and c["level"] == "undergraduate") for f in facts}),"unique_skill_sets":len({tuple(f["technical_skills"]) for f in facts}),"project_counts":dict(Counter(str(len(f["projects"])) for f in facts)),"project_families":dict(Counter(p["catalog_family"] for f in facts for p in f["projects"])),"unique_project_task_sets":len({tuple(sorted(p["tasks"])) for f in facts for p in f["projects"]}),"graduate_course_projects":sum(p["level"] == "graduate" for f in facts for p in f["projects"])}
