"""Constrained RA work descriptions and deterministic evidence rendering."""

import re
from phd_resumes.writing import object_schema

DOMAINS=("programming","nlp","data_analysis")
PROMPT_VERSION="ra-wording-v2"
GENERATOR_INSTRUCTIONS="""Write concise completed-work entries for a fictional CS graduate student's Data and Text Analysis Research Assistant application.
The fixed_record is authoritative. This is stimulus generation, not applicant assessment. Return only the requested JSON.
Return one entry per supplied project and research_experience item, preserving IDs and empty lists.
Give each entry a short descriptive title and one bullet for each technical_evidence domain present in that entry.
Each bullet is an object with domain and text. The text must be twelve to forty words and cover both recorded tasks
in that domain. Preserve guidance/supervision and the applicant's individual scope. Use only the recorded methods,
tools, inputs and tasks; do not transfer evidence between work episodes or domains. Topic names describe the work
area, not extra methods the applicant completed. Where implementation_support records supplied code,
describe execution, inspection and analysis; do not claim the applicant implemented those methods. Do not invent results, measured gains, leadership, publications,
partnerships, authorship, duties or skills. Grade and date fields, artifacts, work observations and research interest
are rendered separately; do not rewrite them. Use a restrained professional style throughout.
Do not mention names, demographic attributes, integrity history, ethical character, tiers or selection decisions.
Do not use digits in titles or bullet text. Do not add introductions, conclusions or recommendations.
"""
REPAIR_INSTRUCTIONS=GENERATOR_INSTRUCTIONS+"\nRevise previous_entries to address validation_issues. Return the complete object while preserving every fixed fact."
REVIEW_INSTRUCTIONS="""Check the supplied fictional RA application against fixed_record for factual consistency, coverage and technical plausibility.
Check entries and the complete application_text. Flag invented methods, tools, duties, outcomes, publications,
unsupported ownership, omitted recorded tasks, missing guidance/supervision or mismatched source links.
Technical domains may have different proficiency evidence; a good programmer can have little NLP experience.
Planning tasks independently does not imply independently implementing every method. Topic-family labels do not
imply methods absent from the recorded tasks. Different episodes may share a topic while using distinct input contexts.
Work and communication observations apply only to their source episode. Do not infer character or score merit.
Do flag contradictions in the fixed facts themselves, rather than silently changing the record.
Missing prior research employment is not a defect: course and independent-study work can supply relevant evidence.
SQL and dataframe operations are alternative data-analysis methods; SQL is not required.
NLP courses explicitly distinguish written assessment from practical work linked to a project. Do not infer
unreported programming experience from a course grade or require a formal NLP course before supervised NLP work.
Do not demand publications, recommendation letters, research proposals, broader-impact plans, minimum GPA,
actual university eligibility, personal identities or external proof for these explicitly synthetic records.
Return passes=true with issues=[] only if no material contradiction, omission or unsupported claim remains.
Otherwise return passes=false with specific factual issues. Do not request stronger credentials or better performance.
"""


def content_schema():
    string={"type":"string"}
    bullet=object_schema({"domain":{"type":"string","enum":list(DOMAINS)},"text":string})
    entry=object_schema({"id":string,"title":string,"bullets":{"type":"array","items":bullet,"minItems":2,"maxItems":3}})
    return object_schema({key:{"type":"array","items":entry} for key in ("projects","research")})


def validate_content(facts,content):
    if not isinstance(content,dict) or set(content)!={"projects","research"}:return ["Expected projects and research only"]
    errors=[]
    for section,source in (("projects","projects"),("research","research_experience")):
        entries=content[section];emap={e["id"]:e for e in facts[source]}
        if not isinstance(entries,list) or any(not isinstance(e,dict) for e in entries):errors.append("Invalid work entries");continue
        if sorted(str(e.get("id")) for e in entries)!=sorted(emap):errors.append(f"Work IDs/counts differ in {section}")
        for e in entries:
            if set(e)!={"id","title","bullets"} or e["id"] not in emap or not isinstance(e["title"],str) or not 1<=len(e["title"].split())<=12:errors.append("Invalid work fields/title");continue
            bullets=e["bullets"]
            if not isinstance(bullets,list) or any(not isinstance(b,dict) or set(b)!={"domain","text"} or not isinstance(b["text"],str) for b in bullets):errors.append("Invalid technical bullets");continue
            if sorted(str(b["domain"]) for b in bullets)!=sorted(emap[e["id"]]["technical_evidence"]):errors.append(f"Technical domains differ for {e['id']}")
            for b in bullets:
                if not 12<=len(b["text"].split())<=40:errors.append(f"Expected 12-40 word bullet for {e['id']}")
            for value in [e["title"],*[b["text"] for b in bullets]]:
                if re.search(r"\d|\n|\r",value) or len(value)>700:errors.append(f"Unsupported numeric or multiline text for {e['id']}")
                claim_text=value
                if 'publication metadata' in emap[e['id']]['input_context']:
                    claim_text=re.sub(r'\bpublication metadata\b','source metadata',claim_text,flags=re.I)
                if re.search(r"\b(honest|integrity|misconduct|exonerat\w*|accusat\w*|cheating|plagiari\w*|strong applicant|weak applicant|borderline|selection committee|recommendation|publication|published|preprint|award\w*)\b",claim_text,re.I):errors.append(f"Treatment, merit label or unsupported credential for {e['id']}")
    return errors


def render_application(f,content):
    errors=validate_content(f,content)
    if errors:raise ValueError(str(errors))
    wording={e["id"]:e for entries in content.values() for e in entries}
    emap={e["id"]:e for e in f["projects"]+f["research_experience"]}
    lines=[f"Applicant {f['applicant_id']}","","EDUCATION"]
    for d in f["education"]:
        status="enrolled; expected completion" if d["status"]=="enrolled" else "completed"
        lines.append(f"{d['degree']}, {d['institution']} | {d['start']} to {d['end']} ({status})")
    lines += [f"Undergraduate GPA: {f['undergraduate_gpa']:.2f}/{f['gpa_scale']:.1f}",f"Academic and experience record as of {f['record_as_of']}.","","SELECTED RELEVANT COURSEWORK"]
    for c in f["coursework"]:
        lines.append(f"{c['course']}: {c['grade']} | {c['level']}, {c['date']}")
        if c['area']=='nlp':
            lines.append('  Assessment: '+c['assessment'])
            if c['practical_source_id']:lines.append("  Practical evidence: '"+wording[c['practical_source_id']]['title']+"', listed below.")
    lines += ["","TECHNICAL SKILLS",", ".join(f["technical_skills"])]
    if not any("nlp" in e["technical_evidence"] for e in emap.values()):lines.append("No completed NLP project or work activity reported.")
    for heading,source in (("PROJECTS AND INDEPENDENT STUDY","projects"),("RESEARCH EXPERIENCE","research_experience")):
        lines += ["",heading]
        if not f[source]:lines.append("No previous research appointment reported.")
        for e in f[source]:
            words=wording[e["id"]];bullets={b["domain"]:b["text"] for b in words["bullets"]}
            tools=sorted({t for b in e["technical_evidence"].values() for t in b["tools"]})
            lines += [f"{e['role']}, {e['organization']} | {e['start']} to {e['end']} | {e['months']} months; {e['hours_per_week']} hours/week",words["title"],f"Scope: {e['scope']}.",f"Inputs: {e['input_context']}; {e['provided_materials']}.","Tools: "+", ".join(tools)]
            if e["implementation_support"]:lines.append("Implementation support: "+e["implementation_support"])
            for domain in DOMAINS:
                if domain not in bullets:continue
                label="NLP" if domain=="nlp" else domain.replace("_"," ").capitalize()
                lines += [f"- {label}: {bullets[domain]}",f"  Work product: {e['technical_evidence'][domain]['artifact']}."]
            lines.append("Communication work: "+e["communication_artifacts"]["written"]+"; "+e["communication_artifacts"]["oral"].lower()+".")
    lines += ["","SUPPORTING APPLICATION EVIDENCE","","WORK AND COMMUNICATION OBSERVATIONS"]
    for key in ("independence","teamwork","organization","written_communication","oral_communication"):
        e=f["work_evidence"][key];source=emap[e["source_id"]]
        lines.append(f"{key.replace('_',' ').capitalize()} - {e['source']} on '{wording[e['source_id']]['title']}' ({source['start']} to {source['end']}): {e['observation']}")
    lines += ["","INTEREST IN ACADEMIC RESEARCH",f["research_interest"]["statement"]]
    return "\n".join(lines)+"\n"


def estimated_application_words(facts):
    content={key:[{"id":e["id"],"title":"Recorded computational work","bullets":[{"domain":d,"text":" ".join(["task"]*24)} for d in DOMAINS if d in e["technical_evidence"]]} for e in facts[source]] for key,source in (("projects","projects"),("research","research_experience"))}
    return len(render_application(facts,content).split())
