import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phd_resumes.api import APIError, response_json
from phd_resumes.io import read_json, read_jsonl, write_json
from phd_resumes.pipeline import generate_run, inspect_configuration, sample_run
from phd_resumes.provenance import PARAMETERS
from phd_resumes.sampling import check_config, generate_cohort, quintiles, validate_profile
from phd_resumes.writing import render_cv, validate_content


def config():
    value = read_json(Path(__file__).resolve().parents[1] / "configs/phd.json")
    value.update(n_per_cohort=20, oversample=10)
    return value


def fixture_content(facts):
    mapping = {"research": "research_experience", "publications": "publications", "work": "work_experience", "projects": "projects"}
    result = {}
    for key, source in mapping.items():
        result[key] = []
        for row in facts[source]:
            entry = {"id": row["id"], "title": "Fictional test entry"}
            if key != "publications":
                entry["bullets"] = ["Prepared the assigned materials and documented the workflow for subsequent review by collaborators.", "Reviewed the available documentation and recorded methodological details within the assigned project scope."]
            result[key].append(entry)
    return result


class FakeAPI:
    def __init__(self, reject=False, incomplete=False):
        self.calls = 0
        self.reject = reject
        self.incomplete = incomplete

    def create(self, body):
        self.calls += 1
        payload = json.loads(body["input"][1]["content"])
        review = body["text"]["format"]["name"] == "cv_review"
        content = {"passes": not self.reject, "issues": ["Fixture contradiction"] if self.reject else []} if review else fixture_content(payload)
        return {"id": "test-only-response", "model": "test-only-model", "status": "incomplete" if self.incomplete else "completed", "incomplete_details": {"reason": "max_output_tokens"} if self.incomplete else None, "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(content)}]}], "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200}}


class SamplingTests(unittest.TestCase):
    def test_inspection_cannot_sample_or_call_a_model(self):
        with patch("phd_resumes.pipeline.generate_cohort") as sampler, patch("phd_resumes.api.OpenAIResponses.create") as api:
            result = inspect_configuration(config())
        sampler.assert_not_called()
        api.assert_not_called()
        self.assertEqual(result["records_generated"], 0)
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(result["planned_selected_records"], 60)

    def test_all_parameter_families_have_provenance(self):
        documented = {key for entry in PARAMETERS for key in entry["keys"]}
        self.assertEqual(set(config()) - {"version", "parameter_status", "opportunity"}, documented)

    def test_quantile_edges_include_ties_on_the_lower_side(self):
        self.assertEqual(quintiles(list(range(10))), [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        self.assertEqual(quintiles([0, 1, 1, 1, 2, 3, 4, 5, 6, 7]), [1, 1, 1, 1, 3, 3, 4, 4, 5, 5])
        with self.assertRaises(ValueError):
            quintiles([1] * 10)

    def test_course_patterns_and_source_config_are_not_shared_mutable_records(self):
        cfg = config()
        pool, _ = generate_cohort(cfg, 123)
        row = pool[0]
        level = row["latent_preparation_quintile"] - 1
        self.assertEqual(row["facts"]["coursework"], cfg["coursework_by_preparation"][level])
        row["facts"]["coursework"][0]["grade"] = "F"
        self.assertNotEqual(row["facts"]["coursework"], cfg["coursework_by_preparation"][level])

    def test_reproducibility_and_distinct_seed_cohorts(self):
        cfg = config()
        check_config(cfg)
        first = generate_cohort(cfg, 123)
        self.assertEqual(first, generate_cohort(cfg, 123))
        self.assertNotEqual(first, generate_cohort(cfg, 456))
        self.assertEqual(len(first[0]), 30)
        self.assertEqual(len(first[1]), 20)
        self.assertEqual(len({p["profile_id"] for p in first[1]}), 20)
        self.assertTrue({p["profile_id"] for p in first[1]} <= {p["profile_id"] for p in first[0]})

    def test_timeline_and_count_constraints_across_seeds(self):
        cfg = config()
        cfg.update(n_per_cohort=500, oversample=250)
        for seed in cfg["seeds"]:
            pool, _ = generate_cohort(cfg, seed)
            self.assertEqual({r["strength"] for r in pool}, {"weak", "borderline", "strong"})
            for row in pool:
                self.assertEqual(validate_profile(row), [])

    def test_no_analysis_metadata_in_cv_or_writer_input(self):
        row = generate_cohort(config(), 123)[1][0]
        for field in ("strength", "strength_status", "latent_preparation_quintile", "perf_quintile", "performance_index"):
            self.assertNotIn(field, row["facts"])
            self.assertNotIn(field, render_cv(row["facts"]))

    def test_changed_facts_are_detected(self):
        row = generate_cohort(config(), 123)[1][0]
        row["facts"]["gpa"] = 4.1
        self.assertIn("facts_hash mismatch", validate_profile(row))
        self.assertIn("GPA mismatch", validate_profile(row))

    def test_invalid_configuration_rejected(self):
        for patch in ({"n_per_cohort": 1}, {"oversample": -1}, {"seeds": [123, 123]}, {"gpa_latent_rank_coefficient": 2}):
            cfg = config()
            cfg.update(patch)
            with self.assertRaises(ValueError):
                check_config(cfg)


class GenerationTests(unittest.TestCase):
    def test_complete_pipeline_and_resume_avoid_duplicate_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            summary = sample_run(config(), root)
            self.assertEqual(summary["profiles"], 60)
            facts = read_jsonl(root / "evaluator_fields.jsonl")
            self.assertEqual(len(facts), 60)
            self.assertTrue(all("strength" not in f for f in facts))
            client = FakeAPI()
            result = generate_run(root, client, "test-model", "test-reviewer", 3)
            self.assertEqual(result["status_counts"], {"ready_for_human_review": 3})
            self.assertEqual(client.calls, 6)
            result = generate_run(root, client, "test-model", "test-reviewer", 3)
            self.assertEqual(client.calls, 6)
            self.assertEqual(result["usage_all_cached_responses_in_batch"]["total_tokens"], 1200)
            with self.assertRaises(ValueError):
                generate_run(root, client, "changed-model", "test-reviewer", 3)
            self.assertEqual(client.calls, 6)

    def test_semantic_rejection_is_not_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            sample_run(config(), root)
            result = generate_run(root, FakeAPI(reject=True), "test", "test", 1)
            self.assertEqual(result["status_counts"], {"needs_revision": 1})
            self.assertEqual(list((root / "generation" / "cvs").glob("*.txt")), [])

    def test_incomplete_response_preserved_without_silent_respending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            sample_run(config(), root)
            client = FakeAPI(incomplete=True)
            for _ in range(2):
                with self.assertRaises(APIError):
                    generate_run(root, client, "test", "test", 1)
            self.assertEqual(client.calls, 1)
            self.assertEqual(len(list((root / "generation" / "raw").glob("*.json"))), 1)

    def test_run_drift_fails_before_spending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            sample_run(config(), root)
            cfg = read_json(root / "config.json")
            cfg["review_month"] = "2027-11"
            write_json(root / "config.json", cfg)
            client = FakeAPI()
            with self.assertRaises(ValueError):
                generate_run(root, client, "test", "test", 1)
            self.assertEqual(client.calls, 0)

    def test_source_map_drift_fails_before_spending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            sample_run(config(), root)
            write_json(root / "source_map.json", {})
            client = FakeAPI()
            with self.assertRaises(ValueError):
                generate_run(root, client, "test", "test", 1)
            self.assertEqual(client.calls, 0)

    def test_extra_achievements_ids_and_leakage_rejected(self):
        facts = generate_cohort(config(), 123)[1][0]["facts"]
        valid = fixture_content(facts)
        self.assertEqual(validate_content(facts, valid), [])
        bad = copy.deepcopy(valid)
        bad["publications"].append({"id": "EXTRA", "title": "Extra paper"})
        self.assertTrue(validate_content(facts, bad))
        bad = copy.deepcopy(valid)
        bad["projects"][0]["title"] = "Honest applicant with 99 awards"
        self.assertTrue(any("leakage" in e for e in validate_content(facts, bad)))
        self.assertTrue(any("numerical" in e for e in validate_content(facts, bad)))

    def test_refusal_rejected(self):
        with self.assertRaises(APIError):
            response_json({"status": "completed", "output": [{"content": [{"type": "refusal", "refusal": "Test"}]}]})

    def test_malformed_envelope_is_logged_and_not_rebilled_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            sample_run(config(), root)
            client = FakeAPI()
            with patch.object(client, "create", return_value=[]) as create:
                for _ in range(2):
                    with self.assertRaises(APIError):
                        generate_run(root, client, "test", "test", 1)
                self.assertEqual(create.call_count, 1)
            summary = read_json(root / "generation/summary.json")
            self.assertEqual(summary["status_counts"], {"api_error": 1})
            self.assertEqual(summary["usage_all_cached_responses_in_batch"], {})
            self.assertEqual(list((root / "generation/cvs").glob("*.txt")), [])


if __name__ == "__main__":
    unittest.main()
