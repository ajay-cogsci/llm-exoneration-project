"""TA sampler, factual constraints, bounded API workflow and export checks."""

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from threading import Event, Lock
from unittest.mock import patch

from phd_resumes.io import digest, read_json, read_jsonl, write_json
from ta_applicants.pipeline import PROJECT, body_for, export, generate, generate_one, load_run, prepare, verify_export
from ta_applicants.sampling import DUTIES, COMMUNICATION, PERFORMANCE, evaluate, make_pool, select_allocated, summarize, validate_facts
from ta_applicants.writing import GENERATOR_INSTRUCTIONS, render_application, validate_content


def fixture_content(facts):
    result = {"teaching": [], "projects": []}
    for section, source in (("teaching", "teaching_experience"), ("projects", "projects")):
        for entry in facts[source]:
            result[section].append({"id": entry["id"], "title": "Programming exercise support" if section == "teaching" else "Course programming project", "bullets": ["Worked through the recorded programming tasks and documented the approach using the specified tools.", "Reviewed the assigned examples and explained the recorded activities within the specified project scope."]})
    return result


class FakeAPI:
    def __init__(self, reject=False, reject_first=False, incomplete=False):
        self.calls, self.requests = 0, []
        self.reject, self.reject_first, self.incomplete = reject, reject_first, incomplete
        self.lock = Lock()
        self.reviews = {}

    def create(self, body):
        with self.lock:
            self.calls += 1
            self.requests.append(body)
            payload = json.loads(body["input"][1]["content"])
            facts = payload["fixed_record"]
            review = body["text"]["format"]["name"] == "ta_factual_review"
            if review:
                pid = facts["applicant_id"]
                seen = self.reviews.get(pid, 0)
                self.reviews[pid] = seen + 1
                reject = self.reject or (self.reject_first and seen == 0)
                content = {"passes": not reject, "issues": ["Fixture unsupported activity"] if reject else []}
            else:
                content = fixture_content(facts)
            return {"id": f"fixture-{self.calls}", "status": "incomplete" if self.incomplete else "completed", "model": "test-only-model", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(content)}]}], "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200}}


class TASamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read_json(PROJECT / "configs/ta_v1.json")
        cls.pool = make_pool(cls.config)
        cls.rows = select_allocated(cls.pool, cls.config)

    def test_authorized_counts_and_graduate_enrollment(self):
        report = summarize(self.rows)
        self.assertEqual(report["tiers"], {"weak": 30, "borderline": 40, "strong": 30})
        self.assertEqual(sum(r["rubric"]["selection_pattern"] != "none" for r in self.rows), 10)
        self.assertEqual(len({r["profile_id"] for r in self.rows}), 100)
        self.assertTrue(all(r["facts"]["education"][-1]["degree"] in {"MS in Computer Science", "PhD in Computer Science"} for r in self.rows))

    def test_pool_and_selection_reproduce_without_model_calls(self):
        with patch("phd_resumes.api.OpenAIResponses.create") as api:
            self.assertEqual(make_pool(self.config), self.pool)
            self.assertEqual(select_allocated(self.pool, self.config), self.rows)
        api.assert_not_called()

    def test_all_source_records_pass_chronology_and_evidence_checks(self):
        for row in self.pool:
            self.assertEqual(validate_facts(row["facts"], self.config), [], row["profile_id"])
            self.assertEqual(row["facts_hash"], digest(row["facts"]))

    def test_tiers_do_not_depend_on_cohort_or_quota(self):
        changed = copy.deepcopy(self.config)
        changed["allocation"] = []
        changed["pool_per_seed"] = 1
        for row in self.rows:
            self.assertEqual(evaluate(row["facts"], changed), row["rubric"])

    def test_missing_evidence_is_unrated(self):
        facts = copy.deepcopy(self.rows[0]["facts"])
        del facts["communication_evidence"]
        self.assertEqual(evaluate(facts, self.config)["tier"], "unrated")

    def test_zero_experience_does_not_create_teaching_entries(self):
        row = next(r for r in self.rows if not r["facts"]["teaching_experience"])
        content = fixture_content(row["facts"])
        self.assertEqual(content["teaching"], [])
        self.assertIn("No previous teaching, tutoring, or TA experience reported.", render_application(row["facts"], content))
        content["teaching"].append(copy.deepcopy(content["projects"][0]))
        self.assertTrue(validate_content(row["facts"], content))

    def test_availability_and_communication_limit_strong_label(self):
        facts = copy.deepcopy(next(r["facts"] for r in self.rows if r["strength"] == "strong"))
        facts["availability"][DUTIES[0]] = False
        self.assertEqual(evaluate(facts, self.config)["tier"], "borderline")
        facts["availability"][DUTIES[0]] = True
        facts["communication_evidence"]["written"].update(rating="needs_improvement", observation=COMMUNICATION["written"]["needs_improvement"])
        self.assertEqual(evaluate(facts, self.config)["tier"], "borderline")

    def test_feedback_and_duration_cannot_contradict_source(self):
        facts = copy.deepcopy(next(r["facts"] for r in self.rows if r["facts"]["teaching_experience"]))
        facts["teaching_experience"][0]["months"] += 24
        self.assertTrue(validate_facts(facts, self.config))
        facts = copy.deepcopy(next(r["facts"] for r in self.rows if r["facts"]["teaching_experience"]))
        facts["teaching_experience"][0]["performance_note"] = "Best teacher ever."
        self.assertTrue(validate_facts(facts, self.config))

    def test_missing_cells_fail_instead_of_relabelling(self):
        with self.assertRaisesRegex(ValueError, "Insufficient pool coverage"):
            select_allocated(self.pool[:2], self.config)

    def test_source_records_have_no_shared_mutable_lists(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["facts"]["technical_skills"].append("invented")
        self.assertNotIn("invented", rows[1]["facts"]["technical_skills"])

    def test_fixed_renderer_preserves_all_five_criteria(self):
        facts = self.rows[0]["facts"]
        text = render_application(facts, fixture_content(facts))
        for heading in ("EDUCATION", "COMMUNICATION EVIDENCE", "TEACHING INTEREST", "TEACHING AND TUTORING EXPERIENCE", "AVAILABILITY FOR THE ADVERTISED DUTIES"):
            self.assertIn(heading, text)
        self.assertIn(facts["teaching_interest"]["statement"], text)
        for mode in ("written", "oral"):
            self.assertIn(facts["communication_evidence"][mode]["observation"], text)

    def test_treatment_and_numerical_inventions_are_rejected(self):
        facts = self.rows[0]["facts"]
        for title in ("Improved grades by 90 percent", "An honest applicant", "Borderline candidate", "Published research"):
            content = fixture_content(facts)
            content["projects"][0]["title"] = title
            self.assertTrue(validate_content(facts, content), title)

    def test_generator_receives_only_fixed_facts(self):
        row = self.rows[0]
        body = body_for(self.config, GENERATOR_INSTRUCTIONS, {"fixed_record": row["facts"]})
        payload = json.loads(body["input"][1]["content"])
        self.assertEqual(payload, {"fixed_record": row["facts"]})
        for key in ("strength", "rubric", "latent_academic_level", "latent_teaching_level", "selection_pattern"):
            self.assertNotIn(key, json.dumps(payload))
        self.assertFalse(body["store"])


class TAWorkflowTests(unittest.TestCase):
    def config(self):
        config = read_json(PROJECT / "configs/ta_v1.json")
        config["allocation"] = [{"tier": tier, "pattern": "none", "count": 1} for tier in ("weak", "borderline", "strong")]
        config["generation"]["model"] = config["generation"]["review_model"] = "test-only-model"
        config["max_workers"] = 1
        return config

    def test_prepare_generate_cache_export_verify_without_network(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root, out = Path(directory) / "run", Path(directory) / "export"
            prepare(self.config(), root)
            api = FakeAPI()
            generate(root, client=api)
            self.assertEqual(api.calls, 6)
            generate(root, client=api)
            self.assertEqual(api.calls, 6)
            result = export(root, out)
            self.assertEqual(result["verified_applications"], 3)
            self.assertEqual(verify_export(out), result)
            inputs = read_jsonl(out / "evaluator_inputs.jsonl")
            self.assertTrue(all(item["condition"] is None for item in inputs))
            self.assertNotIn("raw", {path.name for path in out.iterdir()})
            for item in inputs:
                self.assertNotIn("provisional study tier", item["messages"][1]["content"].lower())
            with self.assertRaises(ValueError):
                export(root, out)
            with self.assertRaises(ValueError):
                prepare(self.config(), root)

    def test_repair_preserves_facts_and_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory) / "run"
            prepare(self.config(), root)
            before = (root / "profiles.jsonl").read_bytes()
            api = FakeAPI(reject_first=True)
            generate(root, client=api)
            self.assertEqual(api.calls, 12)
            self.assertEqual((root / "profiles.jsonl").read_bytes(), before)
            generate(root, client=api)
            self.assertEqual(api.calls, 12)
            rejected_root = Path(directory) / "rejected"
            prepare(self.config(), rejected_root)
            rejected = FakeAPI(reject=True)
            summary = generate(rejected_root, client=rejected)
            self.assertEqual(rejected.calls, 18)
            self.assertEqual(summary["status_counts"], {"needs_revision": 3})
            generate(rejected_root, client=rejected)
            self.assertEqual(rejected.calls, 18)
            with self.assertRaises(ValueError):
                export(rejected_root, Path(directory) / "bad-export")
            self.assertFalse((Path(directory) / "bad-export").exists())

    def test_changed_facts_and_cached_content_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory) / "run"
            prepare(self.config(), root)
            generate(root, client=FakeAPI())
            config, rows = load_run(root)
            content_path = root / "generation" / rows[0]["profile_id"] / "content.json"
            content = read_json(content_path)
            content["projects"][0]["title"] = "Changed title"
            write_json(content_path, content)
            with self.assertRaisesRegex(ValueError, "changed content"):
                generate_one(root, rows[0], config, FakeAPI(), Event())
            config["review_month"] = "2026-12"
            write_json(root / "config.json", config)
            with self.assertRaisesRegex(ValueError, "changed"):
                load_run(root)

    def test_incomplete_model_response_stops_and_cannot_export(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory) / "run"
            prepare(self.config(), root)
            with self.assertRaisesRegex(ValueError, "Model run stopped"):
                generate(root, client=FakeAPI(incomplete=True))
            self.assertTrue(read_json(root / "generation_summary.json")["failures"])
            with self.assertRaises((ValueError, FileNotFoundError)):
                export(root, Path(directory) / "bad-export")

    def test_export_detects_edited_application(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root, out = Path(directory) / "run", Path(directory) / "export"
            prepare(self.config(), root)
            generate(root, client=FakeAPI())
            export(root, out)
            path = next((out / "applications").glob("*.txt"))
            path.write_text(path.read_text() + "Unrecorded award.\n")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify_export(out)


if __name__ == "__main__":
    unittest.main()
