"""Offline tests for the bounded versioned-run helper; no network calls."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phd_resumes.io import digest, read_json, read_jsonl, write_json
from phd_resumes.sampling import generate_cohort
from scripts import run_rubric_validation as run
from test_pipeline import FakeAPI, config, fixture_content


class RepairAwareFake(FakeAPI):
    def create(self, body):
        payload = json.loads(body["input"][1]["content"])
        self.calls += 1
        is_review = body["text"]["format"]["name"] == "cv_review"
        content = {"passes": not self.reject, "issues": ["Fixture rejection"] if self.reject else []} if is_review else fixture_content(payload.get("fixed_record", payload))
        return {"id": "test-" + digest(body), "model": "test-only-model", "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(content)}]}], "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200}}


class LiveRunTests(unittest.TestCase):
    def test_partition_generate_cache_repair_and_package_without_network(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "run"
            api = RepairAwareFake()
            run.prepare(root, 30, 40, 30)
            with patch.object(run, "StoppableClient", return_value=api):
                run.generate(root, pilot=True)
                self.assertEqual(api.calls, 6)
                run.generate(root)
                self.assertEqual(api.calls, 200)
                run.generate(root)
                self.assertEqual(api.calls, 200)
                _, rows, records = run.load_run(root)
                directory, row = records[0]
                path = directory / "generation" / f"{row['profile_id']}.status.json"
                status = read_json(path)
                status.update(status="needs_revision", issues=["Fixture rejection"])
                write_json(path, status)
                run.repair(root)
                self.assertEqual(api.calls, 202)
                run.repair(root)
                self.assertEqual(api.calls, 202)
                run.package(root)
            summary = read_json(root / "validation_summary.json")
            self.assertEqual(summary["resume_count"], 100)
            self.assertEqual(summary["repaired_profiles"], 1)
            self.assertEqual(summary["selected_distribution"]["tiers"], {"weak": 30, "borderline": 40, "strong": 30})
            self.assertEqual(sum(r["rubric"]["selection_pattern"] != "none" for r in rows), 10)
            self.assertEqual(len(list((root / "resumes").glob("*.txt"))), 100)
            self.assertEqual(len(list((root / "blind_review").glob("REVIEW-*.txt"))), 100)
            self.assertFalse(summary["human_review_completed"])
            self.assertEqual(read_jsonl(root / "evaluator_fields.jsonl"), [r["facts"] for r in rows])

    def test_repairs_are_bounded_and_failed_content_never_exported(self):
        cfg = config()
        cfg["generation"].update(model="test-only-model", review_model="test-only-model")
        row = generate_cohort(cfg, 123)[1][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "shards" / "part-1"
            write_json(root / "config.json", cfg)
            write_json(directory / "generation" / f"{row['profile_id']}.status.json", {"status": "needs_revision", "issues": ["Fixture rejection"]})
            write_json(directory / "generation" / f"{row['profile_id']}.content.json", fixture_content(row["facts"]))
            api = RepairAwareFake(reject=True)
            result = run.repair_one(root, directory, row, api)
            self.assertEqual(result["status"], "needs_revision")
            self.assertEqual(result["repair_attempts"], 3)
            self.assertEqual(api.calls, 6)
            self.assertFalse((root / "repairs" / row["profile_id"] / "cv.txt").exists())
            run.repair_one(root, directory, row, api)
            self.assertEqual(api.calls, 6)


if __name__ == "__main__":
    unittest.main()
