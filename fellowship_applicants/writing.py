"""Constrained experience wording and fixed fellowship application components."""

import re

from phd_resumes.writing import object_schema

PROMPT_VERSION = "fellowship-wording-v2"
GENERATOR_INSTRUCTIONS = """Write concise experience entries for a fictional early-stage CS graduate student's fellowship application.
The fixed_record is authoritative. Return only the requested JSON. This is stimulus generation, not assessment.
Return one entry per supplied project and research_experience item, preserving IDs and empty lists.
Each entry has a short descriptive title and exactly two bullets of twelve to thirty words each.
Cover all listed tasks using only that entry's topic, tasks, tools and scope. Paraphrase without inventing work,
methods, results, leadership, authorship, effectiveness, measured improvements, partnerships or achievements.
Describe the applicant's own tasks, not sole ownership of a team's project. Course projects remain course projects;
research assistance remains supervised work. Do not transfer tools or tasks between entries.
The proposal, broader-impact plan, grades, dates, skills, awards, outputs and supervisor observations are fixed
and rendered separately. Do not rewrite or restate them. In particular, never turn proposed work into past work.
Do not mention publications, awards, demographic information, personal names, integrity history, character praise,
tier labels, comparative applicant judgments or selection decisions. Do not use digits in titles or bullets.
Use the same restrained professional style for every applicant. Do not add introductions or conclusions.
"""
REPAIR_INSTRUCTIONS = GENERATOR_INSTRUCTIONS + "\nRevise previous_entries to address validation_issues. Return the complete object without changing any fixed facts."
REVIEW_INSTRUCTIONS = """Review the supplied fictional fellowship application for factual consistency and scientific plausibility.
Compare entries and application_text with fixed_record. Do not assess merit, score applicants or demand stronger evidence.
Flag unsupported claims, tools, tasks, outcomes, publications, sole ownership, partnerships or past achievements.
Projects and supervised research must retain their supplied scope. Planned research and broader-impact activities
must remain future intentions, not accomplishments. Supervisor observations apply only to the linked work episode.
The complete proposals intentionally vary in methodological quality; a narrow design or weak assessment is
a study input, not a factual error to repair. Different work episodes may share a research area while using
distinct public inputs. Do not mistake topical continuity for duplicate work. Absence of a publication, award, prior research job or outreach is not a defect.
Do flag a technical or chronological contradiction within fixed_record if one exists; never silently repair it.
Dates, grades, outputs and fixed proposal components are printed separately and need not recur in generated bullets.
Return passes=true and issues=[] only if there is no material unsupported claim or contradiction.
Otherwise return passes=false with specific factual issues. Do not request essays, recommendation letters,
actual NSF eligibility evidence, real institutional names or external proof for explicitly synthetic records.
"""


def content_schema():
    string = {"type":"string"}
    entry = object_schema({"id":string,"title":string,"bullets":{"type":"array","items":string,"minItems":2,"maxItems":2}})
    return object_schema({key:{"type":"array","items":entry} for key in ("projects","research")})


def validate_content(facts, content):
    errors = []
    if not isinstance(content,dict) or set(content) != {"projects","research"}:
        return ["Expected project and research sections only"]
    for section,source in (("projects","projects"),("research","research_experience")):
        entries = content[section]
        if not isinstance(entries,list) or any(not isinstance(e,dict) for e in entries):
            errors.append(f"Invalid {section} entries")
            continue
        if sorted(str(e.get("id")) for e in entries) != sorted(e["id"] for e in facts[source]):
            errors.append(f"IDs/counts differ in {section}")
        for entry in entries:
            if set(entry) != {"id","title","bullets"} or not isinstance(entry["title"],str) or not 1 <= len(entry["title"].split()) <= 12:
                errors.append(f"Invalid fields/title in {section}")
                continue
            bullets = entry["bullets"]
            if not isinstance(bullets,list) or len(bullets) != 2 or any(not isinstance(b,str) or not 12 <= len(b.split()) <= 30 for b in bullets):
                errors.append(f"Expected two 12-30 word bullets for {entry['id']}")
                continue
            for value in [entry["title"],*bullets]:
                if re.search(r"\d|\n|\r",value) or len(value) > 500:
                    errors.append(f"Unspecified number or invalid text in {entry['id']}")
                if re.search(r"\b(honest|integrity|misconduct|exonerat\w*|accusat\w*|cheating|plagiari\w*|strong applicant|weak applicant|borderline|selection committee|recommendation|publication|published|preprint|award\w*)\b",value,re.I):
                    errors.append(f"Treatment, judgment or unsupported credential in {entry['id']}")
    return errors


def render_application(facts, content):
    errors = validate_content(facts,content)
    if errors:
        raise ValueError(str(errors))
    indexes = {key:{e["id"]:e for e in entries} for key,entries in content.items()}
    lines = [f"Applicant {facts['applicant_id']}","","EDUCATION"]
    for d in facts["education"]:
        status = "enrolled; expected completion" if d["status"] == "enrolled" else "completed"
        lines.append(f"{d['degree']}, {d['institution']} | {d['start']} to {d['end']} ({status})")
    lines += [f"Undergraduate GPA: {facts['undergraduate_gpa']:.2f}/{facts['gpa_scale']:.1f}",f"Academic and experience record as of {facts['record_as_of']}.","","RELEVANT COURSEWORK"]
    for c in facts["coursework"]:
        lines.append(f"{c['course']}: {c['grade']} | {c['level']}, {c['date']}")
    lines += ["","TECHNICAL SKILLS",", ".join(facts["technical_skills"])]
    for heading,section,source in (("PROJECTS AND INDEPENDENT STUDY","projects","projects"),("RESEARCH EXPERIENCE","research","research_experience")):
        lines += ["",heading]
        if not facts[source]:
            lines.append("No research appointment reported. Course-based preparation is listed separately.")
        for e in facts[source]:
            wording = indexes[section][e["id"]]
            lines += [f"{e['role']}, {e['organization']} | {e['start']} to {e['end']} | {e['months']} months; {e['hours_per_week']} hours/week",wording["title"],f"Inputs: {e['work_context']}.",f"Scope: {e['scope']}.","Tools: "+", ".join(e["tools"]),*["- "+b for b in wording["bullets"]],f"Contribution: {e['responsibility']}",f"Deliverable: {e['artifact']}."]
    all_wording = {**indexes["projects"], **indexes["research"]}
    all_facts = {e["id"]:e for e in facts["projects"]+facts["research_experience"]}
    lines += ["","RESEARCH OUTPUTS"]
    for o in facts["research_outputs"]:
        source = all_facts[o["source_id"]]
        lines.append(f"{o['title']} | {o['date']} | {o['status']}; source: {all_wording[o['source_id']]['title']} ({source['start']} to {source['end']}).")
    if not facts["research_outputs"]:
        lines.append("No research publications or presentations reported.")
    lines += ["","AWARDS"]
    for a in facts["awards"]:
        lines.append(f"{a['name']} | {a['date']}")
    if not facts["awards"]:
        lines.append("No awards reported.")
    lines += ["","SUPPORTING APPLICATION EVIDENCE","","INITIATIVE, INDEPENDENCE AND COLLABORATION"]
    for dimension in ("initiative","independence","collaboration"):
        e = facts["research_practice"][dimension]
        lines.append(f"{dimension.capitalize()} - {e['source']} on '{all_wording[e['source_id']]['title']}': {e['observation']}")
    proposal = facts["proposed_research"]
    lines += ["","PROPOSED RESEARCH",f"Area: {proposal['area']}",f"Topic: {proposal['title']}"]
    for key in ("question","rationale","contribution","method","comparison","evaluation","feasibility","limitations"):
        value = proposal["components"][key]
        lines.append(f"{key.capitalize()}: {value}")
    lines += ["","PRIOR BROADER-IMPACT ACTIVITIES"]
    for e in facts["prior_broader_impacts"]:
        lines.append(f"{e['date']} | {e['hours']} hours | {e['task']}. {e['outcome']}.")
    if not facts["prior_broader_impacts"]:
        lines.append("No prior broader-impact activity reported.")
    impact = facts["broader_impacts_plan"]
    lines += ["","BROADER-IMPACTS PLAN"]
    for key in ("beneficiaries","goal","activity","delivery","access","assessment"):
        value = impact["components"][key]
        lines.append(f"{key.capitalize()}: {value}")
    return "\n".join(lines)+"\n"


def estimated_application_words(facts):
    """Pre-generation length proxy with equal wording budgets for every entry."""
    content = {key:[{"id":e["id"],"title":"Computational work summary", "bullets":[" ".join(["task"]*20), " ".join(["task"]*20)]} for e in facts[source]] for key,source in (("projects","projects"),("research","research_experience"))}
    return len(render_application(facts,content).split())
