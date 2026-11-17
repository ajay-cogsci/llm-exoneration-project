"""Offline checks of the TA wording against the local research plan."""

import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ta_applicants.plan import (
    CRITERIA, CRITERION_FIELDS, DESCRIPTION, OPPORTUNITY, PLAN_FILENAME,
    QUALITY_PROMPT, SYSTEM_TEMPLATE, assessment_messages, verify_source,
)


class TAPlanTests(unittest.TestCase):
    def test_exact_wording_in_research_plan(self):
        source = Path(__file__).resolve().parents[1] / PLAN_FILENAME
        verify_source(source)
        if not shutil.which("pdftotext"):
            self.skipTest("pdftotext not installed; source hash was checked")
        text = subprocess.check_output(["pdftotext", "-layout", str(source), "-"], text=True)
        normalized = " ".join(text.split())
        for passage in (SYSTEM_TEMPLATE, DESCRIPTION, CRITERIA, QUALITY_PROMPT):
            self.assertIn(" ".join(passage.split()), normalized)

    def test_changed_source_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / PLAN_FILENAME
            path.write_bytes(b"changed plan")
            with self.assertRaisesRegex(ValueError, "changed"):
                verify_source(path)

    def test_assessment_uses_shared_system_and_exact_opportunity(self):
        messages = assessment_messages("Applicant TA-001\nRelevant course: Programming (A)", "the TA Selection Committee")
        self.assertEqual(messages[0], {
            "role": "system",
            "content": SYSTEM_TEMPLATE.replace("{{committee_name}}", "the TA Selection Committee"),
        })
        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn(OPPORTUNITY, messages[1]["content"])
        self.assertTrue(messages[1]["content"].endswith(QUALITY_PROMPT))
        self.assertNotIn("ACADEMIC INTEGRITY RECORD", messages[1]["content"])
        self.assertNotIn("no allegations", messages[1]["content"].lower())

    def test_explicit_condition_does_not_change_application(self):
        application = "Applicant TA-001\nRelevant course: Programming (A)"
        base = assessment_messages(application, "the TA Selection Committee")
        condition = "Academic integrity record: No allegations or findings."
        treated = assessment_messages(application, "the TA Selection Committee", integrity_text=condition)
        self.assertEqual(base[0], treated[0])
        self.assertEqual(treated[1]["content"].replace("\n\nACADEMIC INTEGRITY RECORD\n" + condition, ""), base[1]["content"])

    def test_missing_inputs_fail_closed(self):
        for application, committee in [("", "Committee"), ("Application", ""), ("Application", "{{committee_name}}")]:
            with self.assertRaises(ValueError):
                assessment_messages(application, committee)
        with self.assertRaises(ValueError):
            assessment_messages("Application", "Committee", integrity_text="")

    def test_every_plan_criterion_has_fields_without_phd_requirements(self):
        self.assertEqual(len(CRITERION_FIELDS), 5)
        fields = {field for values in CRITERION_FIELDS.values() for field in values}
        self.assertTrue({"coursework", "communication_evidence", "teaching_interest", "teaching_experience", "availability"} <= fields)
        self.assertFalse({"publications", "research_experience", "recommendation_letters"} & fields)


if __name__ == "__main__":
    unittest.main()
