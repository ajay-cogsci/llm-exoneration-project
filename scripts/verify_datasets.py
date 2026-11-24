"""Verify the published PhD inputs in data/phd/ without network or model calls.

Checks the CVs (data/phd/cvs) and the application packets built from them
(data/phd/applications):
- every file matches its checksums.json entry and no file is missing or extra;
- every CV's tier recomputes from its facts under the saved rubric;
- every applicant's three recommendation records pass validation, and each
  packet equals that applicant's CV followed by the rendered letters, with the
  hashes in manifest.json.

The fellowship, TA and RA banks have their own commands:
    python3 -m fellowship_applicants verify --out data/fellowship
    python3 -m ta_applicants verify --out data/ta
    python3 -m ra_applicants verify --out data/ra

To re-derive these PhD files from the older dataset versions they were
corrected from, run old/scripts/verify_phd_history.py.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from phd_recommendations.pipeline import load_applicants, render_letters, validate_record
from phd_resumes.io import PROJECT, digest, read_json, read_jsonl
from phd_resumes.rubric import evaluate


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_files(root):
    manifest = read_json(root / "checksums.json")
    paths = {str(p.relative_to(root)): p for p in root.rglob("*")
             if p.is_file() and p.name != "checksums.json" and "__pycache__" not in p.parts}
    require(set(paths) == set(manifest), f"Unexpected or missing files in {root}")
    for name, path in paths.items():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest[name], f"Checksum mismatch: {root.name}/{name}")
    return len(paths)


def verify(phd):
    cvs, packets = Path(phd) / "cvs", Path(phd) / "applications"
    files = check_files(cvs) + check_files(packets)
    profiles = read_jsonl(cvs / "profiles.jsonl")
    rubric = read_json(cvs / "rubric.json")
    require(len(profiles) == 100, "Expected 100 CVs")
    for row in profiles:
        rating = evaluate(row["facts"], rubric)
        require(rating == row["rubric"] and rating["tier"] == row["strength"], f"Tier does not recompute: {row['profile_id']}")
    applicants = {a["facts"]["applicant_id"]: a for a in load_applicants(cvs)}
    records = read_jsonl(packets / "recommendations.jsonl")
    policy = read_json(packets / "policy.json")
    manifest = read_json(packets / "manifest.json")
    require(len(records) == len(manifest) == len(applicants) == 100, "Expected 100 packets")
    require([m["applicant_id"] for m in manifest] == [r["applicant_id"] for r in records], "Manifest order differs")
    for record, item in zip(records, manifest):
        pid = record["applicant_id"]
        applicant = applicants[pid]
        validate_record(applicant, record, policy)
        letters = render_letters(record)
        packet = applicant["cv"] + "\n" + letters
        for folder, text in (("resumes", applicant["cv"]), ("recommendations", letters), ("applications", packet)):
            require((packets / folder / f"{pid}.txt").read_text() == text, f"Content mismatch: {folder}/{pid}")
        require(item == {"applicant_id": pid, "facts_hash": digest(applicant["facts"]), "cv_hash": digest(applicant["cv"]),
                         "recommendations_hash": digest(letters), "application_hash": digest(packet)},
                f"Packet hashes differ: {pid}")
    tiers = {t: sum(r["strength"] == t for r in profiles) for t in ("weak", "borderline", "strong")}
    return {"files_checked": files, "cvs": len(profiles), "packets": len(manifest), "recommendations": 3 * len(records),
            "tiers": tiers, "tiers_recompute": True, "packets_rebuild_from_cvs_and_letters": True, "api_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phd", default=str(PROJECT / "data/phd"))
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.phd), indent=2))
    except (ValueError, KeyError, OSError) as error:
        sys.exit(str(error))
