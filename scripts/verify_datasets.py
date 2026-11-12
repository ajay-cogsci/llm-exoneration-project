"""Verify the published PhD datasets without network or model calls."""

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from phd_resumes.io import digest, read_json, read_jsonl
from phd_resumes.rubric import evaluate
from phd_resumes.rubric_pipeline import make_pool, select_allocated
from phd_recommendations.pipeline import load_applicants, render_letters, validate_record
from phd_revisions.export import CVS, PACKETS, SOURCE_CVS, SOURCE_PACKETS, build
from phd_revisions.gpa_consistency import is_consistent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_files(root):
    manifest = read_json(root / "checksums.json")
    paths = {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file() and p.name != "checksums.json" and "__pycache__" not in p.parts}
    require(set(paths) == set(manifest), f"Unexpected/missing files in {root.name}")
    for name, path in paths.items():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest[name], f"Checksum mismatch: {name}")


def verify(root):
    root = Path(root)
    cvs = root / "phd-cvs-v2-rubric-v1"
    packets = root / "phd-applications-v3-recommendations-v1"
    check_files(cvs)
    check_files(packets)
    applicants = load_applicants(cvs)
    profiles = read_jsonl(cvs / "profiles.jsonl")
    require(len(profiles) == len(applicants) == 100, "Expected 100 applicants")
    by_id = {a["facts"]["applicant_id"]: a for a in applicants}
    require(read_jsonl(cvs / "evaluator_fields.jsonl") == [r["facts"] for r in profiles], "Evaluator fields differ")
    rubric = read_json(cvs / "rubric.json")
    for row in profiles:
        rating = evaluate(row["facts"], rubric)
        require(rating == row["rubric"] and rating["tier"] == row["strength"], "CV rubric mismatch")
    config = read_json(cvs / "config.json")
    sampling = read_json(cvs / "sampling_policy.json")
    pool = [row for seed in config["seeds"] for row in make_pool(config, rubric, sampling, seed)]
    selected = select_allocated(pool, rubric, sampling["allocation"])
    require(selected == profiles, "Published sample does not reproduce from settings")
    records = read_jsonl(packets / "recommendations.jsonl")
    require(len(records) == 100 and {r["applicant_id"] for r in records} == set(by_id), "Recommendation identity mismatch")
    inputs = read_jsonl(packets / "inputs" / "applicants.jsonl")
    require(inputs == applicants, "Recommendation inputs differ from published CVs")
    policy = read_json(packets / "policy.json")
    manifest = read_json(packets / "manifest.json")
    require(len(manifest) == 100 and [m["applicant_id"] for m in manifest] == [r["applicant_id"] for r in records], "Packet manifest identity mismatch")
    for record, item in zip(records, manifest):
        pid = record["applicant_id"]
        applicant = by_id[pid]
        validate_record(applicant, record, policy)
        letters = render_letters(record)
        packet = applicant["cv"] + "\n" + letters
        for folder, text in (("resumes", applicant["cv"]), ("recommendations", letters), ("applications", packet)):
            require((packets / folder / f"{pid}.txt").read_text() == text, f"Content mismatch: {folder}/{pid}")
        require(item == {"applicant_id": pid, "facts_hash": digest(applicant["facts"]), "cv_hash": digest(applicant["cv"]), "recommendations_hash": digest(letters), "application_hash": digest(packet)}, "Packet hashes differ")
    result = {"cv_count": 100, "recommendation_count": 300, "application_count": 100, "checksums_verified": True, "pool_size_reproduced": len(pool), "sample_reproduced": True, "rubric_reproduced": True, "recommendations_reproduced": True, "api_calls": 0}
    result["corrected_datasets"] = verify_corrected(root)
    return result


def verify_corrected(root):
    """Rebuild the corrected datasets from the published ones and their saved
    policies, then require every file to match the committed copy."""
    cvs, packets = root / CVS, root / PACKETS
    check_files(cvs)
    check_files(packets)
    gpa_policy, policy = read_json(cvs / "gpa_consistency_policy.json"), read_json(packets / "policy.json")
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        for name in (SOURCE_CVS, SOURCE_PACKETS):
            shutil.copytree(root / name, scratch / name)
        build(scratch, gpa_policy, policy)
        for name in (CVS, PACKETS):
            rebuilt = {str(p.relative_to(scratch / name)): p.read_bytes() for p in (scratch / name).rglob("*") if p.is_file()}
            saved = {str(p.relative_to(root / name)): p.read_bytes() for p in (root / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
            require(rebuilt == saved, f"{name} does not rebuild from its sources and policy")
    profiles = read_jsonl(cvs / "profiles.jsonl")
    rubric = read_json(cvs / "rubric.json")
    originals = {row["profile_id"]: row for row in read_jsonl(root / SOURCE_CVS / "profiles.jsonl")}
    changed = 0
    for row in profiles:
        require(is_consistent(row["facts"], gpa_policy), f"GPA still contradicts coursework: {row['profile_id']}")
        rating = evaluate(row["facts"], rubric)
        require(rating == row["rubric"] and rating["tier"] == row["strength"], "Corrected CV rubric mismatch")
        before = originals[row["profile_id"]]
        if row != before:
            changed += 1
            masked = {**row["facts"], "gpa": before["facts"]["gpa"]}
            require(masked == before["facts"], f"A field other than GPA changed: {row['profile_id']}")
    applicants = {a["facts"]["applicant_id"]: a for a in load_applicants(cvs)}
    records = read_jsonl(packets / "recommendations.jsonl")
    require(len(records) == len(applicants) == 100, "Expected 100 corrected applicants")
    for record in records:
        validate_record(applicants[record["applicant_id"]], record, policy)
    return {"cv_dataset": CVS, "packet_dataset": PACKETS, "rebuilt_identically": True, "gpa_values_changed": changed, "only_gpa_changed": True, "all_gpas_consistent": True, "recommendations_reproduced": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default=str(PROJECT / "datasets"))
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.datasets), indent=2))
    except (ValueError, KeyError, OSError) as error:
        sys.exit(str(error))
