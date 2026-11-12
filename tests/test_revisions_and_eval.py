"""Corrected datasets and the PhD evaluation harness. No network access."""

import json
import re
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from phd_eval.design import application_text, build_design, check_config, load_applicants, messages
from phd_eval.run import APIError, collect, execute, extract_json, make_plan, parse_reply
from phd_recommendations.pipeline import check_policy
from phd_resumes.io import read_json, read_jsonl
from phd_revisions.export import CVS, PACKETS, SOURCE_CVS, SOURCE_PACKETS
from phd_revisions.gpa_consistency import is_consistent, revise_all, revise_profile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"


class FakeClient:
    """Scores the clean record 80 and every other record 60."""

    def __init__(self, fail_first=0, garbage=False):
        self.calls, self.fail_first, self.garbage = [], fail_first, garbage

    def create(self, body):
        self.calls.append(body)
        if len(self.calls) <= self.fail_first:
            raise APIError("simulated outage")
        user = body["messages"][1]["content"]
        score = 80 if "no academic integrity allegations" in user or "No allegations or findings" in user else 60
        if self.garbage:
            return {"choices": [{"message": {"content": "I cannot assess this."}}]}
        if '"advance_score"' in user:
            reply = {"advance_score": score, "advance": "yes"}
        elif '"decision_score"' in user:
            reply = {"decision_score": score, "decision": "admit"}
        else:
            reply = {"score": score}
        if '"rationale"' in user:
            reply = {"rationale": "Simulated.", **reply}
        return {"choices": [{"message": {"content": "```json\n" + json.dumps(reply) + "\n```"}}]}


class GpaConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = DATA / SOURCE_CVS
        cls.rows = read_jsonl(source / "profiles.jsonl")
        cls.config, cls.rubric, cls.sampling = (read_json(source / n) for n in ("config.json", "rubric.json", "sampling_policy.json"))
        cls.policy = read_json(ROOT / "configs" / "phd_gpa_consistency_v1.json")

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
        self.assertEqual(revised, read_jsonl(DATA / CVS / "profiles.jsonl"))


class RecommendationPolicyV2(unittest.TestCase):
    def test_no_letter_contradicts_its_grade(self):
        for record in read_jsonl(DATA / PACKETS / "recommendations.jsonl"):
            for letter in record["letters"]:
                if letter["assignment_category"] == "course_a_range":
                    self.assertNotEqual(letter["strength_level"], "limited")
                if letter["assignment_category"] == "course_b_range":
                    self.assertNotEqual(letter["strength_level"], "strong")

    def test_only_removed_cells_changed(self):
        old = {r["applicant_id"]: r for r in read_jsonl(DATA / SOURCE_PACKETS / "recommendations.jsonl")}
        changed = 0
        for record in read_jsonl(DATA / PACKETS / "recommendations.jsonl"):
            for before, after in zip(old[record["applicant_id"]]["letters"], record["letters"]):
                if before["summary"] != after["summary"]:
                    changed += 1
                    self.assertEqual(after["strength_level"], "moderate")
                    self.assertIn((before["assignment_category"], before["strength_level"]), {("course_a_range", "limited"), ("course_b_range", "strong")})
        self.assertEqual(changed, 11)

    def test_v2_policy_rejects_restored_contradictions(self):
        policy = read_json(ROOT / "configs" / "phd_recommendations_v2.json")
        check_policy(policy)
        bad = deepcopy(policy)
        bad["strength_probabilities"]["course_b_range"] = [0.25, 0.60, 0.15]
        with self.assertRaises(ValueError):
            check_policy(bad)


class Evaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read_json(ROOT / "configs" / "phd_eval_v1.json")
        cls.applicants = load_applicants(cls.config, ROOT)

    def test_configuration_and_design_size(self):
        check_config(self.config)
        self.assertEqual(len(self.applicants), 100)
        design = build_design(self.config, self.applicants)
        self.assertEqual(len(design), 100 * 11 * 2 * 3 * 2)
        self.assertEqual(len({r["request_id"] for r in design}), len(design))
        self.assertEqual(design, build_design(self.config, self.applicants))

    def test_no_identifier_or_label_reaches_a_prompt(self):
        for applicant in self.applicants:
            user = messages(self.config, applicant, "pending", 1, "quality", "answer_only")[1]["content"]
            self.assertNotIn("PHDv3", user)
            self.assertNotIn(applicant["applicant_id"], user)
            cv, letters = application_text(applicant)
            self.assertIsNone(re.search(r"\b(borderline|pathway|latent|rubric|cv tier|(weak|strong|borderline) applicant)\b", cv + letters, re.I))
            self.assertTrue(cv.startswith("EDUCATION") and letters.startswith("RECOMMENDATION SUMMARIES"))

    def test_conditions_differ_only_in_the_record_block(self):
        applicant = self.applicants[0]
        for task in self.config["tasks"]:
            for style in self.config["formats"]:
                remainders = set()
                for condition in self.config["conditions"]:
                    for number, wording in enumerate(condition["wordings"], 1):
                        system, user = messages(self.config, applicant, condition["id"], number, task, style)
                        block = "INSTITUTIONAL RECORD\n" + wording
                        self.assertEqual(user["content"].count(block), 1)
                        remainders.add((system["content"], user["content"].replace(block, "")))
                self.assertEqual(len(remainders), 1)

    def test_every_condition_is_possible_for_every_applicant(self):
        for condition in self.config["conditions"]:
            for wording in condition["wordings"]:
                self.assertNotIn("shortly before the application review", wording)
        for applicant in self.applicants:
            self.assertTrue(any(d["start"] <= "2026-02" <= d["end"] for d in applicant["facts"]["education"]))

    def test_rationale_format_adds_first_key(self):
        user = messages(self.config, self.applicants[0], "clean", 1, "advance", "rationale")[1]["content"]
        self.assertIn('Return JSON: {"rationale": "<text>", "advance_score": <integer 0-100>, "advance": "yes" or "no"}', user)
        self.assertIn("First give a brief rationale (no more than 3 sentences), then your assessment.", user)

    def test_reply_parsing(self):
        parse = lambda task, style, text: parse_reply(self.config, task, style, text)
        self.assertEqual(parse("quality", "answer_only", '{"score": 72}')["score"], 72)
        self.assertEqual(parse("decide", "answer_only", '```json\n{"decision_score": 40, "decision": "Reject"}\n```')["decision"], 0)
        self.assertEqual(parse("advance", "rationale", 'Here: {"rationale": "ok", "advance_score": 90.0, "advance": "yes"}')["decision"], 1)
        for task, style, text in (("quality", "answer_only", '{"score": 101}'), ("quality", "answer_only", '{"score": "high"}'), ("quality", "answer_only", "seventy"), ("quality", "rationale", '{"score": 70}'), ("decide", "answer_only", '{"decision_score": 50, "decision": "maybe"}'), ("quality", "answer_only", '{"score": 70, "extra": 1}'), ("quality", "answer_only", None)):
            self.assertFalse(parse(task, style, text)["valid"], text)
        self.assertIsNone(extract_json("[1, 2]"))

    def test_plan_run_resume_and_collect(self):
        with tempfile.TemporaryDirectory() as scratch:
            plan = Path(scratch) / "pilot"
            summary = make_plan(self.config, plan, root=ROOT, per_tier=2, conditions=["clean", "cleared", "responsible"], wordings=[1], formats=["answer_only"])
            self.assertEqual(summary["requests_per_model"], 6 * 3 * 1 * 3 * 1)
            with self.assertRaises(ValueError):
                make_plan(self.config, plan, root=ROOT)
            client = FakeClient(fail_first=5)
            first = execute(plan, client, "Fake model", "fake-1", root=ROOT, concurrency=1)
            self.assertEqual((first["error"], first["valid"], first["remaining"]), (5, 49, 5))
            self.assertTrue(all(set(body) == {"model", "messages"} for body in client.calls))
            second = execute(plan, FakeClient(), "Fake model", "fake-1", root=ROOT)
            self.assertEqual((second["sent_now"], second["remaining"]), (5, 0))
            self.assertEqual(execute(plan, FakeClient(), "Fake model", "fake-1", root=ROOT)["sent_now"], 0)
            with self.assertRaises(ValueError):
                execute(plan, FakeClient(), "Fake model", "fake-2", root=ROOT)
            execute(plan, FakeClient(garbage=True), "Refuser", "fake-3", root=ROOT, limit=4)
            result = collect(plan)
            self.assertEqual(result["rows"], 54 + 4)
            report = read_json(plan / "summary.json")
            self.assertEqual(report["Refuser"]["valid"], 0)
            task = report["Fake model"]["tasks"]["quality"]
            self.assertEqual(task["conditions"]["cleared"]["mean_difference_from_clean"], -20)
            self.assertEqual(task["conditions"]["clean"]["mean_difference_from_clean"], 0)
            self.assertEqual(set(task["clean_mean_score_by_cv_tier"]), {"weak", "borderline", "strong"})

    def test_run_refuses_changed_packets(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            for name in (CVS, PACKETS):
                shutil.copytree(DATA / name, scratch / "datasets" / name)
            plan = scratch / "plan"
            make_plan(self.config, plan, root=scratch, per_tier=1, conditions=["clean"], wordings=[1], tasks=["quality"], formats=["answer_only"])
            pid = read_jsonl(plan / "design.jsonl")[0]["applicant_id"]
            path = scratch / "datasets" / PACKETS / "applications" / f"{pid}.txt"
            path.write_text(path.read_text() + "Extra praise.\n")
            with self.assertRaises(ValueError):
                execute(plan, FakeClient(), "Fake model", "fake-1", root=scratch)


if __name__ == "__main__":
    unittest.main()
