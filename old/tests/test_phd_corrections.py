"""Tests of the one-time PhD corrections (old/phd_revisions). No network access.

    python3 -m unittest discover -s old/tests
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "old"))

from phd_resumes.io import read_json, read_jsonl  # noqa: E402
from phd_revisions.gpa_consistency import is_consistent, revise_all, revise_profile  # noqa: E402

OLD = ROOT / "old/datasets"
SOURCE_CVS = OLD / "phd-cvs-v2-rubric-v1"
SOURCE_PACKETS = OLD / "phd-applications-v3-recommendations-v1"
CVS = ROOT / "data/phd/cvs"
PACKETS = ROOT / "data/phd/applications"


class GpaConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = SOURCE_CVS
        cls.rows = read_jsonl(source / "profiles.jsonl")
        cls.config, cls.rubric, cls.sampling = (read_json(source / n) for n in ("config.json", "rubric.json", "sampling_policy.json"))
        cls.policy = read_json(ROOT / "old/configs/phd_gpa_consistency_v1.json")

    def revise(self):
        return revise_all(self.rows, self.config, self.sampling, self.rubric, self.policy)

    def test_only_gpa_changes_and_result_is_consistent(self):
        revised, changes = self.revise()
        self.assertEqual(len(changes), 19)
        changed = {c["profile_id"] for c in changes}
        for before, after in zip(self.rows, revised):
            self.assertTrue(is_consistent(after["facts"], self.policy))
            if before["profile_id"] in changed:
                self.assertFalse(is_consistent(before["facts"], self.policy))
                self.assertEqual({**after["facts"], "gpa": before["facts"]["gpa"]}, before["facts"])
                self.assertEqual(after["features"]["gpa"], after["facts"]["gpa"])
            else:
                self.assertEqual(before, after)

    def test_deterministic_and_independent_of_other_rows(self):
        first, _ = self.revise()
        second, _ = self.revise()
        self.assertEqual(first, second)
        target = next(r for r in self.rows if not is_consistent(r["facts"], self.policy))
        alone, _ = revise_profile(target, self.config, self.sampling, self.rubric, self.policy)
        self.assertEqual(alone, next(r for r in first if r["profile_id"] == target["profile_id"]))

    def test_academic_rating_kept_whenever_possible(self):
        _, changes = self.revise()
        lost = [c for c in changes if not c["academic_rating_preserved"]]
        self.assertEqual([c["profile_id"] for c in lost], ["PHDv3-456-00958"])
        self.assertEqual([c["profile_id"] for c in changes if c["original_tier"] != c["revised_tier"]], ["PHDv3-456-00958"])

    def test_published_corrected_dataset_matches(self):
        revised, _ = self.revise()
        self.assertEqual(revised, read_jsonl(CVS / "profiles.jsonl"))


class LetterCorrection(unittest.TestCase):
    def test_only_removed_cells_changed(self):
        old = {r["applicant_id"]: r for r in read_jsonl(SOURCE_PACKETS / "recommendations.jsonl")}
        changed = 0
        for record in read_jsonl(PACKETS / "recommendations.jsonl"):
            for before, after in zip(old[record["applicant_id"]]["letters"], record["letters"]):
                if before["summary"] != after["summary"]:
                    changed += 1
                    self.assertEqual(after["strength_level"], "moderate")
                    self.assertIn((before["assignment_category"], before["strength_level"]), {("course_a_range", "limited"), ("course_b_range", "strong")})
        self.assertEqual(changed, 11)



if __name__ == "__main__":
    unittest.main()
