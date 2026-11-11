"""Constraint and end-to-end tests for fixed-template letters, with no API."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phd_resumes.io import digest, read_json, read_jsonl, write_json, write_jsonl
from phd_resumes.sampling import generate_cohort
from phd_resumes.writing import render_cv
from phd_recommendations.pipeline import build_record, check_policy, generate, load_applicants, render_letters, tree_hash, validate_record, verify
from test_pipeline import config, fixture_content

ROOT = Path(__file__).resolve().parents[1]


def policy():
    return read_json(ROOT / "configs/phd_recommendations_v1.json")


def applicant(months=1, research=True):
    row = generate_cohort(config(), 123)[1][0]
    facts = copy.deepcopy(row["facts"])
    facts["research_experience"] = [{"id": "R1", "role": "Research assistant", "organization": "University Research Group", "start": f"2026-{11-months:02d}", "end": "2026-11", "months": months, "hours_per_week": 10, "contribution": "assigned implementation tasks"}] if research else []
    facts["projects"] = [{"id": "T1", "kind": "technical course project", "scope": "baseline implementation", "year": 2026}]
    facts["publications"] = []
    content = fixture_content(facts)
    return {"facts": facts, "content": content, "cv": render_cv(facts, content)}


def source_run(path, count=6):
    rows = generate_cohort(config(), 123)[1][:count]
    manifest = []
    for row in rows:
        pid = row["profile_id"]
        content = fixture_content(row["facts"])
        cv = render_cv(row["facts"], content)
        write_json(path / "generation" / f"{pid}.content.json", content)
        write_json(path / "generation" / f"{pid}.status.json", {"status": "ready_for_human_review", "facts_hash": row["facts_hash"], "issues": [], "review": {"passes": True, "issues": []}})
        (path / "resumes").mkdir(exist_ok=True)
        (path / "resumes" / f"{pid}.txt").write_text(cv)
        manifest.append({"profile_id": pid, "facts_hash": row["facts_hash"], "cv_hash": digest(cv), "content_source": f"generation/{pid}.content.json", "resume": f"resumes/{pid}.txt"})
    write_jsonl(path / "profiles.jsonl", rows)
    write_json(path / "resume_manifest.json", manifest)


class RecommendationTests(unittest.TestCase):
    def test_short_research_is_scoped_and_never_gets_exceptional_praise(self):
        a, p = applicant(), policy()
        for seed in range(40):
            p["seed"] = seed
            record = build_record(a, p)
            letter = next(l for l in record["letters"] if l["writer_type"] == "research supervisor")
            self.assertEqual(letter["relationship"]["months"], 1)
            self.assertIn("(1 month)", letter["summary"])
            self.assertNotEqual(letter["strength_level"], "strong")
            self.assertNotIn("best", letter["summary"])
            self.assertEqual(len(record["letters"]), 3)
            validate_record(a, record, p)

    def test_no_research_does_not_invent_supervision(self):
        a, p = applicant(research=False), policy()
        record = build_record(a, p)
        self.assertNotIn("research supervisor", [l["writer_type"] for l in record["letters"]])
        self.assertEqual(len({l["writer_id"] for l in record["letters"]}), 3)
        for l in record["letters"]:
            if l["relationship"]["source_section"] in {"coursework", "projects"}:
                self.assertIsNone(l["relationship"]["months"])
        validate_record(a, record, p)

    def test_four_flag_combinations_and_exact_examples(self):
        a = applicant()
        for compares in (False, True):
            for example in (False, True):
                p = policy()
                p.update(comparison_probability=int(compares), example_probability_when_available=int(example))
                record = build_record(a, p)
                for l in record["letters"]:
                    self.assertEqual(l["compares_with_other_students"], compares)
                    available = l["relationship"]["source_section"] != "coursework"
                    self.assertEqual(l["gives_specific_example"], example and available)
                    self.assertEqual("Compared with other students" in l["summary"], compares)
                    self.assertEqual("As a specific example" in l["summary"], example and available)
                    if l["example"]:
                        e = l["example"]
                        original = next(x for x in a["content"][e["section"]] if x["id"] == e["source_id"])
                        self.assertEqual(e["text"], original["bullets"][e["bullet_index"]])
                validate_record(a, record, p)

    def test_flags_do_not_change_strengths_and_tiers_do_not_enter_generation(self):
        a, p = applicant(6), policy()
        first = build_record(a, p)
        a.update(strength="weak", rubric={"tier": "weak"}, latent_research_level=1)
        self.assertEqual(first, build_record(a, p))
        a.update(strength="strong", rubric={"tier": "strong"}, latent_research_level=5)
        self.assertEqual(first, build_record(a, p))
        p.update(comparison_probability=1, example_probability_when_available=1)
        self.assertEqual([l["strength_level"] for l in first["letters"]], [l["strength_level"] for l in build_record(a, p)["letters"]])

    def test_rejects_duration_flags_wrong_writer_example_and_unapproved_praise(self):
        a, p = applicant(), policy()
        p.update(comparison_probability=1, example_probability_when_available=1)
        original = build_record(a, p)
        for change in ("duration", "comparison", "example", "praise", "duplicate_writer", "boolean"):
            record = copy.deepcopy(original)
            letter = record["letters"][0]
            if change == "duration": letter["relationship"]["months"] = 24
            if change == "comparison": letter["compares_with_other_students"] = False
            if change == "example": letter["example"] = next(l["example"] for l in record["letters"] if l["relationship"]["source_section"] == "projects")
            if change == "praise": letter["summary"] += " The applicant is the best student ever."
            if change == "duplicate_writer": record["letters"][1]["writer_id"] = letter["writer_id"]
            if change == "boolean": letter["gives_specific_example"] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_record(a, record, p)

    def test_course_project_never_claims_named_course_or_grade(self):
        record = build_record(applicant(), policy())
        project = next(l for l in record["letters"] if l["relationship"]["source_section"] == "projects")
        self.assertEqual(project["relationship"]["year"], 2026)
        self.assertNotIn("Machine Learning", project["summary"])
        self.assertNotIn("grade", project["summary"])

    def test_invalid_probability_or_short_research_override_fails(self):
        for key, value in (("comparison_probability", -0.1), ("example_probability_when_available", float('nan')), ("letters_per_applicant", 4)):
            p = policy(); p[key] = value
            with self.assertRaises(ValueError): check_policy(p)
        p = policy(); p["strength_probabilities"]["research_short"] = [0, 0, 1]
        with self.assertRaises(ValueError): check_policy(p)

    def test_end_to_end_immutable_source_repeatability_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out, repeat = (Path(tmp) / name for name in ("source", "out", "repeat"))
            source_run(source)
            before = tree_hash(source)
            with patch("phd_resumes.api.OpenAIResponses.create", side_effect=AssertionError("No model calls allowed")):
                result = generate(source, out, policy())
                generate(source, repeat, policy())
            self.assertEqual(result["applicants"], 6)
            self.assertEqual(result["letters"], 18)
            self.assertEqual(result["api_calls"], 0)
            self.assertEqual(before, tree_hash(source))
            self.assertEqual((out / "recommendations.jsonl").read_bytes(), (repeat / "recommendations.jsonl").read_bytes())
            for row in read_json(out / "manifest.json"):
                pid = row["applicant_id"]
                cv = (source / "resumes" / f"{pid}.txt").read_text()
                self.assertEqual(cv, (out / "resumes" / f"{pid}.txt").read_text())
                self.assertTrue((out / "applications" / f"{pid}.txt").read_text().startswith(cv + "\nApplicant"))
            with self.assertRaises(ValueError): generate(source, out, policy())
            with self.assertRaises(ValueError): generate(source, source / "nested", policy())
            exported = next((out / "applications").glob("*.txt"))
            exported.write_text(exported.read_text() + "Altered")
            with self.assertRaises(ValueError): verify(out, source)

    def test_rejects_unaccepted_sources_bad_hashes_and_traversal_before_export(self):
        for failure in ("rejected", "hash", "path", "identity"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                source, out = Path(tmp) / "source", Path(tmp) / "out"
                source_run(source)
                manifest = read_json(source / "resume_manifest.json")
                if failure == "rejected":
                    path = next((source / "generation").glob("*.status.json"))
                    status = read_json(path); status["review"]["passes"] = False; write_json(path, status)
                if failure == "hash": manifest[0]["cv_hash"] = "changed"
                if failure == "path": manifest[0]["content_source"] = "../outside.json"
                if failure == "identity": manifest.append(manifest[0])
                write_json(source / "resume_manifest.json", manifest)
                with self.assertRaises(ValueError): generate(source, out, policy())
                self.assertFalse(out.exists())

    def test_pilot_subset_uses_same_letters_as_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source_run(source)
            applicants = load_applicants(source)
            pid = applicants[-1]["facts"]["applicant_id"]
            out = Path(tmp) / "pilot"
            generate(source, out, policy(), [pid])
            self.assertEqual(read_jsonl(out / "recommendations.jsonl"), [build_record(applicants[-1], policy())])
            self.assertEqual(render_letters(read_jsonl(out / "recommendations.jsonl")[0]).count("Strength level:"), 3)


if __name__ == "__main__":
    unittest.main()
