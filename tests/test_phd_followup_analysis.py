"""Synthetic analysis tests; never use real responses or call an API."""

import contextlib
import csv
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import scipy
except ImportError:
    scipy = None

from analysis import analyze_phd_followup as analysis
from analysis.phd_followup_spec import CONDITIONS, MODELS, TASKS
from phd_resumes.io import digest


def fixture(applicants=("SYNTHETIC_A", "SYNTHETIC_B")):
    design, rows = {}, []
    label = "GPT-5.4 mini"
    for i, applicant in enumerate(applicants):
        for condition in CONDITIONS:
            for wording in (1, 2):
                for task in TASKS:
                    rid = f"{applicant}|{condition}|w{wording}|{task}|answer_only|r1"
                    planned = dict(request_id=rid, applicant_id=applicant, condition=condition,
                                   wording=wording, task=task, format="answer_only", repeat=1, cv_tier="borderline")
                    design[rid] = planned
                    # Wording variation cancels within each applicant. Independent
                    # applicant differences are 3 and 5 for cleared minus verified.
                    baseline = 50 + i % 2 * 10 + (2 if wording == 2 else -2)
                    increment = (3 + i % 2 * 2) if condition == "ai_use_cleared" else 0
                    rows.append(planned | dict(model_label=label, api_model=MODELS[label], valid=True,
                                               score=baseline + increment, decision=1 if baseline > 55 else 0,
                                               error="", request_parameters={}))
    return design, rows


@unittest.skipIf(scipy is None, "Install analysis/requirements.txt for analysis tests")
class FollowupAnalysisTests(unittest.TestCase):
    def test_paired_unit_is_applicant_not_wording(self):
        design, rows = fixture()
        cells = analysis.cell_values(rows, "score")
        d = analysis.differences(cells, "GPT-5.4 mini", "advance", ["SYNTHETIC_A", "SYNTHETIC_B"],
                                 {"ai_use_cleared": 1, "ai_use_verified": -1})
        self.assertEqual(list(d.values()), [3, 5])
        result = analysis.paired_summary(d.values(), 36)
        self.assertEqual(result["n_applicants"], 2)
        self.assertEqual(result["estimate"], 4)
        self.assertAlmostEqual(result["se"], 1)
        self.assertLess(result["ci_low_adj"], result["ci_low"])

    def test_missing_wording_excludes_incomplete_applicant(self):
        _, rows = fixture()
        rows = [r for r in rows if not (r["applicant_id"] == "SYNTHETIC_B" and
                                        r["condition"] == "ai_use_verified" and r["wording"] == 2)]
        d = analysis.differences(analysis.cell_values(rows, "score"), "GPT-5.4 mini", "advance",
                                 ["SYNTHETIC_A", "SYNTHETIC_B"], {"ai_use_cleared": 1, "ai_use_verified": -1})
        self.assertEqual(d, {"SYNTHETIC_A": 3})
        self.assertIsNone(analysis.paired_summary(d.values(), 36)["p_raw"])

    def test_holm_family_does_not_shrink_when_models_are_missing(self):
        self.assertAlmostEqual(analysis.holm_fixed([.001] + [None] * 35)[0], .036)
        _, rows = fixture()
        estimates = analysis.estimate_all(rows, ["SYNTHETIC_A", "SYNTHETIC_B"])
        primary = [r for r in estimates if r["family"] == "primary_advance_score"]
        self.assertEqual(len(primary), 36)
        self.assertEqual({r["n_in_family"] for r in primary}, {36})
        missing = [r for r in primary if r["model"] != "GPT-5.4 mini"]
        self.assertTrue(all(r["p_raw"] is None and r["n_applicants"] == 0 for r in missing))

    def test_binary_difference_is_a_rate_not_a_score(self):
        _, rows = fixture()
        for row in rows:
            if row["condition"] == "ai_use_cleared":
                row["decision"] = 1
        d = analysis.differences(analysis.cell_values(rows, "decision"), "GPT-5.4 mini", "advance",
                                 ["SYNTHETIC_A", "SYNTHETIC_B"], {"ai_use_cleared": 1, "ai_use_verified": -1})
        self.assertEqual(statistics_mean(d.values()), .5)

    def test_scenario_interaction_uses_four_matched_cells(self):
        _, rows = fixture()
        for row in rows:
            if row["condition"] == "fabrication_cleared":
                row["score"] += 2
            if row["condition"] == "technical_error_cleared":
                row["score"] += 5
        d = analysis.differences(analysis.cell_values(rows, "score"), "GPT-5.4 mini", "advance",
                                 ["SYNTHETIC_A", "SYNTHETIC_B"], {"fabrication_cleared": 1,
                                 "fabrication_verified": -1, "technical_error_cleared": -1, "technical_error_verified": 1})
        self.assertEqual(set(d.values()), {-3})

    def test_invalid_model_score_and_duplicate_are_rejected(self):
        design, rows = fixture()
        with self.assertRaisesRegex(ValueError, "mismatched API"):
            analysis.normalize(rows[0] | {"api_model": "different/model"}, design)
        with self.assertRaisesRegex(ValueError, "integer"):
            analysis.normalize(rows[0] | {"score": math.nan}, design)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analysis.cell_values([rows[0], rows[0]], "score")

    def test_first_attempt_audit_retains_unparseable_and_errors(self):
        design, rows = fixture()
        good = rows[0] | {"response": {"usage": {"cost": .002}}}
        bad = good | {"valid": False, "score": None, "decision": None, "response": {"usage": {"cost": .001}}}
        error = rows[1] | {"valid": False, "score": None, "decision": None, "error": "synthetic error", "response": None}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "synthetic.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (bad, good, error)))
            first, audit = analysis.attempt_audit(tmp, design)
        self.assertEqual(len(first), 2)
        self.assertFalse(any(r["valid"] for r in first))
        cell = next(r for r in audit if r["model"] == "GPT-5.4 mini" and r["condition"] == "clean")
        self.assertEqual(cell["requests_retried_after_unparseable"], 1)
        self.assertEqual(cell["error_attempts"], 1)
        self.assertAlmostEqual(cell["known_cost_usd"], .003)
        self.assertEqual(cell["attempts_without_reported_cost"], 1)

    def test_synthetic_cli_is_provisional_and_cannot_overwrite_outputs(self):
        design, rows = fixture([f"SYNTHETIC_{i:03}" for i in range(100)])
        with tempfile.TemporaryDirectory() as tmp:
            plan, out = Path(tmp) / "synthetic_plan", Path(tmp) / "synthetic_analysis"
            plan.mkdir()
            config = {"followup": {"study_id": "phd-focused-followup-v1"}, "request_parameters": {}}
            (plan / "config.json").write_text(json.dumps(config))
            (plan / "design.jsonl").write_text("".join(json.dumps(r) + "\n" for r in design.values()))
            (plan / "plan.json").write_text(json.dumps({"config_hash": digest(config), "design_hash": digest(list(design.values()))}))
            with (plan / "results.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader(); writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "Incomplete study"):
                analysis.main(["--plan", str(plan), "--out", str(out)])
            self.assertFalse(out.exists())
            with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden")), contextlib.redirect_stdout(io.StringIO()):
                analysis.main(["--plan", str(plan), "--out", str(out), "--allow-incomplete"])
            status = json.loads((out / "analysis_status.json").read_text())
            self.assertTrue(status["provisional"])
            self.assertEqual(status["correction_families"]["primary_advance_score"], 36)
            self.assertFalse(status["first_attempt_logs_available"])
            with self.assertRaises(FileExistsError):
                analysis.main(["--plan", str(plan), "--out", str(out), "--allow-incomplete"])


def statistics_mean(values):
    values = list(values)
    return sum(values) / len(values)


if __name__ == "__main__":
    unittest.main()
