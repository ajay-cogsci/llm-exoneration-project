"""Offline experiment invariants and fake-client runner tests. No network calls."""

import csv
import json
import tempfile
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from phd_eval.run import APIError, parse_reply
from phd_resumes.io import read_json, read_jsonl, write_json
from fellowship_eval.design import ROOT, SHARED, application_text, build_design, check_config, load_applicants, messages
from fellowship_eval.run import OpenRouter, collect, execute, load_plan, make_plan


class FakeClient:
    def __init__(self, mode="valid", cost=0.01):
        self.calls, self.mode, self.cost = [], mode, cost

    def create(self, body):
        self.calls.append(body)
        if self.mode == "error":
            raise APIError("Simulated transport failure")
        user = body["messages"][1]["content"]
        data = {"score": 70}
        if '"advance_score"' in user:
            data = {"advance_score": 70, "advance": "yes"}
        elif '"decision_score"' in user:
            data = {"decision_score": 70, "decision": "award"}
        if '"rationale"' in user:
            data = {"rationale": "Fake test evidence.", **data}
        response = {"choices": [{"message": {"content": "unparseable test reply" if self.mode == "garbage" else json.dumps(data)}}]}
        if self.cost is not None:
            response["usage"] = {"cost": self.cost}
        return response


class FellowshipEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read_json(ROOT / "configs/fellowship_eval_v1.json")
        cls.applicants = load_applicants(cls.config)

    def make_small(self, folder):
        make_plan(self.config, folder, per_tier=1, conditions=["clean"], wordings=[1], tasks=["quality"], formats=["answer_only"])

    def run_fake(self, plan, client, **kwargs):
        return execute(plan, client, "Test model", "test/model", budget_cap=1, request_cost_ceiling=0.02, **kwargs)

    def test_shared_text_is_identical_and_roles_are_fellowship_specific(self):
        original = read_json(ROOT / "configs/phd_eval_v1.json")
        for k in SHARED:
            self.assertEqual(self.config[k], original[k])
        check_config(self.config)
        bad = deepcopy(self.config)
        bad["conditions"][0]["wordings"][0] += " New claim."
        with self.assertRaises(ValueError):
            check_config(bad)
        prompt = messages(self.config, self.applicants[0], "clean", 1, "decide", "answer_only")
        self.assertIn('"award" or "decline"', prompt[1]["content"])
        self.assertNotIn("PhD admissions committee", prompt[0]["content"])

    def test_full_design_is_unique_balanced_and_deterministic(self):
        rows = build_design(self.config, self.applicants)
        self.assertEqual(len(rows), 13200)
        self.assertEqual(len({r["request_id"] for r in rows}), 13200)
        self.assertEqual(rows, build_design(self.config, self.applicants))
        self.assertEqual(set(Counter(r["applicant_id"] for r in rows).values()), {132})
        self.assertEqual(set(Counter(r["condition"] for r in rows).values()), {1200})
        for dim, expected in [("wording", 6600), ("task", 4400), ("format", 6600)]:
            self.assertEqual(set(Counter(r[dim] for r in rows).values()), {expected})

    def test_all_applicants_all_prompts_only_record_varies(self):
        for a in self.applicants:
            text = application_text(a)
            expected = "".join(line for line in a["packet"].splitlines(keepends=True)
                               if line.rstrip("\r\n") != f"Applicant {a['applicant_id']}")
            self.assertEqual(text, expected)
            for task in self.config["tasks"]:
                for style in self.config["formats"]:
                    remainders = set()
                    for condition in self.config["conditions"]:
                        for wording, sentence in enumerate(condition["wordings"], 1):
                            system, user = messages(self.config, a, condition["id"], wording, task, style)
                            block = "INSTITUTIONAL RECORD\n" + sentence
                            self.assertEqual(user["content"].count(block), 1)
                            self.assertIn(text, user["content"])
                            self.assertNotIn(a["applicant_id"], user["content"])
                            self.assertNotIn("{{", system["content"] + user["content"])
                            remainders.add((system["content"], user["content"].replace(block, "")))
                    self.assertEqual(len(remainders), 1)

    def test_parsing_all_tasks_formats_and_invalid_decisions(self):
        client = FakeClient()
        for task in self.config["tasks"]:
            for style in self.config["formats"]:
                chat = messages(self.config, self.applicants[0], "clean", 1, task, style)
                text = client.create({"messages": chat})["choices"][0]["message"]["content"]
                self.assertTrue(parse_reply(self.config, task, style, text)["valid"])
        for word in ["admit", "reject", "yes", "maybe"]:
            self.assertFalse(parse_reply(self.config, "decide", "answer_only", json.dumps({"decision_score": 70, "decision": word}))["valid"])
        self.assertEqual(parse_reply(self.config, "decide", "answer_only", '{"decision_score": 20, "decision":"decline"}')["decision"], 0)
        for task, style, text in [("quality", "answer_only", '{"score":true}'), ("quality", "answer_only", '{"score":101}'),
                                  ("advance", "rationale", '{"advance_score":70,"advance":"yes"}')]:
            self.assertFalse(parse_reply(self.config, task, style, text)["valid"])

    def test_plan_freezes_config_implementation_and_input_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan"
            self.make_small(plan)
            self.assertEqual(len(load_plan(plan)[1]), 3)
            with self.assertRaises(ValueError):
                self.make_small(plan)
            with patch("fellowship_eval.run.implementation_hash", return_value="changed"):
                with self.assertRaises(ValueError):
                    load_plan(plan)
            changed = deepcopy(self.applicants)
            changed[0]["application_hash"] = "changed"
            # Change a selected applicant regardless of sample selection.
            selected = set(read_json(plan / "plan.json")["application_hashes"])
            for a in changed:
                if a["applicant_id"] in selected:
                    a["evaluator_text_hash"] = "changed"
            with patch("fellowship_eval.run.load_applicants", return_value=changed):
                with self.assertRaises(ValueError):
                    load_plan(plan)
            config = read_json(plan / "config.json")
            config["status"] = "edited"
            write_json(plan / "config.json", config)
            with self.assertRaises(ValueError):
                load_plan(plan)

    def test_resume_settings_retries_and_first_attempt_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan"
            self.make_small(plan)
            first = FakeClient("garbage")
            self.assertEqual(self.run_fake(plan, first, limit=1)["unparseable"], 1)
            second = FakeClient()
            self.assertEqual(self.run_fake(plan, second)["remaining"], 0)
            self.assertEqual(self.run_fake(plan, FakeClient()).get("sent_now", 0), 0)
            self.assertTrue(all(set(b) == {"model", "messages"} for b in second.calls))
            with self.assertRaises(ValueError):
                execute(plan, FakeClient(), "Test model", "different/model", budget_cap=1, request_cost_ceiling=0.02)
            collect(plan)
            with (plan / "first_attempt_results.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 3)
            self.assertEqual(sum(r["valid"] == "False" for r in rows), 1)
            stats = read_json(plan / "attempt_summary.json")["Test model"]
            self.assertEqual(stats["attempts"], 4)
            self.assertEqual(stats["unparseable_requests_retried_by_condition"], {"clean": 1})

    def test_finite_attempt_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan"
            self.make_small(plan)
            self.run_fake(plan, FakeClient("garbage"))
            self.run_fake(plan, FakeClient("garbage"))
            client = FakeClient()
            result = self.run_fake(plan, client)
            self.assertEqual(client.calls, [])
            self.assertEqual(result["exhausted_before_run"], 3)

    def test_budget_reserves_concurrent_requests_and_is_shared_across_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan"
            self.make_small(plan)
            client = FakeClient(cost=0.01)
            result = execute(plan, client, "A", "a", budget_cap=0.025, request_cost_ceiling=0.01, concurrency=4)
            self.assertEqual(len(client.calls), 2)
            self.assertLessEqual(result["total_reported_or_reserved_usd"], 0.025)
            other = FakeClient()
            execute(plan, other, "B", "b", budget_cap=0.025, request_cost_ceiling=0.01)
            self.assertFalse(other.calls)
            with self.assertRaises(ValueError):
                execute(plan, other, "B", "b", budget_cap=1, request_cost_ceiling=0.01)

    def test_missing_cost_errors_and_exceeded_bound_stop_and_block_resume(self):
        for mode, cost in [("valid", None), ("error", None), ("valid", 0.03)]:
            with self.subTest(mode=mode, cost=cost), tempfile.TemporaryDirectory() as tmp:
                plan = Path(tmp) / "plan"
                self.make_small(plan)
                result = self.run_fake(plan, FakeClient(mode, cost))
                self.assertTrue(result["stop_reasons"])
                self.assertEqual(result["sent_now"], 1)
                with self.assertRaises(ValueError):
                    self.run_fake(plan, FakeClient())

    def test_interrupted_attempt_blocks_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan"
            self.make_small(plan)
            (plan / "attempt_starts.jsonl").write_text('{"attempt_id":"interrupted"}\n')
            with self.assertRaisesRegex(ValueError, "unresolved billing"):
                self.run_fake(plan, FakeClient())

    def test_run_condition_filter_uses_same_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan"
            make_plan(self.config, plan, per_tier=1, conditions=["clean", "cleared"], wordings=[1], tasks=["quality"], formats=["answer_only"])
            first = self.run_fake(plan, FakeClient(), conditions=["clean"])
            self.assertEqual(first["sent_now"], 3)
            self.assertEqual(first["remaining"], 3)
            self.assertEqual(self.run_fake(plan, FakeClient())["remaining"], 0)

    def test_key_only_from_eval_environment_no_fallback(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only-not-real"}, clear=True):
            with self.assertRaises(APIError):
                OpenRouter()


if __name__ == "__main__":
    unittest.main()
