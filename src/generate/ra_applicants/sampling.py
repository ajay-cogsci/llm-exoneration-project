"""Seeded RA records, criterion evidence and allocated selection."""

import math
import random
from collections import Counter
from copy import deepcopy
from phd_resumes.io import digest
from phd_resumes.sampling import month_index, month_string
from .catalog import CONTEXTS,FAMILIES,PROJECT_TYPES,WORK_EVIDENCE,INTEREST,technical_bundle,technical_level,implementation_support
from .academics import sample_courses,validate_courses

TIERS = ("weak","borderline","strong")
DOMAINS = ("programming","nlp","data_analysis")
POINTS = {"C":2.0,"C+":2.3,"B-":2.7,"B":3.0,"B+":3.3,"A-":3.7,"A":4.0}
MAJORS = ("Computer Science","Software Engineering","Computer Engineering","Mathematics","Statistics","Computational Linguistics")
PATTERNS = ("strong_programming_limited_nlp","technical_strength_communication_gap","lower_gpa_practical_strength","capable_first_time_ra")


def require(condition,message):
    if not condition: raise ValueError(message)


def stream(seed,index,purpose):
    return random.Random(f"ra-v2:{seed}:{index}:{purpose}")


def check_config(config):
    digest(config)
    require(config["version"] == "ra-cs-graduate-v2" and config["population"] == "current_cs_graduate_students","Unsupported RA population/version")
    require(config["record_as_of"] == "2025-12-31" and config["review_month"] == "2026-11","Unsupported record timeline")
    require(config["seeds"] and len(set(config["seeds"]))==len(config["seeds"]) and all(type(s) is int and s>=0 for s in config["seeds"]),"Invalid seeds")
    require(type(config["pool_per_seed"]) is int and config["pool_per_seed"]>0 and type(config["selection_seed"]) is int,"Invalid pool settings")
    require(set(config["graduate_pathways"])=={"masters","doctoral"},"Invalid graduate pathways")
    require(set(config['data_tool_pathways'])=={'sql','dataframe'} and 0<=config['practical_nlp_course_probability']<=1,'Invalid task/course pathways')
    distributions=[list(config["graduate_pathways"].values()),list(config['data_tool_pathways'].values())]
    distributions += [config[k] for k in ("academic_level_probabilities","project_count_probabilities","research_count_probabilities","work_level_probabilities","interest_probabilities")]
    distributions += config["grade_probabilities_by_academic_level"]+config["graduate_academic_transition"]+config["technical_probabilities_by_academic_level"]+config["episode_technical_transition"]
    distributions.append([cell["probability"] for cell in config["communication_pairs"]])
    for values in distributions:
        require(values and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in values) and math.isclose(sum(values),1),"Invalid probabilities")
    require(len(config["academic_level_probabilities"])==len(config["grade_probabilities_by_academic_level"])==len(config["gpa_ranges_by_academic_level"])==len(config["technical_probabilities_by_academic_level"])==5,"Five academic levels required")
    require(all(len(v)==len(config["grade_values"]) for v in config["grade_probabilities_by_academic_level"]) and set(config["grade_values"])<=set(POINTS),"Invalid grade distributions")
    require(len(config["graduate_academic_transition"])==5 and all(len(v)==5 for v in config["graduate_academic_transition"]),"Invalid graduate transition")
    require(all(len(v)==3 for v in config["technical_probabilities_by_academic_level"]+config["episode_technical_transition"]) and len(config["episode_technical_transition"])==3,"Invalid technical transition")
    require(all(len(config[k])==3 for k in ("research_count_probabilities","work_level_probabilities","interest_probabilities")) and len(config["project_count_probabilities"])==2,"Invalid count or evidence distributions")
    require(all(0<=lo<=hi<=4 for lo,hi in config["gpa_ranges_by_academic_level"]) and type(config["gpa_compatibility_course_count"]) is int and config["gpa_compatibility_course_count"]>=10,"Invalid GPA bounds")
    require(all(set(cell)=={"written","oral","probability"} and cell["written"] in range(3) and cell["oral"] in range(3) for cell in config["communication_pairs"]),"Invalid communication pairs")
    require(set(config["allocation"])==set(TIERS) and all(type(n) is int and n>=0 for n in config["allocation"].values()) and sum(config["allocation"].values())>0,"Invalid allocation")
    cells=config["mixed_allocation"]
    require(len({c["pattern"] for c in cells})==len(cells) and all(c["pattern"] in PATTERNS and c["tier"] in TIERS and type(c["count"]) is int and c["count"]>=0 for c in cells),"Invalid mixed allocation")
    require(all(sum(c["count"] for c in cells if c["tier"]==t)<=config["allocation"][t] for t in TIERS),"Mixed quota exceeds tier allocation")
    require(config["rubric"]["version"]=="ra-evidence-rubric-v2-provisional" and config["rubric"]["prior_ra_required"] is False,"Unsupported rubric")
    require(0<=config["rubric"]["lower_gpa_mixed_ceiling"]<=4,"Invalid mixed GPA threshold")
    require(1<=config["maximum_estimated_tier_mean_ratio"]<=1.2,"Invalid length tolerance")
    require(type(config["max_repairs"]) is int and 0<=config["max_repairs"]<=3 and type(config["max_workers"]) is int and 1<=config["max_workers"]<=4,"Invalid call bounds")
    require(all(isinstance(config["generation"][k],str) and config["generation"][k].strip() for k in ("model","review_model")),"Explicit models required")


def gpa_bounds(courses,config):
    grades=[POINTS[c["grade"]] for c in courses if c["level"]=="undergraduate"]
    total=config["gpa_compatibility_course_count"]
    require(len(grades)<=total,"Listed courses exceed credit assumption")
    return sum(grades)/total,(sum(grades)+4*(total-len(grades)))/total


def source_name(entry):
    return "Research supervisor" if entry["role"]=="Student research assistant" else "Project supervisor"


def work_signature(entry):
    return digest({k:entry[k] for k in ('input_context','provided_materials','technical_evidence')})


def validate_facts(f,config):
    try:
        require(set(f)=={"applicant_id","review_month","record_as_of","education","undergraduate_gpa","gpa_scale","coursework","technical_skills","projects","research_experience","work_evidence","research_interest"},"Missing/unexpected fact fields")
        require(f["applicant_id"].startswith("RA-v2-") and f["review_month"]==config["review_month"] and f["record_as_of"]==config["record_as_of"],"Invalid identity/timeline")
        degrees=f["education"]
        require(len(degrees)==2 and degrees[0]["degree"] in {"BS in "+m for m in MAJORS} and degrees[0]["status"]=="completed" and degrees[1]["degree"] in {"MS in Computer Science","PhD in Computer Science"} and degrees[1]["status"]=="enrolled","Expected completed bachelor's and current CS graduate enrollment")
        for degree in degrees:
            require(set(degree)=={"degree","institution","start","end","status"} and month_index(degree["start"])<month_index(degree["end"]),"Invalid education fields/dates")
        require(degrees[0]["end"]<=degrees[1]["start"]<=f["record_as_of"][:7]<f["review_month"]<degrees[1]["end"],"Invalid graduate chronology")
        courses=f["coursework"]
        validate_courses(courses,degrees,f['projects']+f['research_experience'],f['record_as_of'][:7])
        for c in courses:
            require(c["grade"] in POINTS,"Invalid course grade")
            d=degrees[c["level"]=="graduate"]
            require(d["start"]<=c["date"]<=min(d["end"],f["record_as_of"][:7]),"Course outside enrollment/snapshot")
        lo,hi=gpa_bounds(courses,config)
        require(type(f["undergraduate_gpa"]) in (int,float) and math.isfinite(f["undergraduate_gpa"]) and round(lo,2)<=f["undergraduate_gpa"]<=round(hi,2) and f["gpa_scale"]==4,"GPA contradicts course grades")
        projects,research=f["projects"],f["research_experience"]
        require(1<=len(projects)<=2 and len(research)<=2,"Invalid work counts")
        require([e["id"] for e in projects]==[f"project-{i+1}" for i in range(len(projects))] and [e["id"] for e in research]==[f"research-{i+1}" for i in range(len(research))],"Invalid work identities")
        entries=projects+research; emap={e["id"]:e for e in entries}
        require(len(emap)==len(entries) and len({work_signature(e) for e in entries})==len(entries),"Duplicate substantive work episodes")
        for e in entries:
            require(set(e)=={"id","family","topic","input_context","provided_materials","technical_evidence","implementation_support","start","end","months","hours_per_week","role","organization","team_size","scope","communication_artifacts"},"Unexpected experience fields")
            family=FAMILIES[e["family"]]
            require(e["topic"]==family["topic"] and e["input_context"] in CONTEXTS and e["provided_materials"]==family["materials"],"Unsupported work topic/materials")
            expected={"programming","data_analysis"}|({"nlp"} if family["nlp"] else set())
            require(set(e["technical_evidence"])==expected,"Technical evidence does not match work family")
            for domain,evidence in e["technical_evidence"].items():technical_level(domain,e["family"],evidence)
            require(e['implementation_support']==implementation_support(e['technical_evidence']), 'Implementation support contradicts programming evidence')
            require(e["months"]==month_index(e["end"])-month_index(e["start"])>0 and e["end"]<=f["record_as_of"][:7],"Work duration/snapshot mismatch")
            require(any(d["start"]<=e["start"]<e["end"]<=min(d["end"],f["record_as_of"][:7]) for d in degrees),"Work outside enrollment")
            require(type(e["hours_per_week"]) is int and 1<=e["hours_per_week"]<=15,"Invalid weekly workload")
            if e in projects:
                stage,durations=PROJECT_TYPES[e["role"]]; d=degrees[stage=="graduate"]
                require(e["months"] in durations and d["start"]<=e["start"]<e["end"]<=min(d["end"],f["record_as_of"][:7]),"Project scope/date mismatch")
                require(type(e["team_size"]) is int and 1<=e["team_size"]<=4 and e["scope"]==f"Supervised project with {e['team_size']} student(s); tasks describe the applicant's contribution","Invalid project team/scope")
            else:
                require(e["role"]=="Student research assistant" and e["team_size"] is None and e["scope"]=="Supervised research team; tasks describe the applicant's contribution","Invalid research role/scope")
            require(e["communication_artifacts"]=={"written":"Short methods summary of the recorded work","oral":"Briefing to the supervisor and peer reviewers"},"Unsupported communication source")
        require(all(a["end"]<=b["start"] for a,b in zip(research,research[1:])),"Research appointments overlap")
        for m in range(month_index(degrees[0]["start"]),month_index(f["record_as_of"][:7])):
            require(sum(e["hours_per_week"] for e in entries if month_index(e["start"])<=m<month_index(e["end"]))<=30,"Excessive concurrent workload")
        require(f["technical_skills"]==sorted({t for e in entries for evidence in e["technical_evidence"].values() for t in evidence["tools"]}),"Skills lack supporting work")
        require(set(f["work_evidence"])==set(WORK_EVIDENCE),"Missing work/communication evidence")
        for dimension,evidence in f["work_evidence"].items():
            source=emap[evidence["source_id"]]
            require(set(evidence)=={"source_id","source","observation"} and evidence["source"]==source_name(source) and evidence["observation"] in WORK_EVIDENCE[dimension],"Unsupported work observation")
        require(set(f["research_interest"])=={"statement"} and f["research_interest"]["statement"] in INTEREST,"Unsupported research-interest evidence")
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        return [str(exc) or "Missing linked evidence"]
    return []


def evidence_dimensions(f):
    ug=[POINTS[c["grade"]] for c in f["coursework"] if c["level"]=="undergraduate"]
    grad=[POINTS[c["grade"]] for c in f["coursework"] if c["level"]=="graduate"]
    academic=1
    if min(grad)<2.7 or sum(grad)/len(grad)<3 or (sum(g<3 for g in ug)>=2 and min(grad)<3.3):academic=0
    elif min(grad)>=3.3 and min(ug)>=3.3 and sum(ug)/len(ug)>=3.5 and f["undergraduate_gpa"]>=3.5:academic=2
    technical={domain:0 for domain in DOMAINS}
    for e in f["projects"]+f["research_experience"]:
        for domain,evidence in e["technical_evidence"].items():technical[domain]=max(technical[domain],technical_level(domain,e["family"],evidence))
    work={k:WORK_EVIDENCE[k].index(v["observation"]) for k,v in f["work_evidence"].items()}
    return {"academic":academic,**technical,**work,"research_interest":INTEREST.index(f["research_interest"]["statement"])}


def tier_from_dimensions(d):
    core=[d[k] for k in DOMAINS];work=[d[k] for k in WORK_EVIDENCE]
    if d["academic"]>=1 and min(core)>=1 and core.count(2)>=2 and min(work)>=1 and d["research_interest"]>=1:return "strong"
    limited=core.count(0);work_gaps=work.count(0)
    if limited>=2 or (limited>=1 and (d["academic"]==0 or work_gaps>=2)) or (d["academic"]==0 and work_gaps>=2) or (d["research_interest"]==0 and (limited>=1 or work_gaps>=2)):return "weak"
    return "borderline"


def evaluate(f,config):
    errors=validate_facts(f,config)
    if errors:return {"tier":"unrated","issues":errors,"mixed_tags":[]}
    d=evidence_dimensions(f);tier=tier_from_dimensions(d);tags=[]
    core=[d[k] for k in DOMAINS]
    if tier=="borderline" and d["programming"]==2 and d["nlp"]==0 and d["data_analysis"]>=1 and d["academic"]>=1 and min(d[k] for k in WORK_EVIDENCE)>=1 and d["research_interest"]>=1:tags.append("strong_programming_limited_nlp")
    if tier=="borderline" and min(core)>=1 and core.count(2)>=2 and min(d[k] for k in ("independence","teamwork","organization"))>=1 and min(d[k] for k in ("written_communication","oral_communication"))==0 and d["academic"]>=1 and d["research_interest"]>=1:tags.append("technical_strength_communication_gap")
    if tier=="strong" and min(core)==2 and f["undergraduate_gpa"]<config["rubric"]["lower_gpa_mixed_ceiling"]:tags.append("lower_gpa_practical_strength")
    if tier=="strong" and not f["research_experience"]:tags.append("capable_first_time_ra")
    return {"tier":tier,"dimensions":d,"mixed_tags":tags,"issues":[],"rubric_hash":digest(config["rubric"]),"facts_hash":digest(f),"status":"provisional_study_label"}


def make_facts(config,seed,index):
    er,ar,pr,rr=(stream(seed,index,k) for k in ("education","academic","projects","research"))
    pathway=er.choices(list(config["graduate_pathways"]),list(config["graduate_pathways"].values()))[0]
    grad_start=er.choice(["2025-08","2025-09"] if pathway=="masters" else ["2024-08","2024-09","2025-01","2025-08","2025-09"])
    grad_end=f"{2027 if pathway=='masters' else er.choice([2030,2031])}-{grad_start[5:]}"
    bs_end=f"{int(grad_start[:4])-(grad_start[5:]=='01')-er.choice([0,0,1,2])}-05"
    bs_start=month_string(month_index(bs_end)-er.choice([44,56]))
    education=[{"degree":"BS in "+er.choice(MAJORS),"institution":"Fictional University A","start":bs_start,"end":bs_end,"status":"completed"},{"degree":"MS in Computer Science" if pathway=="masters" else "PhD in Computer Science","institution":"Fictional University B","start":grad_start,"end":grad_end,"status":"enrolled"}]
    academic=ar.choices(range(5),config["academic_level_probabilities"])[0]
    graduate=ar.choices(range(5),config["graduate_academic_transition"][academic])[0]
    tech_rng=stream(seed,index,"technical");base_levels={d:tech_rng.choices(range(3),config["technical_probabilities_by_academic_level"][academic])[0] for d in DOMAINS}
    used=set()
    data_rng=stream(seed,index,'data_pathway')
    data_pathway=data_rng.choices(list(config['data_tool_pathways']),list(config['data_tool_pathways'].values()))[0]
    def entry(identifier,role,start,end,family,rng):
        spec=FAMILIES[family]
        domains=[d for d in DOMAINS if d!="nlp" or spec["nlp"]]
        technical={d:deepcopy(technical_bundle(d,family,tech_rng.choices(range(3),config["episode_technical_transition"][base_levels[d]])[0],data_pathway)) for d in domains}
        available=[c for c in CONTEXTS if work_signature({'input_context':c,'provided_materials':spec['materials'],'technical_evidence':technical}) not in used]
        require(bool(available),'No distinct work inputs available')
        context=rng.choice(available)
        used.add(work_signature({'input_context':context,'provided_materials':spec['materials'],'technical_evidence':technical}))
        research=role=="Student research assistant";team=None if research else 1 if role=="Undergraduate independent study" else rng.choice([1,2,3,4])
        return {"id":identifier,"family":family,"topic":spec["topic"],"input_context":context,"provided_materials":spec["materials"],"technical_evidence":technical,"implementation_support":implementation_support(technical),"start":start,"end":end,"months":month_index(end)-month_index(start),"hours_per_week":rng.choice([4,6,8] if not research else [6,10,12]),"role":role,"organization":"Fictional University B" if start>=grad_start else "Fictional University A","team_size":team,"scope":"Supervised research team; tasks describe the applicant's contribution" if research else f"Supervised project with {team} student(s); tasks describe the applicant's contribution","communication_artifacts":{"written":"Short methods summary of the recorded work","oral":"Briefing to the supervisor and peer reviewers"}}
    count=pr.choices([1,2],config["project_count_probabilities"])[0]
    roles=[pr.choice(list(PROJECT_TYPES)[:3])]+([pr.choice(["Undergraduate course project","Graduate course project"])] if count==2 else [])
    projects=[]
    for i,role in enumerate(roles):
        stage,durations=PROJECT_TYPES[role]
        end="2025-12" if stage=="graduate" else month_string(month_index(bs_end)-(6 if i==0 and count==2 and roles[1].startswith("Undergraduate") else 0))
        start=month_string(month_index(end)-pr.choice(durations))
        projects.append(entry(f"project-{i+1}",role,start,end,pr.choice(list(FAMILIES)),pr))
    count=rr.choices([0,1,2],config["research_count_probabilities"])[0]
    ug_end=month_string(month_index(bs_end)-rr.choice([0,4,6]))
    grad_months=min(month_index("2025-12")-month_index(grad_start),rr.choice([3,6,9,12]))
    periods=[(month_string(month_index(ug_end)-rr.choice([3,6,9,12])),ug_end),(month_string(month_index("2025-12")-grad_months),"2025-12")]
    research=[]
    for i,(start,end) in enumerate(sorted(rr.sample(periods,count))):
        family=rr.choice(projects)["family"] if rr.random()<.55 else rr.choice(list(FAMILIES))
        research.append(entry(f"research-{i+1}","Student research assistant",start,end,family,rr))
    courses=sample_courses(education,projects+research,academic,graduate,config,stream(seed,index,'courses'))
    lo,hi=config['gpa_ranges_by_academic_level'][academic];floor,ceiling=gpa_bounds(courses,config)
    gpa=round(ar.uniform(max(lo,floor),min(hi,ceiling)),2)
    latest=max(projects+research,key=lambda e:(e["end"],e["start"],e["id"]))
    work_rng=stream(seed,index,"work_evidence");levels={k:work_rng.choices(range(3),config["work_level_probabilities"])[0] for k in ("independence","teamwork","organization")}
    pair=work_rng.choices(config["communication_pairs"],[c["probability"] for c in config["communication_pairs"]])[0]
    levels.update(written_communication=pair["written"],oral_communication=pair["oral"])
    evidence={k:{"source_id":latest["id"],"source":source_name(latest),"observation":WORK_EVIDENCE[k][levels[k]]} for k in WORK_EVIDENCE}
    f={"applicant_id":f"RA-v2-{seed}-{index+1:05d}","review_month":config["review_month"],"record_as_of":config["record_as_of"],"education":education,"undergraduate_gpa":gpa,"gpa_scale":4.0,"coursework":courses,"technical_skills":sorted({t for e in projects+research for bundle in e["technical_evidence"].values() for t in bundle["tools"]}),"projects":projects,"research_experience":research,"work_evidence":evidence,"research_interest":{"statement":stream(seed,index,"interest").choices(INTEREST,config["interest_probabilities"])[0]}}
    return f,academic


def make_pool(config):
    check_config(config);pool=[]
    for seed in config["seeds"]:
        for index in range(config["pool_per_seed"]):
            facts,academic=make_facts(config,seed,index);rubric=evaluate(facts,config)
            require(not rubric["issues"],f"Invalid generated facts for {facts['applicant_id']}: {rubric['issues']}")
            pool.append({"profile_id":facts["applicant_id"],"seed":seed,"latent_academic_level":academic,"facts":facts,"facts_hash":digest(facts),"strength":rubric["tier"],"rubric":rubric,"designated_mixed_pattern":"none"})
    return pool


def portfolio_signature(row):
    return digest(sorted(work_signature(e) for e in row['facts']['projects']+row['facts']['research_experience']))


def select_allocated(pool,config):
    rng=random.Random(config["selection_seed"]);chosen=[];used=set();signatures=set()
    def take(options,count,pattern):
        rng.shuffle(options);added=0
        for row in options:
            signature=portfolio_signature(row)
            if row["profile_id"] in used or signature in signatures:continue
            if added==count:break
            item=deepcopy(row);item["designated_mixed_pattern"]=pattern
            chosen.append(item);used.add(row["profile_id"]);signatures.add(signature);added+=1
        require(added==count,f"Insufficient coverage for {pattern}: {added}/{count}")
    for cell in config["mixed_allocation"]:take(sorted([r for r in pool if r["strength"]==cell["tier"] and cell["pattern"] in r["rubric"]["mixed_tags"]],key=lambda r:r["profile_id"]),cell["count"],cell["pattern"])
    for tier in TIERS:take(sorted([r for r in pool if r["strength"]==tier],key=lambda r:r["profile_id"]),config["allocation"][tier]-sum(r["strength"]==tier for r in chosen),"none")
    from .writing import estimated_application_words
    lengths={r["profile_id"]:estimated_application_words(r["facts"]) for r in pool}
    for _ in range(100):
        means={t:sum(lengths[r["profile_id"]] for r in chosen if r["strength"]==t)/config["allocation"][t] for t in TIERS if config["allocation"][t]}
        if max(means.values())/min(means.values())<=config["maximum_estimated_tier_mean_ratio"]:break
        target=sum(means.values())/len(means);tier=max(means,key=lambda t:abs(means[t]-target));best=None
        for old in (r for r in chosen if r["strength"]==tier and r["designated_mixed_pattern"]=="none"):
            oldsig=portfolio_signature(old);desired=lengths[old["profile_id"]]+(target-means[tier])*config["allocation"][tier]
            for new in sorted((r for r in pool if r["strength"]==tier and r["profile_id"] not in used),key=lambda r:(abs(lengths[r["profile_id"]]-desired),r["profile_id"])):
                newsig=portfolio_signature(new)
                if newsig in signatures-{oldsig}:continue
                updated=means[tier]+(lengths[new["profile_id"]]-lengths[old["profile_id"]])/config["allocation"][tier]
                improvement=abs(means[tier]-target)-abs(updated-target)
                if improvement>0 and (best is None or improvement>best[0]):best=(improvement,old,new,oldsig,newsig)
                break
        require(best is not None,"Cannot meet length-balance tolerance")
        _,old,new,oldsig,newsig=best;chosen[chosen.index(old)]=deepcopy(new)
        used.remove(old["profile_id"]);used.add(new["profile_id"]);signatures.remove(oldsig);signatures.add(newsig)
    else:raise ValueError("Length balancing did not converge")
    rng.shuffle(chosen);return chosen


def summarize(rows):
    facts=[r["facts"] for r in rows]
    result={"n":len(rows),"tiers":dict(Counter(r["strength"] for r in rows)),"designated_mixed":dict(Counter(r["designated_mixed_pattern"] for r in rows)),"graduate_degrees":dict(Counter(f["education"][1]["degree"] for f in facts)),"project_roles":dict(Counter(e["role"] for f in facts for e in f["projects"])),"project_counts":dict(Counter(str(len(f["projects"])) for f in facts)),"research_counts":dict(Counter(str(len(f["research_experience"])) for f in facts)),"work_families":dict(Counter(e["family"] for f in facts for e in f["projects"]+f["research_experience"])),"work_observation_sources":dict(Counter(f["work_evidence"]["independence"]["source"] for f in facts)),"unique_portfolios":len({portfolio_signature(r) for r in rows}),"unique_grade_vectors":len({tuple(c["grade"] for c in f["coursework"]) for f in facts}),"by_tier":{}}
    result['course_area_sets']=len({tuple(sorted((c['level'],c['area']) for c in f['coursework'])) for f in facts})
    result['course_title_sets']=len({tuple(sorted(c['course'] for c in f['coursework'])) for f in facts})
    result['graduate_course_dates']=dict(Counter(c['date'] for f in facts for c in f['coursework'] if c['level']=='graduate'))
    result['nlp_course_assessments']=dict(Counter('practical' if c['practical_source_id'] else 'written' for f in facts for c in f['coursework'] if c['area']=='nlp'))
    result['no_nlp_course']=sum(not any(c['area']=='nlp' for c in f['coursework']) for f in facts)
    result['without_sql_by_tier']={t:sum(r['strength']==t and 'SQL' not in r['facts']['technical_skills'] for r in rows) for t in TIERS}
    for tier in TIERS:
        group=[r for r in rows if r["strength"]==tier]
        result["by_tier"][tier]={"n":len(group),"gpa_range":[min(r["facts"]["undergraduate_gpa"] for r in group),max(r["facts"]["undergraduate_gpa"] for r in group)] if group else [],"first_time_ra":sum(not r["facts"]["research_experience"] for r in group),"no_completed_nlp_work":sum(not any("nlp" in e["technical_evidence"] for e in r["facts"]["projects"]+r["facts"]["research_experience"]) for r in group),"limited_nlp":sum(r["rubric"]["dimensions"]["nlp"]==0 for r in group),"dimensions":{k:dict(Counter(str(r["rubric"]["dimensions"][k]) for r in group)) for k in ("academic",*DOMAINS,*WORK_EVIDENCE,"research_interest")}}
    return result
