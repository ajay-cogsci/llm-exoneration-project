import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.audit_ta import audit


PROJECT = Path(__file__).resolve().parents[1]
DATASET = PROJECT / "datasets/ta-applicants-v2"


class ApprovedTAAuditTests(unittest.TestCase):
    def test_approved_dataset_audits_without_a_previous_dataset(self):
        result = audit(DATASET)
        self.assertEqual(result["current"]["applicants"], 100)
        self.assertNotIn("previous", result)
        self.assertEqual(result, json.loads((DATASET / "audit.json").read_text()))

    def test_altered_plan_wording_is_rejected_without_a_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "approved"
            shutil.copytree(DATASET, copied)
            prompt = copied / "prompts/opportunity.txt"
            prompt.write_text(prompt.read_text().replace("introductory computer science", "advanced computer science"))
            with self.assertRaises(AssertionError):
                audit(copied)

    def test_only_approved_ta_assets_are_allowed_by_ignore_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(PROJECT / ".gitignore", root / ".gitignore")
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            cases = {
                "datasets/ta-applicants-v2/profiles.jsonl": 1,
                "datasets/ta-applicants-v1/profiles.jsonl": 0,
                "datasets/ta-applicants-v3/profiles.jsonl": 0,
                "datasets/ta-pilot/profiles.jsonl": 0,
                "runs/ta-draft/profiles.jsonl": 0,
                "ta_applicants/pipeline.py": 1,
                "ta_applicants_v1/pipeline.py": 0,
                "ta_applicants_v2/pipeline.py": 0,
                "configs/ta.json": 1,
                "configs/ta_v1.json": 0,
                "configs/ta_v2.json": 0,
                "TA_METHOD.md": 1,
                "TA_V2_METHOD.md": 0,
                "scripts/audit_ta.py": 1,
                "scripts/audit_ta_v2.py": 0,
                "tests/test_ta_v2.py": 0,
            }
            for path, expected in cases.items():
                with self.subTest(path=path):
                    result = subprocess.run(
                        ["git", "-C", str(root), "check-ignore", "--no-index", "--quiet", path],
                        check=False,
                    )
                    self.assertEqual(result.returncode, expected)


if __name__ == "__main__":
    unittest.main()
