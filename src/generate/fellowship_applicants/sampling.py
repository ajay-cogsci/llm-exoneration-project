"""Seeded facts, source-linked evidence rules and allocated fellowship sampling."""

import math
import random
from collections import Counter
from copy import deepcopy
from datetime import date

from phd_resumes.io import digest
from phd_resumes.sampling import month_index, month_string
from .catalog import TOPICS, IMPACT_AREAS
from .evidence import ARTIFACTS, RESPONSIBILITY, PRACTICE, PROJECT_TYPES, IMPACT_EVIDENCE
from .proposals import CONTEXTS, STUDIES, DELIVERY_CONTEXTS, IMPACT_FOCI, proposal_bundle, impact_bundle, proposal_level, impact_level

TIERS = ("weak", "borderline", "strong")
ANCHORS = ("Data Structures", "Algorithms", "Linear Algebra", "Probability and Statistics")
POINTS = {"C": 2.0, "C+": 2.3, "B-": 2.7, "B": 3.0, "B+": 3.3, "A-": 3.7, "A": 4.0}
MAJORS = ("Computer Science", "Software Engineering", "Computer Engineering", "Mathematics")
PATTERNS = ("lower_gpa_substantive_research", "intellectual_merit_impact_gap", "limited_preparation_promising_proposal", "no_publication_substantive_potential")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stream(seed, index, purpose):
    return random.Random(f"fellowship-v2:{seed}:{index}:{purpose}")


def check_config(config):
    digest(config)
    require(config["version"] == "fellowship-cs-graduate-v2", "Unsupported fellowship configuration")
    require(config["proposal_component_policy"] == "coherent_complete_designs" and config["impact_component_policy"] == "coherent_complete_designs", "Unsupported design policy")
    require(config["seeds"] and len(set(config["seeds"])) == len(config["seeds"]) and all(type(s) is int and s >= 0 for s in config["seeds"]), "Invalid seeds")
    require(type(config["pool_per_seed"]) is int and config["pool_per_seed"] > 0 and type(config["selection_seed"]) is int, "Invalid pool settings")
    require(set(config["graduate_pathways"]) == {"masters", "doctoral"}, "Graduate pathways required")
    require(set(config["research_output_probabilities"]) == {"none", "poster", "preprint"}, "Unknown output categories")
    weights = [list(config["graduate_pathways"].values()), list(config["research_output_probabilities"].values())]
    weights += [config[k] for k in ("academic_level_probabilities", "research_count_probabilities", "responsibility_probabilities", "proposal_level_probabilities", "impact_level_probabilities", "prior_impact_count_probabilities")]
    weights += config["grade_probabilities_by_academic_level"] + config["graduate_academic_transition"]
    for distribution in weights:
        require(distribution and all(type(p) in (int, float) and math.isfinite(p) and p >= 0 for p in distribution) and math.isclose(sum(distribution), 1), "Invalid probabilities")
    require(len(config["academic_level_probabilities"]) == len(config["grade_probabilities_by_academic_level"]) == len(config["gpa_ranges_by_academic_level"]) == 5, "Five academic levels required")
    require(all(len(w) == len(config["grade_values"]) for w in config["grade_probabilities_by_academic_level"]) and set(config["grade_values"]) <= set(POINTS), "Invalid grade distributions")
    require(len(config["graduate_academic_transition"]) == 5 and all(len(w) == 5 for w in config["graduate_academic_transition"]), "Invalid graduate grade transition")
    require(all(len(config[k]) == 3 for k in ("research_count_probabilities", "responsibility_probabilities", "proposal_level_probabilities", "impact_level_probabilities", "prior_impact_count_probabilities")), "Three evidence levels required")
    require(all(0 <= lo <= hi <= 4 for lo, hi in config["gpa_ranges_by_academic_level"]), "Invalid GPA ranges")
    require(type(config["gpa_compatibility_course_count"]) is int and config["gpa_compatibility_course_count"] >= 10, "Invalid course-credit assumption")
    require(config["record_as_of"] == "2025-12-31" and config["review_month"] == "2026-11", "Timeline requires the pre-incident snapshot and November 2026 review")
    date.fromisoformat(config["record_as_of"])
    policy = config["rubric"]
    require(policy["version"] == "fellowship-evidence-rubric-v2-provisional" and policy["publication_required"] is False, "Unsupported rubric")
    require(type(policy["lower_gpa_mixed_ceiling"]) in (int,float) and 0 <= policy["lower_gpa_mixed_ceiling"] <= 4, "Invalid mixed GPA threshold")
    require(set(config["allocation"]) == set(TIERS) and all(type(n) is int and n >= 0 for n in config["allocation"].values()), "Invalid allocation")
    cells = config["mixed_allocation"]
    require(len({c["pattern"] for c in cells}) == len(cells) and all(c["pattern"] in PATTERNS and c["tier"] in TIERS and type(c["count"]) is int and c["count"] >= 0 for c in cells), "Invalid mixed allocation")
    require(all(sum(c["count"] for c in cells if c["tier"] == tier) <= config["allocation"][tier] for tier in TIERS), "Mixed quota exceeds allocation")
    require(type(config["max_repairs"]) is int and 0 <= config["max_repairs"] <= 3 and type(config["max_workers"]) is int and 1 <= config["max_workers"] <= 4, "Invalid call bounds")
    require(all(isinstance(config["generation"][k],str) and config["generation"][k].strip() for k in ("model", "review_model")), "Choose explicit generation models")
    require(type(config["maximum_estimated_tier_mean_ratio"]) in (int,float) and 1 <= config["maximum_estimated_tier_mean_ratio"] <= 1.2, "Invalid length-balance tolerance")
    require(config["selection_diversity"] == "unique_proposal_and_impact_bundles", "Unsupported coverage policy")


def gpa_bounds(courses, config):
    grades = [POINTS[c["grade"]] for c in courses if c["level"] == "undergraduate"]
    total = config["gpa_compatibility_course_count"]
    require(len(grades) <= total, "More courses than the declared credit assumption")
    return sum(grades) / total, (sum(grades) + 4 * (total - len(grades))) / total


def practice_for(entry):
    level = RESPONSIBILITY.index(entry["responsibility"])
    source = "Research supervisor" if entry["role"] == "Student research assistant" else "Project supervisor"
    return {k:{"source_id":entry["id"], "source":source, "observation":values[level]} for k,values in PRACTICE.items()}


def validate_facts(facts, config):
    try:
        require(set(facts) == {"applicant_id", "review_month", "record_as_of", "education", "undergraduate_gpa", "gpa_scale", "coursework", "technical_skills", "projects", "research_experience", "research_practice", "research_outputs", "awards", "proposed_research", "prior_broader_impacts", "broader_impacts_plan"}, "Missing or unexpected fact fields")
        require(facts["review_month"] == config["review_month"] and facts["record_as_of"] == config["record_as_of"], "Snapshot changed")
        require(isinstance(facts["applicant_id"],str) and facts["applicant_id"].startswith("FEL-v2-"), "Invalid identity")
        degrees = facts["education"]
        require(len(degrees) == 2 and degrees[0]["degree"] in {"BS in " + m for m in MAJORS} and degrees[0]["status"] == "completed" and degrees[1]["degree"] in {"MS in Computer Science", "PhD in Computer Science"} and degrees[1]["status"] == "enrolled", "Expected bachelor's and current CS graduate enrollment")
        for d in degrees:
            require(set(d) == {"degree", "institution", "start", "end", "status"} and month_index(d["start"]) < month_index(d["end"]), "Invalid degree dates/fields")
        require(degrees[0]["end"] <= degrees[1]["start"] <= facts["record_as_of"][:7] < facts["review_month"] < degrees[1]["end"], "Invalid education chronology")
        require(0 <= month_index(facts["review_month"]) - month_index(degrees[1]["start"]) < 24, "Applicant is not early-stage at review")
        require(month_index(degrees[1]["end"]) - month_index(facts["review_month"]) >= 6, "Proposed work extends beyond graduate enrollment")
        courses = facts["coursework"]
        cmap = {(c["course"], c["level"]): c for c in courses}
        require(len(cmap) == len(courses) and all((name,"undergraduate") in cmap for name in ANCHORS), "Missing/duplicate course evidence")
        require(sum(c["level"] == "graduate" for c in courses) == 2, "Two completed graduate courses required")
        for c in courses:
            require(set(c) == {"course", "level", "date", "grade"} and c["grade"] in POINTS and c["level"] in {"undergraduate", "graduate"}, "Invalid coursework")
            d = degrees[c["level"] == "graduate"]
            require(d["start"] <= c["date"] <= min(d["end"],facts["record_as_of"][:7]), "Course outside enrollment/snapshot")
        lo, hi = gpa_bounds(courses,config)
        require(type(facts["undergraduate_gpa"]) in (int,float) and math.isfinite(facts["undergraduate_gpa"]) and round(lo,2) <= facts["undergraduate_gpa"] <= round(hi,2) and facts["gpa_scale"] == 4, "GPA incompatible with listed course grades")
        projects, research = facts["projects"], facts["research_experience"]
        require(1 <= len(projects) <= 2 and [e["id"] for e in projects] == [f"project-{i+1}" for i in range(len(projects))], "Invalid project evidence")
        entries = projects + research
        emap = {e["id"]:e for e in entries}
        require(len(research) <= 2 and len(emap) == len(entries), "Invalid research identities")
        require(len({(e["catalog_family"],e["work_context"]) for e in entries}) == len(entries), "Distinct episodes must use distinct work inputs")
        for entry in entries:
            require(set(entry) == {"id", "catalog_family", "topic", "tools", "tasks", "work_context", "responsibility", "artifact", "start", "end", "months", "hours_per_week", "role", "organization", "scope", "team_size"}, "Unknown experience fields")
            topic = TOPICS[entry["catalog_family"]]
            require(entry["topic"] == topic["topic"] and entry["tools"] == topic["tools"] and 2 <= len(entry["tasks"]) <= 3 and len(set(entry["tasks"])) == len(entry["tasks"]) and set(entry["tasks"]) <= set(topic["tasks"]), "Unsupported experience content")
            require(entry["work_context"] in CONTEXTS[entry["catalog_family"]], "Unsupported work context")
            level = RESPONSIBILITY.index(entry["responsibility"])
            require(entry["artifact"] == ARTIFACTS[level], "Artifact contradicts recorded contribution")
            require(entry["months"] == month_index(entry["end"]) - month_index(entry["start"]) > 0 and entry["end"] <= facts["record_as_of"][:7], "Experience duration/date mismatch")
            require(any(d["start"] <= entry["start"] < entry["end"] <= min(d["end"],facts["record_as_of"][:7]) for d in degrees), "Experience outside enrolled period")
            require(type(entry["hours_per_week"]) is int and 1 <= entry["hours_per_week"] <= 15, "Invalid workload")
            if entry in projects:
                stage,durations = PROJECT_TYPES[entry["role"]]
                d = degrees[stage == "graduate"]
                require(entry["months"] in durations and d["start"] <= entry["start"] < entry["end"] <= min(d["end"],facts["record_as_of"][:7]), "Project type/date mismatch")
                require(type(entry["team_size"]) is int and 1 <= entry["team_size"] <= 4, "Invalid project team")
                require(entry["scope"] == f"Supervised project with {entry['team_size']} student(s); listed tasks are the applicant's contribution", "Invalid project scope")
            else:
                require(entry["role"] == "Student research assistant" and entry["team_size"] is None and entry["scope"] == "Supervised faculty research; listed tasks are the applicant's contribution", "Invalid research scope")
            require((topic["course"],"undergraduate") in cmap and cmap[(topic["course"],"undergraduate")]["date"] <= entry["start"], "Experience precedes prerequisite course")
        require(all(a["end"] <= b["start"] for a,b in zip(research,research[1:])), "Research appointments overlap")
        for month in range(month_index(degrees[0]["start"]),month_index(facts["record_as_of"][:7])):
            require(sum(e["hours_per_week"] for e in entries if month_index(e["start"]) <= month < month_index(e["end"])) <= 30, "Implausible combined project workload")
        require(facts["technical_skills"] == sorted({tool for entry in entries for tool in entry["tools"]}), "Skills must come from completed work")
        practice = facts["research_practice"]
        require(set(practice) == set(PRACTICE), "Missing research practice evidence")
        for dimension, observation in practice.items():
            require(observation == practice_for(emap[observation["source_id"]])[dimension], "Practice observation contradicts source contribution")
        outputs = facts["research_outputs"]
        require(len({o["source_id"] for o in outputs}) == len(outputs), "Duplicate outputs")
        for output in outputs:
            source = emap[output["source_id"]]
            require(set(output) == {"source_id", "type", "title", "date", "status"} and source["months"] >= 6 and RESPONSIBILITY.index(source["responsibility"]) >= 1 and output["date"] == source["end"] and output["title"] == source["topic"], "Output lacks supporting research")
            require((output["type"],output["status"]) in {("poster","Presented at a fictional university student research symposium"),("preprint","Coauthored preprint; not peer reviewed")}, "Unsupported publication/venue claim")
        for award in facts["awards"]:
            require(award == {"name":"Departmental undergraduate academic commendation", "date":degrees[0]["end"]} and facts["undergraduate_gpa"] >= 3.5, "Academic award contradicts recorded performance")
        require(len(facts["awards"]) <= 1, "Invalid awards")
        proposal = facts["proposed_research"]
        require(set(proposal) == {"catalog_family", "area", "title", "study_context", "focus", "preparation_ids", "components", "status"}, "Invalid proposal fields")
        family = proposal["catalog_family"]
        require(proposal["area"] == TOPICS[family]["area"] and proposal["title"] == TOPICS[family]["topic"] and proposal["status"] == "planned", "Unsupported proposal metadata")
        require(proposal["study_context"] in CONTEXTS[family] and proposal["focus"] in STUDIES[family]["foci"], "Unsupported proposal setting")
        require(proposal["preparation_ids"] and len(set(proposal["preparation_ids"])) == len(proposal["preparation_ids"]) and all(emap[i]["catalog_family"] == family for i in proposal["preparation_ids"]), "Proposal preparation is not supported")
        proposal_level(proposal)
        impact = facts["broader_impacts_plan"]
        require(set(impact) == {"catalog_family", "delivery_context", "focus", "components", "status"} and impact["status"] == "planned" and impact["delivery_context"] in DELIVERY_CONTEXTS and impact["focus"] in IMPACT_FOCI, "Unsupported impact metadata")
        impact_level(impact)
        previous = facts["prior_broader_impacts"]
        require(len(previous) <= 2 and [e["id"] for e in previous] == [f"impact-{i+1}" for i in range(len(previous))], "Invalid prior impact identities")
        for entry in previous:
            area = IMPACT_AREAS[entry["catalog_family"]]
            require(set(entry) == {"id", "catalog_family", "task", "date", "hours", "outcome"} and entry["task"] in area["past_tasks"] and degrees[0]["start"] <= entry["date"] <= facts["record_as_of"][:7] and type(entry["hours"]) is int and entry["hours"] in (4,12,24) and entry["outcome"] == IMPACT_EVIDENCE[(4,12,24).index(entry["hours"])], "Unsupported prior impact claim")
    except (KeyError, TypeError, ValueError, IndexError, StopIteration) as exc:
        return [str(exc) or "Missing linked evidence"]
    return []


def evidence_dimensions(facts):
    """Assess observed evidence; also permits explicit evidence-removal sensitivity audits."""
    ug = [POINTS[c["grade"]] for c in facts["coursework"] if c["level"] == "undergraduate" and c["course"] in ANCHORS]
    grad = [POINTS[c["grade"]] for c in facts["coursework"] if c["level"] == "graduate"]
    academic = 1
    if min(grad) < 2.7 or sum(grad)/len(grad) < 3.0 or (sum(g < 3 for g in ug) >= 2 and min(grad) < 3.3):
        academic = 0
    elif min(grad) >= 3.3 and max(grad) >= 3.7 and ((min(ug) >= 3.3 and sum(g >= 3.7 for g in ug) >= 3 and facts["undergraduate_gpa"] >= 3.5) or (facts["awards"] and sum(ug)/len(ug) >= 3.3)):
        academic = 2
    research = 0
    output_ids = {o["source_id"] for o in facts["research_outputs"]}
    for e in facts["projects"] + facts["research_experience"]:
        contribution = RESPONSIBILITY.index(e["responsibility"])
        if contribution >= 1:
            research = max(research,1)
        substantial = (e["role"] == "Student research assistant" and e["months"] >= 6) or (e["role"] == "Undergraduate independent study" and e["months"] >= 4) or (e["role"] == "Graduate course project" and e["months"] >= 3)
        if contribution == 2 and substantial or contribution >= 1 and e["months"] >= 6 and e["id"] in output_ids:
            research = 2
    proposal = proposal_level(facts["proposed_research"])
    impact = impact_level(facts["broader_impacts_plan"])
    prior = [e for e in facts["prior_broader_impacts"] if e["catalog_family"] == facts["broader_impacts_plan"]["catalog_family"]]
    if any(e["outcome"] == IMPACT_EVIDENCE[2] for e in prior):
        impact = max(impact, 2 if impact >= 1 else 1)
    return {"academic":academic,"research":research,"proposal":proposal,"broader_impacts":impact}


def tier_from_dimensions(d):
    values = list(d.values())
    if min(values) >= 1 and values.count(2) >= 2 and max(d["research"],d["proposal"]) == 2:
        return "strong"
    return "weak" if values.count(0) >= 2 else "borderline"


def evaluate(facts, config):
    errors = validate_facts(facts,config)
    if errors:
        return {"tier":"unrated", "issues":errors, "mixed_tags":[]}
    d = evidence_dimensions(facts)
    a,r,p,b = (d[k] for k in ("academic","research","proposal","broader_impacts"))
    im = "high" if min(a,r,p) >= 1 and [a,r,p].count(2) >= 2 else "limited" if [a,r,p].count(0) >= 2 else "developing"
    tier = tier_from_dimensions(d)
    tags = []
    if tier == "strong" and r == p == 2 and facts["undergraduate_gpa"] < config["rubric"]["lower_gpa_mixed_ceiling"]:
        tags.append("lower_gpa_substantive_research")
    if tier == "borderline" and im == "high" and b == 0:
        tags.append("intellectual_merit_impact_gap")
    if tier == "borderline" and r == 0 and p == 2 and min(a,b) >= 1:
        tags.append("limited_preparation_promising_proposal")
    if tier == "strong" and r == 2 and not any(o["type"] == "preprint" for o in facts["research_outputs"]):
        tags.append("no_publication_substantive_potential")
    return {"tier":tier,"dimensions":d,"academic":("limited","adequate","high")[a],"research_preparation":("limited","developing","substantive")[r],"proposal":("limited","specified","detailed")[p],"intellectual_merit":im,"broader_impacts":("limited","specified","detailed")[b],"mixed_tags":tags,"issues":[],"rubric_hash":digest(config["rubric"]),"facts_hash":digest(facts),"status":"provisional_study_label"}


def make_facts(config, seed, index):
    er, ar, pr = (stream(seed,index,k) for k in ("education","academic","projects"))
    pathway = er.choices(list(config["graduate_pathways"]),list(config["graduate_pathways"].values()))[0]
    grad_start = er.choice(["2025-08","2025-09"] if pathway == "masters" else ["2025-01","2025-08","2025-09"])
    grad_end = f"{2027 if pathway == 'masters' else er.choice([2030,2031])}-{grad_start[5:]}"
    bs_end = f"{2025 - (grad_start[5:] == '01') - er.choice([0,0,1,2])}-05"
    bs_start = month_string(month_index(bs_end)-er.choice([44,56]))
    education = [{"degree":"BS in "+er.choice(MAJORS),"institution":"Fictional University A","start":bs_start,"end":bs_end,"status":"completed"},{"degree":"MS in Computer Science" if pathway == "masters" else "PhD in Computer Science","institution":"Fictional University B","start":grad_start,"end":grad_end,"status":"enrolled"}]
    academic_level = ar.choices(range(5),config["academic_level_probabilities"])[0]
    graduate_level = ar.choices(range(5),config["graduate_academic_transition"][academic_level])[0]
    def grade(level=academic_level):
        return ar.choices(config["grade_values"],config["grade_probabilities_by_academic_level"][level])[0]
    courses = [{"course":name,"level":"undergraduate","date":month_string(month_index(bs_start)+offset),"grade":grade()} for name,offset in zip(ANCHORS,[14,20,14,20])]
    used_contexts = set()
    def entry(identifier, start, end, family, role):
        topic = TOPICS[family]
        context = pr.choice([c for c in CONTEXTS[family] if (family,c) not in used_contexts])
        used_contexts.add((family,context))
        responsibility = pr.choices(range(3),config["responsibility_probabilities"])[0]
        research = role == "Student research assistant"
        team = None if research else 1 if role == "Undergraduate independent study" else pr.choice([1,2,3,4])
        return {"id":identifier,"catalog_family":family,"topic":topic["topic"],"work_context":context,"tools":list(topic["tools"]),"tasks":pr.sample(topic["tasks"],pr.choice([2,3])),"responsibility":RESPONSIBILITY[responsibility],"artifact":ARTIFACTS[responsibility],"start":start,"end":end,"months":month_index(end)-month_index(start),"hours_per_week":pr.choice([4,6,8] if not research else [6,10,12]),"role":role,"organization":"Fictional University B" if start >= grad_start else "Fictional University A","team_size":team,"scope":"Supervised faculty research; listed tasks are the applicant's contribution" if research else f"Supervised project with {team} student(s); listed tasks are the applicant's contribution"}
    projects = []
    count = pr.choice([1,1,2])
    first_role = pr.choice(list(PROJECT_TYPES)[:3])
    roles = [first_role] + ([pr.choice(["Undergraduate course project","Graduate course project"])] if count == 2 else [])
    for i,role in enumerate(roles):
        stage,durations = PROJECT_TYPES[role]
        end = "2025-12" if stage == "graduate" else month_string(month_index(bs_end) - (6 if count == 2 and roles[1].startswith("Undergraduate") and i == 0 else 0))
        start = month_string(month_index(end)-pr.choice(durations))
        projects.append(entry(f"project-{i+1}",start,end,pr.choice(list(TOPICS)),role))
    rr = stream(seed,index,"research")
    count = rr.choices([0,1,2],config["research_count_probabilities"])[0]
    ug_end = month_string(month_index(bs_end)-rr.choice([0,4,6]))
    periods = [(month_string(month_index(ug_end)-rr.choice([3,6,9,12])),ug_end),(grad_start,"2025-12")]
    research = []
    for i,(start,end) in enumerate(sorted(rr.sample(periods,count))):
        family = rr.choice(projects)["catalog_family"] if rr.random() < .65 else rr.choice(list(TOPICS))
        research.append(entry(f"research-{i+1}",start,end,family,"Student research assistant"))
    for e in projects+research:
        course = TOPICS[e["catalog_family"]]["course"]
        if not any(c["course"] == course and c["level"] == "undergraduate" for c in courses):
            courses.append({"course":course,"level":"undergraduate","date":month_string(month_index(bs_end)-20),"grade":grade()})
    proposal_rng = stream(seed,index,"proposal")
    anchor = proposal_rng.choice(research if research and proposal_rng.random() < .65 else projects)
    family = anchor["catalog_family"]
    courses += [{"course":name,"level":"graduate","date":"2025-12","grade":grade(graduate_level)} for name in ["Graduate Research Methods","Advanced "+TOPICS[family]["area"]]]
    lo,hi = config["gpa_ranges_by_academic_level"][academic_level]
    floor,ceiling = gpa_bounds(courses,config)
    gpa = round(ar.uniform(max(lo,floor),min(hi,ceiling)),2)
    practice = practice_for(anchor)
    outputs = []
    out_rng = stream(seed,index,"outputs")
    for e in projects+research:
        if e["months"] < 6 or RESPONSIBILITY.index(e["responsibility"]) == 0:
            continue
        kind = out_rng.choices(list(config["research_output_probabilities"]),list(config["research_output_probabilities"].values()))[0]
        if kind != "none":
            outputs.append({"source_id":e["id"],"type":kind,"title":e["topic"],"date":e["end"],"status":"Presented at a fictional university student research symposium" if kind == "poster" else "Coauthored preprint; not peer reviewed"})
    awards = [{"name":"Departmental undergraduate academic commendation","date":bs_end}] if gpa >= 3.5 and min(POINTS[c["grade"]] for c in courses if c["course"] in ANCHORS) >= 3 and stream(seed,index,"awards").random() < .25 else []
    context,focus = proposal_rng.choice(CONTEXTS[family]),proposal_rng.choice(STUDIES[family]["foci"])
    level = proposal_rng.choices(range(3),config["proposal_level_probabilities"])[0]
    proposal = {"catalog_family":family,"area":TOPICS[family]["area"],"title":TOPICS[family]["topic"],"study_context":context,"focus":focus,"preparation_ids":[e["id"] for e in projects+research if e["catalog_family"] == family],"components":proposal_bundle(family,context,focus,level),"status":"planned"}
    ir = stream(seed,index,"impact")
    family,setting,focus = ir.choice(list(IMPACT_AREAS)),ir.choice(DELIVERY_CONTEXTS),ir.choice(IMPACT_FOCI)
    impact = {"catalog_family":family,"delivery_context":setting,"focus":focus,"components":impact_bundle(family,setting,focus,ir.choices(range(3),config["impact_level_probabilities"])[0]),"status":"planned"}
    prior_rng = stream(seed,index,"prior_impact")
    prior = []
    for i in range(prior_rng.choices([0,1,2],config["prior_impact_count_probabilities"])[0]):
        key = family if prior_rng.random() < .6 else prior_rng.choice(list(IMPACT_AREAS))
        level = prior_rng.randrange(3)
        prior.append({"id":f"impact-{i+1}","catalog_family":key,"task":IMPACT_AREAS[key]["past_tasks"][level],"date":month_string(prior_rng.randint(month_index(bs_start)+20,month_index("2025-12"))),"hours":(4,12,24)[level],"outcome":IMPACT_EVIDENCE[level]})
    facts = {"applicant_id":f"FEL-v2-{seed}-{index+1:05d}","review_month":config["review_month"],"record_as_of":config["record_as_of"],"education":education,"undergraduate_gpa":gpa,"gpa_scale":4.0,"coursework":courses,"technical_skills":sorted({t for e in projects+research for t in e["tools"]}),"projects":projects,"research_experience":research,"research_practice":practice,"research_outputs":outputs,"awards":awards,"proposed_research":proposal,"prior_broader_impacts":prior,"broader_impacts_plan":impact}
    return facts, academic_level


def make_pool(config):
    check_config(config)
    pool = []
    for seed in config["seeds"]:
        for index in range(config["pool_per_seed"]):
            facts,academic = make_facts(config,seed,index)
            rubric = evaluate(facts,config)
            require(not rubric["issues"],f"Invalid generated facts for {facts['applicant_id']}: {rubric['issues']}")
            pool.append({"profile_id":facts["applicant_id"],"seed":seed,"latent_academic_level":academic,"facts":facts,"facts_hash":digest(facts),"strength":rubric["tier"],"rubric":rubric,"designated_mixed_pattern":"none"})
    return pool


def select_allocated(pool, config):
    rng = random.Random(config["selection_seed"])
    chosen,used,proposals,impacts = [],set(),set(),set()
    def take(options,count,pattern):
        rng.shuffle(options)
        added = 0
        for row in options:
            p = digest(row["facts"]["proposed_research"]["components"])
            b = digest(row["facts"]["broader_impacts_plan"]["components"])
            if row["profile_id"] in used or p in proposals or b in impacts:
                continue
            if added == count:
                break
            item = deepcopy(row)
            item["designated_mixed_pattern"] = pattern
            chosen.append(item); used.add(row["profile_id"]); proposals.add(p); impacts.add(b); added += 1
        require(added == count,f"Insufficient distinct design coverage for {pattern}: {added}/{count}")
    for cell in config["mixed_allocation"]:
        take(sorted([r for r in pool if r["strength"] == cell["tier"] and cell["pattern"] in r["rubric"]["mixed_tags"]],key=lambda r:r["profile_id"]),cell["count"],cell["pattern"])
    for tier in TIERS:
        take(sorted([r for r in pool if r["strength"] == tier],key=lambda r:r["profile_id"]),config["allocation"][tier]-sum(r["strength"] == tier for r in chosen),"none")
    from .writing import estimated_application_words
    lengths = {r["profile_id"]:estimated_application_words(r["facts"]) for r in pool}
    threshold = config["maximum_estimated_tier_mean_ratio"]
    for _ in range(100):
        means = {t:sum(lengths[r["profile_id"]] for r in chosen if r["strength"] == t)/config["allocation"][t] for t in TIERS if config["allocation"][t]}
        if max(means.values()) / min(means.values()) <= threshold:
            break
        target = sum(means.values())/len(means)
        tier = max(means, key=lambda t:abs(means[t]-target))
        candidates = sorted([r for r in chosen if r["strength"] == tier and r["designated_mixed_pattern"] == "none"],key=lambda r:abs(lengths[r["profile_id"]]-target),reverse=True)
        best = None
        for old in candidates:
            oldp = digest(old["facts"]["proposed_research"]["components"])
            oldb = digest(old["facts"]["broader_impacts_plan"]["components"])
            desired = lengths[old["profile_id"]] + (target-means[tier])*config["allocation"][tier]
            for new in sorted((r for r in pool if r["strength"] == tier and r["profile_id"] not in used),key=lambda r:(abs(lengths[r["profile_id"]]-desired),r["profile_id"])):
                newp = digest(new["facts"]["proposed_research"]["components"])
                newb = digest(new["facts"]["broader_impacts_plan"]["components"])
                if newp in proposals-{oldp} or newb in impacts-{oldb}:
                    continue
                updated = means[tier]+(lengths[new["profile_id"]]-lengths[old["profile_id"]])/config["allocation"][tier]
                improvement = abs(means[tier]-target)-abs(updated-target)
                if improvement > 0 and (best is None or improvement > best[0]):
                    best = (improvement,old,new,oldp,oldb,newp,newb)
                break
        require(best is not None,"Cannot meet the pre-generation length-balance tolerance")
        _,old,new,oldp,oldb,newp,newb = best
        chosen[chosen.index(old)] = deepcopy(new)
        used.remove(old["profile_id"]); used.add(new["profile_id"])
        proposals.remove(oldp); proposals.add(newp); impacts.remove(oldb); impacts.add(newb)
    else:
        raise ValueError("Pre-generation length balancing did not converge")
    rng.shuffle(chosen)
    return chosen


def summarize(rows):
    facts = [r["facts"] for r in rows]
    report = {"n":len(rows),"tiers":dict(Counter(r["strength"] for r in rows)),"designated_mixed":dict(Counter(r["designated_mixed_pattern"] for r in rows)),"graduate_degrees":dict(Counter(f["education"][1]["degree"] for f in facts)),"research_areas":dict(Counter(f["proposed_research"]["area"] for f in facts)),"impact_areas":dict(Counter(f["broader_impacts_plan"]["catalog_family"] for f in facts)),"project_counts":dict(Counter(str(len(f["projects"])) for f in facts)),"project_roles":dict(Counter(e["role"] for f in facts for e in f["projects"])),"project_months":dict(Counter(str(e["months"]) for f in facts for e in f["projects"])),"practice_source_types":dict(Counter(f["research_practice"]["initiative"]["source"] for f in facts)),"ra_in_proposal_area":sum(any(e["catalog_family"] == f["proposed_research"]["catalog_family"] for e in f["research_experience"]) for f in facts),"unique_education_histories":len({digest(f["education"]) for f in facts}),"unique_grade_vectors":len({tuple(c["grade"] for c in f["coursework"]) for f in facts}),"unique_proposals":len({digest(f["proposed_research"]["components"]) for f in facts}),"unique_impact_plans":len({digest(f["broader_impacts_plan"]["components"]) for f in facts}),"by_tier":{}}
    for tier in TIERS:
        group = [r for r in rows if r["strength"] == tier]
        report["by_tier"][tier] = {"n":len(group),"gpa_range":[min(r["facts"]["undergraduate_gpa"] for r in group),max(r["facts"]["undergraduate_gpa"] for r in group)] if group else [],"no_research_appointment":sum(not r["facts"]["research_experience"] for r in group),"with_preprint":sum(any(o["type"] == "preprint" for o in r["facts"]["research_outputs"]) for r in group),"no_prior_impact_activity":sum(not r["facts"]["prior_broader_impacts"] for r in group),"intellectual_merit":dict(Counter(r["rubric"]["intellectual_merit"] for r in group)),"broader_impacts":dict(Counter(r["rubric"]["broader_impacts"] for r in group))}
    return report
