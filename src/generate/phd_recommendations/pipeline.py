"""Seeded structured letters and fixed rendering; no model or network access."""

import hashlib
import html
import math
import random
import re
import string
from collections import Counter
from pathlib import Path

from phd_resumes.io import digest, implementation_hash, read_json, read_jsonl, write_json, write_jsonl
from phd_resumes.sampling import month_index, validate_profile
from phd_resumes.writing import render_cv, validate_content

LEVELS = ("limited", "moderate", "strong")
CONTRIBUTIONS = {
    "assigned implementation tasks": "research_routine",
    "data preparation and baseline implementation": "research_routine",
    "experimental design with supervisor guidance": "research_guided",
    "designed experiments and analyzed results": "research_intellectual",
    "formulated a research question and led method development": "research_intellectual",
}
PROJECTS = {"baseline implementation": "project_baseline", "implementation and comparative evaluation": "project_comparative"}
CATEGORIES = {*CONTRIBUTIONS.values(), *PROJECTS.values(), "research_short", "course_a_range", "course_b_range", "course_below_b", "work"}
FORBIDDEN = re.compile(r"\b(honest\w*|dishonest\w*|integrity|misconduct|exonerat\w*|accusat\w*|cheating|trustworth\w*|best.ever|top\s+\d+|strong applicant|weak applicant|borderline applicant)\b", re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_policy(policy):
    require(policy["version"] in {"phd-recommendations-v1", "phd-recommendations-v2"}, "Unsupported recommendation policy")
    require(type(policy["seed"]) is int, "Seed must be an integer")
    require(type(policy["letters_per_applicant"]) is int and policy["letters_per_applicant"] == 3, "Exactly three letters are required")
    require(policy["strength_levels"] == list(LEVELS), "Unsupported letter strength scale")
    require(type(policy["short_research_months"]) is int and policy["short_research_months"] > 0, "Invalid short-research bound")
    for key in ("comparison_probability", "example_probability_when_available"):
        require(type(policy[key]) in (int, float) and math.isfinite(policy[key]) and 0 <= policy[key] <= 1, f"Invalid {key}")
    require(set(policy["strength_probabilities"]) == CATEGORIES, "Incomplete strength policy")
    for probabilities in policy["strength_probabilities"].values():
        require(isinstance(probabilities, list) and len(probabilities) == 3 and all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in probabilities) and abs(sum(probabilities) - 1) < 1e-9, "Invalid strength probabilities")
    require(policy["strength_probabilities"]["research_short"][2] == 0, "Short research cannot receive a strong research letter in v1")
    if policy["version"] == "phd-recommendations-v2":
        # v2 removes endorsements that contradict the grade the letter cites.
        require(policy["strength_probabilities"]["course_a_range"][0] == 0, "An A-range course letter cannot be a limited endorsement in v2")
        require(policy["strength_probabilities"]["course_b_range"][2] == 0, "A B-range course letter cannot be a strong endorsement in v2")
    formatter = string.Formatter()
    for name, fields in (("endorsement_templates", {"scope"}), ("comparison_templates", {"scope", "group"})):
        require(set(policy[name]) == set(LEVELS), "Incomplete templates")
        for template in policy[name].values():
            parsed = list(formatter.parse(template))
            require({field for _, field, _, _ in parsed if field is not None} == fields and all(not spec and not conversion for _, _, spec, conversion in parsed), "Unsupported template fields")
            require(not FORBIDDEN.search(template) and "\n" not in template, "Forbidden template language")
    require(policy["example_template"] == "As a specific example of the applicant's work, the writer cites this recorded activity: {activity}", "Unsupported example template")


def rng(policy, applicant_id, purpose):
    # Each decision has a separate stream: adding an example cannot change strength.
    return random.Random(int(digest([policy["seed"], applicant_id, purpose]), 16))


def weighted_level(probabilities, generator):
    draw, total = generator.random(), 0.0
    for level, probability in zip(LEVELS, probabilities):
        total += probability
        if draw < total:
            return level
    return LEVELS[-1]


def course_category(grade):
    if grade in {"A+", "A", "A-"}:
        return "course_a_range"
    if grade in {"B+", "B"}:
        return "course_b_range"
    require(grade in {"B-", "C+", "C", "C-", "D", "F"}, "Unknown course grade")
    return "course_below_b"


def select_sources(facts, policy):
    """One research writer if available, one graded-course writer, then a
    course-project writer. Without research, use a work writer; fall back to
    distinct graded-course writers if a source is absent. No applicant tier input.
    """
    pid = facts["applicant_id"]
    research = sorted(facts["research_experience"], key=lambda e: (-e["months"], e["id"]))
    work = sorted(facts["work_experience"], key=lambda e: (-e["months"], e["id"]))
    courses = sorted(facts["coursework"], key=lambda e: e["course"])
    rng(policy, pid, "course-selection").shuffle(courses)
    projects = sorted((e for e in facts["projects"] if e["kind"] == "technical course project"), key=lambda e: e["id"])
    require(courses, "No eligible academic recommender")
    selected = []
    if research:
        selected.append(("research_experience", research[0]["id"]))
    selected.append(("coursework", courses.pop()["course"]))
    if projects:
        selected.append(("projects", projects[0]["id"]))
    if len(selected) < 3 and work:
        selected.append(("work_experience", work[0]["id"]))
    while len(selected) < 3 and courses:
        selected.append(("coursework", courses.pop()["course"]))
    require(len(selected) == 3, "Insufficient eligible sources for three distinct writers")
    return selected


def source_details(facts, content, section, key, policy):
    key_name = "course" if section == "coursework" else "id"
    matches = [e for e in facts[section] if e[key_name] == key]
    require(len(matches) == 1, "Missing or ambiguous recommender source")
    entry = matches[0]
    relation = {"source_section": section, "source_id": key, "start": None, "end": None, "months": None, "year": None}
    examples = []
    if section in {"research_experience", "work_experience"}:
        relation.update({k: entry[k] for k in ("start", "end", "months")})
        require(month_index(entry["end"]) - month_index(entry["start"]) == entry["months"] > 0 and entry["end"] <= facts["review_month"], "Invalid observation period")
        research = section == "research_experience"
        writer = "research supervisor" if research else "work supervisor"
        scope = "research preparation" if research else "performance in the recorded work role"
        group = "other students the writer has supervised in research" if research else "other students the writer has supervised in similar work roles"
        relation["description"] = f"The writer supervised the applicant as {entry['role']} at {entry['organization']} from {entry['start']} to {entry['end']} ({entry['months']} {'month' if entry['months'] == 1 else 'months'})."
        category = CONTRIBUTIONS[entry["contribution"]] if research else "work"
        if research and entry["months"] < policy["short_research_months"]:
            category = "research_short"
        content_section = "research" if research else "work"
    elif section == "coursework":
        writer, scope = "course instructor", f"academic preparation in {entry['course']}"
        group = "other students the writer has taught in the same subject"
        relation["description"] = f"The writer taught the applicant in {entry['course']}, for which the recorded grade is {entry['grade']}."
        category, content_section = course_category(entry["grade"]), None
    else:
        require(section == "projects" and entry["kind"] == "technical course project", "Only a recorded course project can have a course-project instructor")
        require(entry["year"] <= int(facts["review_month"][:4]), "Project occurs after application review")
        writer, scope = "course instructor", "technical project work"
        group = "other students the writer has taught on comparable technical course projects"
        relation["year"] = entry["year"]
        title = next(e["title"] for e in content["projects"] if e["id"] == key)
        relation["description"] = f"The writer was the course instructor for the applicant's recorded technical course project, {title} ({entry['year']})."
        category, content_section = PROJECTS[entry["scope"]], "projects"
    if content_section:
        description = next(e for e in content[content_section] if e["id"] == key)
        examples = [{"section": content_section, "source_id": key, "bullet_index": i, "text": bullet} for i, bullet in enumerate(description["bullets"])]
    return {"writer_type": writer, "relationship": relation, "scope": scope, "comparison_group": group, "assignment_category": category, "available_examples": examples}


def summary_text(letter, policy):
    parts = [letter["relationship"]["description"], policy["endorsement_templates"][letter["strength_level"]].format(scope=letter["scope"])]
    if letter["compares_with_other_students"]:
        parts.append(letter["comparison"]["text"])
    if letter["gives_specific_example"]:
        parts.append(policy["example_template"].format(activity=letter["example"]["text"]))
    return " ".join(parts)


def build_record(applicant, policy):
    check_policy(policy)
    facts, content = applicant["facts"], applicant["content"]
    pid, letters = facts["applicant_id"], []
    for i, (section, key) in enumerate(select_sources(facts, policy), 1):
        details = source_details(facts, content, section, key, policy)
        probabilities = policy["strength_probabilities"][details["assignment_category"]]
        level = weighted_level(probabilities, rng(policy, pid, f"letter-{i}-strength"))
        compares = rng(policy, pid, f"letter-{i}-comparison").random() < policy["comparison_probability"]
        examples = details.pop("available_examples")
        specific = bool(examples) and rng(policy, pid, f"letter-{i}-example-present").random() < policy["example_probability_when_available"]
        example = rng(policy, pid, f"letter-{i}-example-choice").choice(examples) if specific else None
        comparison = None
        group = details.pop("comparison_group")
        if compares:
            comparison = {"group": group, "text": policy["comparison_templates"][level].format(group=group, scope=details["scope"])}
        letter = {"letter_id": f"L{i}", "writer_id": f"{pid}-REF{i}", **details, "strength_level": level, "compares_with_other_students": compares, "gives_specific_example": specific, "comparison": comparison, "example": example}
        letter["summary"] = summary_text(letter, policy)
        letters.append(letter)
    return {"applicant_id": pid, "facts_hash": digest(facts), "content_hash": digest(content), "cv_hash": digest(applicant["cv"]), "policy_hash": digest(policy), "letters": letters}


def validate_record(applicant, record, policy):
    """Reject unsupported observations and flag/content disagreement, then
    replay the saved policy to detect edited assignments or templates.
    """
    check_policy(policy)
    facts, content = applicant["facts"], applicant["content"]
    pid = facts["applicant_id"]
    require(record["applicant_id"] == pid, "Applicant mismatch")
    for key, value in (("facts_hash", facts), ("content_hash", content), ("cv_hash", applicant["cv"]), ("policy_hash", policy)):
        require(record[key] == digest(value), f"{key} mismatch")
    letters = record["letters"]
    require(len(letters) == 3 and len({e["writer_id"] for e in letters}) == 3 and len({e["letter_id"] for e in letters}) == 3, "Exactly three distinct writers/letters required")
    for letter in letters:
        require(letter["strength_level"] in LEVELS, "Unknown endorsement")
        for flag in ("compares_with_other_students", "gives_specific_example"):
            require(type(letter[flag]) is bool, "Flags must be yes/no booleans")
        relation = letter["relationship"]
        expected = source_details(facts, content, relation["source_section"], relation["source_id"], policy)
        require(relation == expected["relationship"] and letter["writer_type"] == expected["writer_type"] and letter["scope"] == expected["scope"], "Writer observation/history does not match source")
        require(letter["assignment_category"] == expected["assignment_category"], "Endorsement basis mismatch")
        require(policy["strength_probabilities"][letter["assignment_category"]][LEVELS.index(letter["strength_level"])] > 0, "Endorsement is ineligible for this source")
        require(letter["compares_with_other_students"] == (letter["comparison"] is not None), "Comparison flag disagrees with content")
        if letter["comparison"]:
            require(letter["comparison"]["group"] == expected["comparison_group"], "Comparison group outside writer scope")
            require(letter["comparison"]["text"] == policy["comparison_templates"][letter["strength_level"]].format(group=expected["comparison_group"], scope=expected["scope"]), "Comparison differs from fixed template")
        require(letter["gives_specific_example"] == (letter["example"] is not None), "Example flag disagrees with content")
        if letter["example"]:
            require(letter["example"] in expected["available_examples"], "Example is not an exact activity observed by this writer")
        require(letter["summary"] == summary_text(letter, policy), "Summary differs from fixed template")
        require(not FORBIDDEN.search(letter["summary"]), "Treatment, applicant-tier, or exceptional-praise leakage")
    require(record == build_record(applicant, policy), "Record differs from seeded policy; regenerate in a new version")


def render_letters(record):
    lines = [f"Applicant {record['applicant_id']}", "", "RECOMMENDATION SUMMARIES"]
    for letter in record["letters"]:
        lines += ["", f"Recommendation {letter['letter_id'][1:]}", f"Writer type: {letter['writer_type']}", f"Strength level: {letter['strength_level']}", "Compares applicant with other students: " + ("Yes" if letter["compares_with_other_students"] else "No"), "Gives a specific example of the applicant's work: " + ("Yes" if letter["gives_specific_example"] else "No"), letter["summary"]]
    return "\n".join(lines) + "\n"


def contained_file(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), "Source paths must be relative")
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()) and path.is_file(), "Source path escapes run or is missing")
    return path


def load_applicants(source):
    source = Path(source).resolve()
    rows, manifest = read_jsonl(source / "profiles.jsonl"), read_json(source / "resume_manifest.json")
    ids = [row["profile_id"] for row in rows]
    mids = [entry["profile_id"] for entry in manifest]
    require(ids and len(ids) == len(set(ids)) and len(mids) == len(set(mids)) and set(ids) == set(mids), "Manifest/profile identity mismatch")
    by_id = {entry["profile_id"]: entry for entry in manifest}
    applicants = []
    for row in sorted(rows, key=lambda r: r["profile_id"]):
        require(re.fullmatch(r"[A-Za-z0-9_-]+", row["profile_id"]), "Unsafe applicant identifier")
        require(not validate_profile(row), f"Invalid source profile {row['profile_id']}")
        item, facts = by_id[row["profile_id"]], row["facts"]
        content_path = contained_file(source, item["content_source"])
        content = read_json(content_path)
        cv = contained_file(source, item["resume"]).read_text(encoding="utf-8")
        require(not validate_content(facts, content), "Source prose failed its original constraints")
        require(cv == render_cv(facts, content) and digest(cv) == item["cv_hash"] and digest(facts) == item["facts_hash"], "Source CV/facts hash or render mismatch")
        status_path = content_path.parent / "status.json" if content_path.name == "content.json" else content_path.with_name(content_path.name.replace(".content.json", ".status.json"))
        require(status_path.is_file(), "Missing accepted-generation status")
        status = read_json(status_path)
        require(status["status"] == "ready_for_human_review" and status["facts_hash"] == digest(facts) and not status.get("issues") and status.get("review") == {"passes": True, "issues": []}, "Source CV was not accepted by factual checks")
        applicants.append({"facts": facts, "content": content, "cv": cv})
    return applicants


def tree_hash(root):
    root = Path(root)
    return digest({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts})


def distributions(records):
    letters = [letter for record in records for letter in record["letters"]]
    return {
        "writer_types": dict(Counter(l["writer_type"] for l in letters)),
        "strength_levels": dict(Counter(l["strength_level"] for l in letters)),
        "flag_combinations": dict(Counter(f"comparison={l['compares_with_other_students']},example={l['gives_specific_example']}" for l in letters)),
        "by_source": {source: {"n": len(group), "strength_levels": dict(Counter(l["strength_level"] for l in group)), "comparisons": sum(l["compares_with_other_students"] for l in group), "examples": sum(l["gives_specific_example"] for l in group)} for source in ("research_experience", "coursework", "projects", "work_experience") if (group := [l for l in letters if l["relationship"]["source_section"] == source])},
        "summary_words": {"min": min(len(l["summary"].split()) for l in letters), "max": max(len(l["summary"].split()) for l in letters)},
    }


def index_html(applicants, records):
    escape, cards = html.escape, []
    for applicant, record in zip(applicants, records):
        pid = record["applicant_id"]
        cards.append(f'<details><summary>{escape(pid)} · {escape(applicant["facts"]["research_area"])}</summary><p><a href="applications/{pid}.txt">Complete application</a> · <a href="recommendations/{pid}.txt">Three recommendations</a> · <a href="resumes/{pid}.txt">Original CV</a></p><h3>CV</h3><pre>{escape(applicant["cv"])}</pre><h3>Recommendations</h3><pre>{escape(render_letters(record))}</pre></details>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PhD CVs with recommendation summaries</title>
<style>body{font:16px/1.55 system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#18232d;background:#f6f8fa}h1{line-height:1.2}input{font:inherit;padding:10px;width:95%;margin:16px 0}details{background:white;border:1px solid #d4dce5;border-radius:8px;margin:12px 0;padding:16px}summary{cursor:pointer;font-weight:650}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.65 system-ui,sans-serif}a{color:#145a96}.note{color:#435362}</style>
<h1>PhD applications with recommendation summaries</h1><p>''' + str(len(records)) + ''' unchanged CVs, each accompanied by three summaries written from fixed templates.</p><p class="note">Strength level refers to the recommendation, not the applicant's CV tier. Writer relationships, endorsement levels and comparisons are synthetic. These new summaries have automated checks; human review of them is not recorded.</p><p><a href="README.md">Method and limitations</a> · <a href="validation.json">Automated validation</a></p><label for="search">Find an applicant or phrase</label><input id="search" placeholder="Applicant ID, research area, or text"><p id="count"></p>''' + "\n".join(cards) + '''<script>const s=document.querySelector('#search'),d=[...document.querySelectorAll('details')],c=document.querySelector('#count');function filter(){let n=0;for(const e of d){e.hidden=!e.textContent.toLowerCase().includes(s.value.toLowerCase());if(!e.hidden)n++;}c.textContent=n+' of '+d.length+' applicants';}s.addEventListener('input',filter);filter();</script></html>'''


def generate(source, out, policy, applicant_ids=None):
    check_policy(policy)
    source, out = Path(source).resolve(), Path(out).resolve()
    require(not out.exists() and not out.is_relative_to(source), "Choose a new output directory outside the source run")
    before = tree_hash(source)
    applicants = load_applicants(source)
    if applicant_ids is not None:
        requested = set(applicant_ids)
        require(requested and len(requested) == len(applicant_ids) and requested <= {a['facts']['applicant_id'] for a in applicants}, "Invalid/duplicate requested applicant IDs")
        applicants = [a for a in applicants if a['facts']['applicant_id'] in requested]
    records = [build_record(a, policy) for a in applicants]
    for a, record in zip(applicants, records):
        validate_record(a, record, policy)
    require(tree_hash(source) == before, "Source changed during generation")
    # All applicants must validate before any output is created.
    out.mkdir(parents=True)
    write_json(out / "policy.json", policy)
    write_jsonl(out / "inputs" / "applicants.jsonl", applicants)
    write_jsonl(out / "recommendations.jsonl", records)
    for folder in ("resumes", "recommendations", "applications"):
        (out / folder).mkdir()
    manifest = []
    for applicant, record in zip(applicants, records):
        pid = record["applicant_id"]
        letters = render_letters(record)
        packet = applicant["cv"] + "\n" + letters
        for folder, text in (("resumes", applicant["cv"]), ("recommendations", letters), ("applications", packet)):
            (out / folder / f"{pid}.txt").write_text(text, encoding="utf-8")
        manifest.append({"applicant_id": pid, "facts_hash": record["facts_hash"], "cv_hash": record["cv_hash"], "recommendations_hash": digest(letters), "application_hash": digest(packet)})
    write_json(out / "manifest.json", manifest)
    (out / "index.html").write_text(index_html(applicants, records), encoding="utf-8")
    code = Path(__file__).parent
    for package in (code, code.parent / "phd_resumes"):
        for p in sorted(package.glob("*.py")):
            target = out / "implementation" / package.name / p.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(p.read_bytes())
    write_json(out / "provenance.json", {"source_directory": str(source), "source_tree_hash": before, "source_profile_count": len(read_jsonl(source / "profiles.jsonl")), "selected_applicant_ids": [r['applicant_id'] for r in records], "policy_hash": digest(policy), "implementation_hash": digest({p.name: p.read_text() for p in sorted(code.glob('*.py'))}), "cv_implementation_hash": implementation_hash(), "api_calls": 0, "cv_labels": "Existing CV-only labels are unchanged and are not inputs to letter generation.", "treatment_use": "Reuse each exact application file across integrity conditions. This module does not generate conditions."})
    (out / "README.md").write_text(RUN_README, encoding="utf-8")
    return verify(out, source)


def verify(out, source=None):
    out = Path(out).resolve()
    policy, applicants = read_json(out / "policy.json"), read_jsonl(out / "inputs" / "applicants.jsonl")
    records, manifest = read_jsonl(out / "recommendations.jsonl"), read_json(out / "manifest.json")
    provenance = read_json(out / "provenance.json")
    ids = [a["facts"]["applicant_id"] for a in applicants]
    require(ids and len(ids) == len(set(ids)) and ids == [r["applicant_id"] for r in records] == [r["applicant_id"] for r in manifest] == provenance["selected_applicant_ids"], "Output identity/count mismatch")
    require(provenance["policy_hash"] == digest(policy), "Policy provenance mismatch")
    snapshot = out / "implementation" / "phd_recommendations"
    require(provenance["implementation_hash"] == digest({p.name: p.read_text() for p in sorted(snapshot.glob('*.py'))}), "Implementation snapshot mismatch")
    core_snapshot = out / "implementation" / "phd_resumes"
    require(provenance["cv_implementation_hash"] == digest({p.name: p.read_text() for p in sorted(core_snapshot.glob('*.py'))}) == implementation_hash(), "CV dependency drift; verify using the frozen implementation")
    require(provenance["implementation_hash"] == digest({p.name: p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))}), "Recommendation implementation drift; verify using the frozen implementation")
    for a, r, m in zip(applicants, records, manifest):
        require(not validate_content(a["facts"], a["content"]) and a["cv"] == render_cv(a["facts"], a["content"]), "Copied input CV is inconsistent")
        validate_record(a, r, policy)
        pid, letters = r["applicant_id"], render_letters(r)
        require(m == {"applicant_id": pid, "facts_hash": digest(a["facts"]), "cv_hash": digest(a["cv"]), "recommendations_hash": digest(letters), "application_hash": digest(a["cv"] + "\n" + letters)}, "Manifest hash mismatch")
        for folder, text in (("resumes", a["cv"]), ("recommendations", letters), ("applications", a["cv"] + "\n" + letters)):
            require((out / folder / f"{pid}.txt").read_text(encoding="utf-8") == text, "Export differs from validated content")
    for folder in ("resumes", "recommendations", "applications"):
        require({p.name for p in (out / folder).iterdir()} == {f"{pid}.txt" for pid in ids}, "Unexpected/missing export files")
    require((out / "index.html").read_text(encoding="utf-8") == index_html(applicants, records), "Browser index differs from validated records")
    source_verified = None
    if source is not None:
        require(tree_hash(source) == provenance["source_tree_hash"], "Original source run changed")
        originals = {a['facts']['applicant_id']: a for a in load_applicants(source)}
        require(all(originals[pid] == a for pid, a in zip(ids, applicants)), "Copied source inputs changed")
        source_verified = True
    result = {"applicants": len(records), "letters": 3 * len(records), "api_calls": 0, "checks": {"three_distinct_writers_each": True, "relationships_and_examples_match_sources": True, "flags_match_content": True, "seeded_assignments_reproduced": True, "templates_and_export_hashes_match": True, "original_source_tree_unchanged": source_verified}, "distribution": distributions(records), "new_recommendations_human_review_completed": False, "limitations": ["Endorsements and peer comparisons are synthetic judgments; their distributions are provisional.", "A grade-only instructor has no task example; example probability is applied only where recorded activity exists.", "Exact wording is controlled, but factual checks cannot establish realistic endorsement distributions or absence of evaluator bias.", "Prior human reviewer feedback on the original CVs motivated this implementation; these newly rendered summaries have not received that person's review."]}
    write_json(out / "validation.json", result)
    return result


RUN_README = """# Three recommendation summaries per PhD applicant

Open `index.html` to browse each unchanged CV and its three recommendation
summaries. `applications/` contains ready-to-use CV-plus-recommendation packets;
`recommendations/` contains the summaries alone; `resumes/` contains exact copies
of the source CVs. Every letter exposes the reviewer's four fields: writer type,
strength level, comparison yes/no, and specific-example yes/no.

All summaries use fixed fill-in templates. No new model calls were made.
`recommendations.jsonl` stores the fields and their source links. `policy.json`
contains the exact templates, seed, strength probabilities and assumptions.
`inputs/applicants.jsonl` preserves the facts and previously accepted CV prose.
`manifest.json` hashes the unchanged CV and complete packet. `provenance.json`
identifies the source run and implementation; `implementation/` saves the new
module. `validation.json` reports automated checks and observed distributions.

The recommendation scale is limited / moderate / strong. These describe the
writer's endorsement, not the applicant's CV tier. Writer relationships,
endorsement judgments and comparisons are explicit synthetic additions. Grades,
dates and activities are preserved. Examples quote an accepted CV bullet
exactly and come only from that writer's linked research, work, or course-project
entry. A course-project instructor is not claimed to have taught any particular
named graded course. Grade-only letters have no specific work example.

For each applicant, use the longest research entry if present, a seeded choice
of graded course, and the first recorded technical course project. If research
is absent, use a work supervisor. Missing sources fall back to distinct graded
courses. Three distinct fictional writers are assigned; identities and their
comparative assessments were not present in the original CV. Academic grades,
research contribution/scope and project scope determine probability categories;
the applicant tier and latent variables never enter this stage. A short research
letter (under three months) is at most moderate in v1. Neither this threshold nor
the probabilities are empirically calibrated admissions rules. No exceptional
best-ever comparisons are used. The two flags use separate seeded draws, with
examples eligible only when a concrete activity exists. Flag frequencies need
not be equal by writer type or applicant tier.

Reuse the exact complete packet for an applicant across integrity conditions.
Do not regenerate letters for each condition. Applicant strength labels remain
CV-only; this module does not relabel applicants or estimate admission chances.
Validation checks internal consistency and reproducibility, not the truth of
synthetic endorsements or perceived merit. Prior human review of the original
CVs supplied the requirements; human review of these new summaries is not
recorded. No reviewer was contacted by this module.
"""
