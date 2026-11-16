"""Offline checks of the draft's invariants, including purposeful corruptions."""

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from analysis.phd_followup_spec import ROOT, load_manifest
from scripts.check_phd_followup import render_wordings, validate_materials


class FollowupMaterialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "configs/phd_eval_followup_v1.json").read_text())
        cls.original = json.loads((ROOT / "configs/phd_eval_v1.json").read_text())
        cls.manifest = load_manifest()

    def test_full_design_and_reused_prompts_without_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden")):
            report = validate_materials(self.config, self.original, self.manifest)
        self.assertEqual(report["requests_per_model"], 8000)
        self.assertEqual(report["exact_reused_prompt_checks"], 2800)
        self.assertEqual(report["prompts_checked_for_record_only_changes"], 8000)
        self.assertFalse(report["plan_directory_created"])

    def test_system_instruction_change_is_rejected(self):
        config = deepcopy(self.config)
        config["system_message"] = config["system_message"].replace("Do not assume or infer details that are not stated. ", "")
        with self.assertRaisesRegex(ValueError, "system_message"):
            validate_materials(config, self.original, self.manifest)

    def test_acknowledgment_cannot_add_favorable_character_trait(self):
        config = deepcopy(self.config)
        condition = next(c for c in config["conditions"] if c["id"] == "fabrication_acknowledged")
        condition["wordings"][0] += " The applicant showed resilience."
        with self.assertRaisesRegex(ValueError, "one-sentence addition"):
            validate_materials(config, self.original, self.manifest)

    def test_reused_prompt_text_cannot_drift(self):
        config = deepcopy(self.config)
        condition = next(c for c in config["conditions"] if c["id"] == "ai_use_pending")
        condition["wordings"][0] = condition["wordings"][0].replace("No finding", "No adverse finding")
        with self.assertRaisesRegex(ValueError, "Reused text changed"):
            validate_materials(config, self.original, self.manifest)

    def test_review_contains_exact_text_and_is_current(self):
        rendered = render_wordings(self.config, self.manifest)
        for condition in self.config["conditions"]:
            for text in condition["wordings"]:
                self.assertIn("\n" + text + "\n", rendered)
        self.assertEqual(rendered, (ROOT / "docs/phd_followup/WORDINGS.md").read_text())


if __name__ == "__main__":
    unittest.main()
