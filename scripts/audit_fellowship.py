"""Offline chronology, evidence coverage and sensitivity checks of a fellowship export."""

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fellowship_applicants.sampling import evidence_dimensions, tier_from_dimensions
from fellowship_applicants.writing import estimated_application_words


def sensitivity(rows):
    report = {}
    for intervention in ("graduate_grades_to_C","remove_research_appointments","remove_outputs","remove_awards","remove_prior_impact"):
        dimensions = Counter(); changed = []; eligible = 0
        for row in rows:
            f = deepcopy(row["facts"])
            before = evidence_dimensions(f)
            if intervention == "graduate_grades_to_C":
                eligible += any(c["grade"] != "C" for c in f["coursework"] if c["level"] == "graduate")
                for c in f["coursework"]:
                    if c["level"] == "graduate": c["grade"] = "C"
            else:
                field = {"remove_research_appointments":"research_experience","remove_outputs":"research_outputs","remove_awards":"awards","remove_prior_impact":"prior_broader_impacts"}[intervention]
                eligible += bool(f[field]); f[field] = []
                if field == "research_experience":
                    f["research_outputs"] = [o for o in f["research_outputs"] if o["source_id"].startswith("project-")]
            after = evidence_dimensions(f)
            dimensions.update(k for k in before if before[k] != after[k])
            if tier_from_dimensions(after) != row["strength"]:
                changed.append({"profile_id":row["profile_id"],"before":row["strength"],"after":tier_from_dimensions(after)})
        report[intervention] = {"affected_records":eligible,"dimension_changes":dict(dimensions),"tier_changes":len(changed),"changes":changed}
    return report


def audit(root):
    root = Path(root)
    rows = [json.loads(line) for line in (root/"profiles.jsonl").read_text().splitlines()]
    config = json.loads((root/"config.json").read_text())
    inputs = [json.loads(line) for line in (root/"evaluator_inputs.jsonl").read_text().splitlines()]
    errors, lengths, estimates = [], {t:[] for t in config["allocation"]}, {t:[] for t in config["allocation"]}
    def check(value, message):
        if not value: errors.append(message)
    def month(value):
        year,number = map(int,value.split("-")); return year*12+number
    points = {"C":2,"C+":2.3,"B-":2.7,"B":3,"B+":3.3,"A-":3.7,"A":4}
    check(len(rows) == sum(config["allocation"].values()),"Applicant count differs from allocation")
    check(dict(Counter(r["strength"] for r in rows)) == config["allocation"],"Tier allocation differs")
    check(len({r["profile_id"] for r in rows}) == len(rows),"Duplicate applicant identity")
    check(len(inputs) == len(rows),"Missing evaluator inputs")
    ra_continuity = 0
    for row in rows:
        pid,f = row["profile_id"],row["facts"]
        text = (root/"applications"/(pid+".txt")).read_text()
        lengths[row["strength"]].append(len(text.split())); estimates[row["strength"]].append(estimated_application_words(f))
        grad = f["education"][-1]
        check(grad["degree"] in {"MS in Computer Science","PhD in Computer Science"},pid+": not a CS graduate")
        check(0 <= month(f["review_month"])-month(grad["start"]) < 24,pid+": not early-stage at review")
        check(month(grad["end"])-month(f["review_month"]) >= 6,pid+": proposal exceeds enrollment")
        ug = [c for c in f["coursework"] if c["level"] == "undergraduate"]
        total = config["gpa_compatibility_course_count"]
        remainder = f["undergraduate_gpa"]*total-sum(points[c["grade"]] for c in ug)
        check(-.005*total <= remainder <= 4*(total-len(ug))+.005*total,pid+": incompatible GPA and course grades")
        entries = f["projects"]+f["research_experience"]
        emap = {e["id"]:e for e in entries}
        check(len({(e["catalog_family"],e["work_context"]) for e in entries}) == len(entries),pid+": duplicate work inputs")
        for e in entries:
            check(month(e["end"])-month(e["start"]) == e["months"],pid+": wrong experience duration")
            check(e["end"] <= f["record_as_of"][:7],pid+": experience after snapshot")
            check(any(d["start"] <= e["start"] < e["end"] <= d["end"] for d in f["education"]),pid+": work outside enrollment")
            for value in (e["work_context"],e["responsibility"],e["artifact"]): check(value in text,pid+": omitted contribution evidence")
        for m in range(month(f["education"][0]["start"]),month(f["record_as_of"][:7])):
            check(sum(e["hours_per_week"] for e in entries if month(e["start"]) <= m < month(e["end"])) <= 30,pid+": excessive concurrent workload")
        for output in f["research_outputs"]:
            e = emap.get(output["source_id"])
            check(e is not None and e["months"] >= 6 and output["date"] == e["end"],pid+": unsupported output")
        for field in ("proposed_research","broader_impacts_plan"):
            for value in f[field]["components"].values(): check(value in text,pid+": omitted or altered "+field+" component")
        ra_continuity += any(e["catalog_family"] == f["proposed_research"]["catalog_family"] for e in f["research_experience"])
        for evidence in f["research_practice"].values():
            check(evidence["source_id"] in emap and evidence["observation"] in text,pid+": unlinked or omitted supporting evidence")
        for key in ("rubric_hash","designated_mixed_pattern","latent_academic_level","Provisional study tier","not an established novelty claim","no results or partnerships claimed","not yet specified","not yet selected"):
            check(key not in text,pid+": researcher metadata or missing-detail marker leaked")
        check("ACADEMIC INTEGRITY RECORD" not in text,pid+": unsolicited integrity treatment")
        check(not re.search(r"\b(strong applicant|weak applicant|borderline applicant)\b",text,re.I),pid+": merit label leaked")
        packet = next((p for p in inputs if p["profile_id"] == pid),None)
        check(packet is not None and packet["condition"] is None and text.strip() in packet["messages"][1]["content"],pid+": evaluator input differs")
        if row["strength"] == "strong":
            check(all(points[c["grade"]] >= 2.7 for c in f["coursework"] if c["level"] == "graduate"),pid+": strong tier despite poor recent grades")
    mixed = Counter(r["designated_mixed_pattern"] for r in rows if r["designated_mixed_pattern"] != "none")
    check(dict(mixed) == {cell["pattern"]:cell["count"] for cell in config["mixed_allocation"]},"Mixed allocation differs")
    unique = {field:len({json.dumps(r["facts"][field]["components"],sort_keys=True) for r in rows}) for field in ("proposed_research","broader_impacts_plan")}
    check(all(n == len(rows) for n in unique.values()),"Repeated complete proposal or impact bundle")
    stats = {tier:{"min":min(v),"max":max(v),"mean":round(sum(v)/len(v),1)} for tier,v in lengths.items() if v}
    means = [sum(v)/len(v) for v in estimates.values() if v]
    ratio = max(v["mean"] for v in stats.values())/min(v["mean"] for v in stats.values())
    check(max(means)/min(means) <= config["maximum_estimated_tier_mean_ratio"],"Pre-generation length balance differs")
    check(ratio <= config["maximum_estimated_tier_mean_ratio"]+.04,"Rendered tier means exceed wording tolerance")
    return {"applicants":len(rows),"tiers":dict(Counter(r["strength"] for r in rows)),"designated_mixed":dict(mixed),"errors":errors,"word_counts_by_tier":stats,"largest_to_smallest_tier_mean_ratio":round(ratio,4),"unique_proposals":unique["proposed_research"],"unique_impact_plans":unique["broader_impacts_plan"],"ra_in_proposal_area":ra_continuity,"evidence_sensitivity":sensitivity(rows),"sensitivity_interpretation":"Evidence ablations test the rubric, not new valid applicant packets. Removing appointments also removes their outputs; proposal design and all other evidence remain fixed. These diagnostics share the rubric function; structural and rendering checks above are separately implemented.","limitations":["Provisional rubric and distributions; no empirical fellowship calibration.","Complete designs vary in methodological quality, but novelty and scientific value remain unvalidated.","Full bundles are unique; shared sentence templates, generic institutions and eight topic families constrain diversity.","Tier mean lengths are controlled before wording, not exact individual length matching or proof against length effects.","Separate-context factual review by the same model is not independent human validation."],"api_calls":0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--out",required=True)
    result = audit(parser.parse_args().out); print(json.dumps(result,indent=2)); raise SystemExit(bool(result["errors"]))
