"""Behavioral and integration checks; model transport is always simulated."""

import copy
import csv
import json
import random
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from phd_resumes.io import digest, read_json, read_jsonl, write_json
from phd_resumes.pipeline import generate_run
from phd_resumes.rubric import check_rubric, evaluate
from phd_resumes.rubric_pipeline import audit_existing, check_sampling, inspect_revision, make_pool, sample_revision, select_allocated, tree_hash
from phd_resumes.sampling import make_profile, validate_profile
from phd_resumes.writing import render_cv
from test_pipeline import FakeAPI, config

ROOT = Path(__file__).resolve().parents[1]


def policies():
    return read_json(ROOT / "configs/phd_rubric_v1.json"), read_json(ROOT / "configs/phd_sampling_v3.json")


def facts(academic=4, research=4, gpa=3.7, months=24):
    cfg = config()
    cfg["research_month_ranges_by_preparation"] = [[months, months]] * 5
    cfg["internship_count_ranges_by_preparation"] = [[0, 0]] * 5
    cfg["publication_probability_per_six_months"] = [0] * 5
    row = make_profile(cfg, random.Random(42), 42, 1, research, gpa)
    row["facts"]["coursework"] = copy.deepcopy(cfg["coursework_by_preparation"][academic-1])
    return row["facts"]


def allocation():
    # Test-only counts, not the user's future experimental allocation.
    return {"seed": 891, "cells": [
        {"tier": "weak", "pattern": "none", "count": 4},
        {"tier": "borderline", "pattern": "none", "count": 6},
        {"tier": "strong", "pattern": "none", "count": 4},
        {"tier": "strong", "pattern": "lower_gpa_strong_research", "count": 2},
        {"tier": "borderline", "pattern": "high_academics_limited_research", "count": 2},
    ]}


class RubricTests(unittest.TestCase):
    def setUp(self):
        self.rubric, self.sampling = policies()

    def test_publication_is_neither_necessary_nor_sufficient(self):
        strong = facts()
        self.assertEqual(evaluate(strong, self.rubric)["tier"], "strong")
        strong["publications"] = [{"venue": "A prestigious venue"}] * 10
        self.assertEqual(evaluate(strong, self.rubric)["tier"], "strong")
        weak = facts(academic=1, research=1, gpa=3.1, months=3)
        weak["publications"] = strong["publications"]
        self.assertEqual(evaluate(weak, self.rubric)["tier"], "weak")

    def test_duration_alone_does_not_establish_intellectual_contribution(self):
        result = evaluate(facts(research=1), self.rubric)
        self.assertEqual(result["research"], "adequate")
        self.assertEqual(result["tier"], "borderline")

    def test_hours_matter_and_calendar_months_are_not_full_time_months(self):
        f = facts()
        result = evaluate(f, self.rubric)
        self.assertEqual(result["evidence"]["research_fte_months"], 6)
        f["research_experience"][0]["hours_per_week"] = 2
        self.assertEqual(evaluate(f, self.rubric)["research"], "low")

    def test_short_intellectual_role_does_not_upgrade_entire_history(self):
        f = facts()
        e = f["research_experience"][0]
        e.update(end="2026-08", months=21, contribution="assigned implementation tasks")
        f["research_experience"].append({**e, "id": "R2", "start": "2026-08", "end": "2026-11", "months": 3, "contribution": "designed experiments and analyzed results"})
        self.assertEqual(evaluate(f, self.rubric)["research"], "adequate")

    def test_compensation_and_conflicting_evidence_are_explicit(self):
        lower = evaluate(facts(gpa=3.2), self.rubric)
        self.assertEqual((lower["academic"], lower["tier"]), ("adequate", "strong"))
        self.assertIn("lower_gpa_strong_research", lower["mixed_tags"])
        gaps = evaluate(facts(academic=1), self.rubric)
        self.assertEqual((gaps["academic"], gaps["tier"]), ("low", "borderline"))
        high_grades = evaluate(facts(research=1, months=3), self.rubric)
        self.assertEqual(high_grades["tier"], "borderline")
        self.assertIn("high_academics_limited_research", high_grades["mixed_tags"])

    def test_missing_unknown_or_invalid_evidence_is_unrated_not_weak(self):
        variants = []
        for field in ("coursework", "research_experience", "publications", "gpa"):
            f = facts()
            del f[field]
            variants.append(f)
        for field, value in (("contribution", "unmapped claim"), ("contribution", []), ("hours_per_week", -1), ("months", 999), ("start", "invalid")):
            f = facts()
            f["research_experience"][0][field] = value
            variants.append(f)
        f = facts()
        f["research_experience"] *= 2
        variants.append(f)
        f = facts()
        f["coursework"][0]["grade"] = []
        variants.append(f)
        f = facts()
        f["review_month"] = "invalid"
        variants.append(f)
        for f in variants:
            with self.subTest(f=f):
                result = evaluate(f, self.rubric)
                self.assertEqual(result["tier"], "unrated")
                self.assertTrue(result["issues"])

    def test_improving_gpa_never_reduces_tier(self):
        order = {"weak": 0, "borderline": 1, "strong": 2}
        for academic in range(1, 6):
            for research in range(1, 6):
                scores = [order[evaluate(facts(academic, research, gpa), self.rubric)["tier"]] for gpa in (2.8, 2.99, 3.0, 3.39, 3.4, 3.49, 3.5, 4.0)]
                self.assertEqual(scores, sorted(scores))

    def test_unrelated_metadata_and_cohort_members_do_not_change_rating(self):
        f = facts()
        before = evaluate(f, self.rubric)
        for _ in range(3):
            evaluate(facts(1, 1, 2.8, 3), self.rubric)
        after = evaluate(f, self.rubric)
        self.assertEqual(before, after)
        self.assertNotIn("latent", json.dumps(before))
        self.assertEqual(f, facts())
        before["not_assessed"].clear()
        self.assertTrue(evaluate(f, self.rubric)["not_assessed"])

    def test_policy_rejects_nonmonotonic_rules_and_invalid_thresholds(self):
        bad = copy.deepcopy(self.rubric)
        bad["tier_table"]["high"]["high"] = "weak"
        with self.assertRaises(ValueError):
            check_rubric(bad)
        for value in (True, -1, float("nan"), float("inf")):
            bad = copy.deepcopy(self.rubric)
            bad["research"]["high_fte_months_min"] = value
            with self.assertRaises(ValueError):
                check_rubric(bad)


class RevisedSamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = config()
        cls.rubric, cls.sampling = policies()
        cls.sampling["pool_per_cohort"] = 1000
        cls.pool = make_pool(cls.cfg, cls.rubric, cls.sampling, 123)

    def test_reproducible_independent_levels_and_valid_fixed_facts(self):
        self.assertEqual(self.pool, make_pool(self.cfg, self.rubric, self.sampling, 123))
        self.assertEqual(len({(r["latent_academic_level"], r["latent_research_level"]) for r in self.pool}), 25)
        self.assertTrue(any(r["rubric"]["academic"] == "high" and r["rubric"]["research"] == "low" for r in self.pool))
        for row in self.pool:
            self.assertEqual(validate_profile(row), [])
            self.assertTrue(row["profile_id"].startswith("PHDv3-"))
            for key in ("rubric", "strength", "legacy_diagnostic", "latent_academic_level", "latent_research_level", "mixed_tags"):
                self.assertNotIn(key, row["facts"])
                self.assertNotIn(key, render_cv(row["facts"]))

    def test_academic_draw_changes_do_not_change_research_history(self):
        alternate = copy.deepcopy(self.sampling)
        alternate["academic_given_research_probabilities"] = [[1, 0, 0, 0, 0]] * 5
        other = make_pool(self.cfg, self.rubric, alternate, 123)
        self.assertEqual([r["facts"]["research_experience"] for r in self.pool], [r["facts"]["research_experience"] for r in other])
        self.assertNotEqual([r["facts"]["coursework"] for r in self.pool], [r["facts"]["coursework"] for r in other])

    def test_exact_counts_without_relabeling_or_duplicate_records(self):
        before = digest(self.pool)
        chosen = select_allocated(self.pool, self.rubric, allocation())
        self.assertEqual(chosen, select_allocated(list(reversed(self.pool)), self.rubric, allocation()))
        actual = Counter((r["strength"], r["rubric"]["selection_pattern"]) for r in chosen)
        self.assertEqual(actual, {(c["tier"], c["pattern"]): c["count"] for c in allocation()["cells"]})
        self.assertEqual(len({r["profile_id"] for r in chosen}), 18)
        self.assertEqual(digest(self.pool), before)

    def test_shortage_and_tampering_fail_without_relabeling(self):
        excessive = allocation()
        excessive["cells"][0]["count"] = 99999
        with self.assertRaisesRegex(ValueError, "Insufficient pool support"):
            select_allocated(self.pool, self.rubric, excessive)
        altered = copy.deepcopy(self.pool)
        altered[0]["strength"] = "invented"
        with self.assertRaisesRegex(ValueError, "metadata changed"):
            select_allocated(altered, self.rubric, allocation())

    def test_unset_allocation_cannot_create_a_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "must-not-exist"
            with self.assertRaisesRegex(ValueError, "Allocation is unset"):
                sample_revision(self.cfg, self.rubric, self.sampling, out)
            self.assertFalse(out.exists())

    def test_invalid_allocation_and_matrices_rejected(self):
        for value in (-1, 1.5, True):
            bad = copy.deepcopy(self.sampling)
            bad["allocation"] = allocation()
            bad["allocation"]["cells"][0]["count"] = value
            with self.assertRaises(ValueError):
                check_sampling(bad, self.cfg)
        bad = copy.deepcopy(self.sampling)
        bad["academic_given_research_probabilities"][0][0] = 0.8
        with self.assertRaises(ValueError):
            check_sampling(bad, self.cfg)
        duplicate = allocation()
        duplicate["cells"].append(duplicate["cells"][0])
        with self.assertRaises(ValueError):
            select_allocated(self.pool, self.rubric, duplicate)

    def test_inspect_is_read_only_and_cannot_call_a_model(self):
        with patch("phd_resumes.rubric_pipeline.make_pool") as sampler, patch("phd_resumes.api.OpenAIResponses.create") as api:
            result = inspect_revision(self.cfg, self.rubric, self.sampling)
        sampler.assert_not_called()
        api.assert_not_called()
        self.assertIsNone(result["allocation"])

    def test_existing_writer_accepts_new_sample_cache_and_rejects_policy_drift(self):
        cfg, policy = copy.deepcopy(self.cfg), copy.deepcopy(self.sampling)
        cfg["seeds"] = [123]
        policy["allocation"] = allocation()
        class CapturingAPI(FakeAPI):
            def create(self, body):
                data = json.loads(body["input"][1]["content"])
                fixed = data.get("fixed_record", data)
                assert not {"strength", "rubric", "mixed_tags", "legacy_diagnostic"}.intersection(fixed)
                return super().create(body)
        with tempfile.TemporaryDirectory() as tmp:
            sample_revision(cfg, self.rubric, policy, tmp)
            api = CapturingAPI()
            generate_run(tmp, api, "test-only-model", "test-only-model", 3)
            self.assertEqual(api.calls, 6)
            generate_run(tmp, api, "test-only-model", "test-only-model", 3)
            self.assertEqual(api.calls, 6)
            changed = copy.deepcopy(self.rubric)
            changed["academic"]["high_gpa_min"] = 3.6
            write_json(Path(tmp) / "rubric.json", changed)
            with self.assertRaisesRegex(ValueError, "policy has changed"):
                generate_run(tmp, api, "test-only-model", "test-only-model", 3)
            self.assertEqual(api.calls, 6)

    def test_historical_audit_preserves_source_and_blinds_existing_cvs(self):
        source = ROOT / "sample-100-resume-generated"
        before = tree_hash(source)
        cfg, policy = copy.deepcopy(self.cfg), copy.deepcopy(self.sampling)
        cfg["seeds"] = [123]
        policy["pool_per_cohort"] = 100
        with tempfile.TemporaryDirectory() as tmp, patch("phd_resumes.api.OpenAIResponses.create") as api:
            report = audit_existing(source, tmp, cfg, self.rubric, policy)
            api.assert_not_called()
            self.assertEqual(report["cv_content_reuse_verified"], 100)
            self.assertEqual(len(read_jsonl(Path(tmp) / "proposed_labels.jsonl")), 150)
            review = Path(tmp) / "blind_review"
            self.assertEqual(len(list(review.glob("REVIEW-*.txt"))), 100)
            for path in review.glob("REVIEW-*.txt"):
                self.assertNotIn("PHD-", path.read_text())
            with (review / "ratings.csv").open(newline="") as stream:
                ratings = list(csv.DictReader(stream))
            self.assertEqual(len(ratings), 100)
            self.assertTrue(all(all(not v for k, v in row.items() if k != "review_id") for row in ratings))
            with self.assertRaisesRegex(ValueError, "new or empty"):
                audit_existing(source, tmp, cfg, self.rubric, policy)
        self.assertEqual(tree_hash(source), before)

    def test_cli_unset_allocation_exits_cleanly_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent"
            result = subprocess.run([sys.executable, "-m", "phd_resumes", "sample-rubric", "--out", str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Allocation is unset", result.stderr)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
