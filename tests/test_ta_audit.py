import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.audit_ta import audit


PROJECT = Path(__file__).resolve().parents[1]
DATASET = PROJECT / "data/ta"


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

    def test_only_published_ta_data_is_tracked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(PROJECT / ".gitignore", root / ".gitignore")
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            cases = {
                "data/ta/profiles.jsonl": 1,
                "data/ta-draft/profiles.jsonl": 0,
                "data/ta-pilot/profiles.jsonl": 0,
                "runs/ta-draft/profiles.jsonl": 0,
                "src/generate/ta_applicants/pipeline.py": 1,
                "configs/ta.json": 1,
                "docs/methods/ta.md": 1,
                "scripts/audit_ta.py": 1,
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
