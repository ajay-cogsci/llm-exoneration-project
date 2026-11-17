"""Read-only substantive audit from exported facts and text, without the sampler."""

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def month(value):
    year,number=map(int,value.split("-"))
    assert 1 <= number <= 12
    return year*12+number-1


def metrics(root):
    rows=read_rows(root/"profiles.jsonl")
    facts=[r["facts"] for r in rows]
    groups={}
    for prior in (False,True):
        group=[f for f in facts if bool(f["teaching_experience"])==prior]
        bad=sum(any(e["rating"]=="needs_improvement" for e in f["communication_evidence"].values()) for f in group)
        groups["experienced" if prior else "first_time"]={"n":len(group),"communication_concerns":bad,"fraction":round(bad/len(group),4) if group else None}
    anchors={"Introduction to Programming","Data Structures","Discrete Mathematics"}
    return {
        "applicants":len(rows),
        "tiers":dict(Counter(r["strength"] for r in rows)),
        "strong_first_time":sum(r["strength"]=="strong" and not r["facts"]["teaching_experience"] for r in rows),
        "communication_by_experience":groups,
        "unavailable":sum(not all(f["availability"].values()) for f in facts),
        "education_histories":len({json.dumps(f["education"],sort_keys=True) for f in facts}),
        "anchor_grade_patterns":len({tuple(sorted((c["course"],c["grade"]) for c in f["coursework"] if c["course"] in anchors and c.get("level","undergraduate")=="undergraduate")) for f in facts}),
        "skill_sets":len({tuple(sorted(f["technical_skills"])) for f in facts}),
        "project_counts":dict(Counter(str(len(f["projects"])) for f in facts)),
        "project_task_sets":len({tuple(sorted(p["tasks"])) for f in facts for p in f["projects"]}),
        "application_words_by_tier":{tier:{"min":min(lengths),"max":max(lengths),"mean":round(statistics.mean(lengths),1)} for tier in ("weak","borderline","strong") if (lengths:=[len((root/"applications"/f"{r['profile_id']}.txt").read_text().split()) for r in rows if r["strength"]==tier])},
    }


def audit(root, previous):
    root,previous=Path(root),Path(previous)
    rows=read_rows(root/"profiles.jsonl")
    config=json.loads((root/"config.json").read_text())
    assert len(rows)==100 and len({r["profile_id"] for r in rows})==100
    assert Counter(r["strength"] for r in rows)=={"weak":30,"borderline":40,"strong":30}
    assert sum(r["designated_mixed_pattern"]!="none" for r in rows)==10
    assert len(list((root/"applications").glob("*.txt")))==100
    assert all(all(r["facts"]["availability"].values()) for r in rows)
    assert all(r["facts"]["education"][-1]["degree"] in {"MS in Computer Science","PhD in Computer Science"} for r in rows)
    texts={}
    for row in rows:
        f=row["facts"];pid=row["profile_id"]
        text=(root/"applications"/f"{pid}.txt").read_text()
        texts[pid]=text
        assert f["education"][-1]["start"] <= f["review_month"] < f["education"][-1]["end"]
        assert f"{f['undergraduate_gpa']:.2f}/{f['gpa_scale']:.1f}" in text
        assert f["teaching_interest"]["statement"] in text
        for course in f["coursework"]:
            assert f"{course['course']}: {course['grade']} | {course['level']}, {course['date']}" in text
        for e in f["teaching_experience"]:
            assert month(e["end"])-month(e["start"])==e["months"]>0
            assert e["end"]<=f["record_as_of"][:7]
            assert any(d["start"] <= e["start"] < e["end"] <= d["end"] for d in f["education"])
            assert e["role"] in text and e["performance_note"] in text
            assert f"{e['start']} to {e['end']} | {e['months']} months; {e['hours_per_week']} hours/week" in text
        if not f["teaching_experience"]:
            assert "No previous teaching, tutoring, or TA experience reported." in text
            assert "Not applicable: no previous teaching, tutoring, or TA appointment reported." in text
        for evidence in f["communication_evidence"].values():
            assert evidence["source_project_id"] in {p["id"] for p in f["projects"]}
            assert evidence["observation"] in text
        if row["strength"]=="strong":
            assert f["teaching_interest"]["category"]=="beginner_support"
            assert all(e["rating"]!="needs_improvement" for e in f["communication_evidence"].values())
            assert all(e["performance"]!="needs_improvement" for e in f["teaching_experience"])
        assert all(s not in text for s in ("designated_mixed_pattern","latent_academic_level","Provisional study tier:","RECOMMENDATION LETTER"))
    messages=read_rows(root/"evaluator_inputs.jsonl")
    assert len(messages)==100 and {m["profile_id"] for m in messages}==set(texts)
    for record in messages:
        assert record["condition"] is None
        assert record["messages"][0]["content"]==(root/"prompts/system_resolved.txt").read_text().strip()
        assert texts[record["profile_id"]].strip() in record["messages"][1]["content"]
    for filename in ("system_template.txt","system_resolved.txt","opportunity.txt"):
        assert (root/"prompts"/filename).read_bytes()==(previous/"prompts"/filename).read_bytes()
    corpus=metrics(root)
    assert corpus["strong_first_time"]>=3 and corpus["education_histories"]>2 and corpus["anchor_grade_patterns"]>5 and corpus["skill_sets"]>1 and corpus["project_task_sets"]>1
    return {"status":"record_and_text_checks_passed","api_calls":0,"current":corpus,"previous":metrics(previous),"fixed_facts_present_in_text":True,"plan_prompt_files_unchanged":True,"designated_mixed_profiles":10,"independent_human_validation":False,"interpretation":"Checks address the identified construction problems. Descriptive differences and consistency do not establish empirical hiring validity. No population targets were fitted."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",default="datasets/ta-applicants-v2")
    parser.add_argument("--previous",default="datasets/ta-applicants-v1")
    parser.add_argument("--report")
    args=parser.parse_args()
    result=audit(args.dataset,args.previous)
    if args.report:
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
