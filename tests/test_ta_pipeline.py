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
from ta_applicants.sampling import ANCHORS, INTEREST, make_facts, DUTIES, COMMUNICATION, PERFORMANCE, evaluate, make_pool, select_allocated, summarize, validate_facts
from ta_applicants.plan import SYSTEM_TEMPLATE
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
        cls.config = read_json(PROJECT / "configs/ta.json")
        cls.pool = make_pool(cls.config)
        cls.rows = select_allocated(cls.pool, cls.config)

    def test_authorized_counts_and_graduate_enrollment(self):
        report = summarize(self.rows)
        self.assertEqual(report["tiers"], {"weak": 30, "borderline": 40, "strong": 30})
        self.assertEqual(sum(r["designated_mixed_pattern"] != "none" for r in self.rows), 10)
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
        changed["allocation"] = {}
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
        self.assertEqual(evaluate(facts, self.config)["tier"], "unrated")
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
        with self.assertRaisesRegex(ValueError, "Insufficient coverage"):
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
        def field_names(value):
            if isinstance(value, dict):
                return set(value).union(*(field_names(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(field_names(v) for v in value))
            return set()
        for key in ("strength", "rubric", "latent_academic_level", "latent_teaching_level", "selection_pattern"):
            self.assertNotIn(key, field_names(payload))
        self.assertFalse(body["store"])


class TAWorkflowTests(unittest.TestCase):
    def config(self):
        config = read_json(PROJECT / "configs/ta.json")
        config["allocation"] = {tier: 1 for tier in ("weak", "borderline", "strong")}
        config["mixed_allocation"] = []
        config["pool_per_seed"] = 100
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


class TAEvidenceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read_json(PROJECT / "configs/ta.json")
        cls.pool = make_pool(cls.config)
        cls.rows = select_allocated(cls.pool,cls.config)

    def strong_novice(self):
        return copy.deepcopy(next(r["facts"] for r in self.rows if r["strength"] == "strong" and not r["facts"]["teaching_experience"]))

    def test_100_graduates_30_40_30_and_exactly_10_designated_cases(self):
        report = summarize(self.rows)
        self.assertEqual(report["n"],100)
        self.assertEqual(report["tiers"],{"weak":30,"borderline":40,"strong":30})
        self.assertEqual(report["designated_mixed"]["none"],90)
        self.assertEqual(sum(report["graduate_degrees"].values()),100)
        self.assertEqual(len({r["profile_id"] for r in self.rows}),100)
        self.assertEqual(report["unavailable"],0)
        for cell in self.config["mixed_allocation"]:
            chosen=[r for r in self.rows if r["designated_mixed_pattern"]==cell["pattern"]]
            self.assertEqual(len(chosen),cell["count"])
            self.assertTrue(all(r["strength"]==cell["tier"] and cell["pattern"] in r["rubric"]["mixed_tags"] for r in chosen))

    def test_first_time_applicants_can_be_strong_without_fabricated_experience(self):
        facts = self.strong_novice()
        rating = evaluate(facts,self.config)
        self.assertEqual(rating["tier"],"strong")
        self.assertEqual(rating["teaching_performance"],"no_prior_evidence")
        self.assertEqual(facts["teaching_experience"],[])
        self.assertGreaterEqual(summarize(self.rows)["first_time_by_tier"]["strong"],3)
        self.assertIn("No previous teaching, tutoring, or TA experience reported.",render_application(facts,fixture_content(facts)))

    def test_high_grades_adequate_communication_and_interest_suffice_for_novice(self):
        facts=self.strong_novice()
        for c in facts["coursework"]:
            if c["course"] in ANCHORS and c["level"]=="undergraduate":c["grade"]="A"
        for mode,e in facts["communication_evidence"].items():
            e.update(rating="satisfactory",observation=COMMUNICATION[mode]["satisfactory"])
        facts["teaching_interest"]={"category":"beginner_support","statement":INTEREST["beginner_support"]}
        self.assertEqual(evaluate(facts,self.config)["tier"],"strong")

    def test_experience_intervention_cannot_change_communication(self):
        none,experienced=copy.deepcopy(self.config),copy.deepcopy(self.config)
        none["teaching_count_probabilities"]=[1,0,0]
        experienced["teaching_count_probabilities"]=[0,0,1]
        for index in range(80):
            a,_=make_facts(none,123,index);b,_=make_facts(experienced,123,index)
            self.assertEqual(a["teaching_experience"],[])
            self.assertEqual(len(b["teaching_experience"]),2)
            self.assertEqual(a["communication_evidence"],b["communication_evidence"])
            self.assertEqual(a["coursework"],b["coursework"])

    def test_communication_intervention_does_not_change_experience(self):
        variant=copy.deepcopy(self.config)
        for cell in variant["communication_pairs"]:
            cell["probability"]=int(cell["written"]==cell["oral"]=="effective")
        for index in range(30):
            a,_=make_facts(self.config,456,index);b,_=make_facts(variant,456,index)
            self.assertEqual(a["teaching_experience"],b["teaching_experience"])
            self.assertEqual(b["communication_evidence"]["oral"]["rating"],"effective")

    def test_old_extreme_communication_imbalance_is_not_reproduced(self):
        for rows in (self.pool,self.rows):
            report=summarize(rows)["communication_by_experience"]
            self.assertLess(abs(report["first_time"]["fraction"]-report["experienced"]["fraction"]),0.15)

    def test_unavailable_duties_are_separate_from_merit_tiers(self):
        facts=self.strong_novice()
        facts["availability"]["office_hours"]=False
        rating=evaluate(facts,self.config)
        self.assertEqual(rating["tier"],"unrated")
        self.assertEqual(rating["eligibility"],"unavailable_for_required_duties")
        self.assertEqual(rating["issues"],[])

    def test_diversity_is_in_facts_not_only_in_prose(self):
        report=summarize(self.rows)
        self.assertGreaterEqual(report["unique_education_histories"],30)
        self.assertGreaterEqual(report["unique_grade_vectors"],40)
        self.assertGreaterEqual(report["unique_skill_sets"],10)
        self.assertEqual(set(report["project_counts"]),{"1","2","3"})
        self.assertEqual(len(report["project_families"]),8)
        self.assertGreaterEqual(report["unique_project_task_sets"],30)

    def test_selected_facts_are_unchanged_members_of_pool(self):
        pool={r["profile_id"]:r for r in self.pool}
        for row in self.rows:
            source=pool[row["profile_id"]]
            for key in ("facts","facts_hash","rubric","strength"):
                self.assertEqual(row[key],source[key])

    def test_all_6000_records_have_coherent_dates_sources_and_grades(self):
        for row in self.pool:
            self.assertEqual(validate_facts(row["facts"],self.config),[],row["profile_id"])

    def test_invalid_evidence_does_not_become_a_weak_profile(self):
        facts=self.strong_novice();del facts["communication_evidence"]
        self.assertEqual(evaluate(facts,self.config)["tier"],"unrated")

    def test_impossible_gpa_and_wrong_project_tools_are_rejected(self):
        facts=copy.deepcopy(next(r["facts"] for r in self.rows if r["strength"]=="weak"))
        facts["undergraduate_gpa"]=4.0
        self.assertTrue(validate_facts(facts,self.config))
        facts=self.strong_novice()
        facts["projects"][0]["tools"]=["invented tool"]
        self.assertTrue(validate_facts(facts,self.config))

    def test_history_repair_cannot_exceed_recorded_dates(self):
        facts=copy.deepcopy(next(r["facts"] for r in self.rows if r["facts"]["teaching_experience"]))
        facts["teaching_experience"][0]["months"]+=24
        self.assertTrue(validate_facts(facts,self.config))

    def test_campus_teaching_in_an_enrollment_gap_is_rejected(self):
        facts=copy.deepcopy(next(r["facts"] for r in self.pool if r["facts"]["education"][0]["end"]<="2021-05" and r["facts"]["education"][1]["start"]>="2025-01" and r["facts"]["teaching_experience"]))
        entry=facts["teaching_experience"][0]
        entry.update(start="2023-01",end="2023-05",months=4)
        facts["teaching_experience"]=[entry]
        self.assertIn("Campus teaching appointment outside enrolled study",validate_facts(facts,self.config))

    def test_no_strong_profile_has_undecided_or_unspecified_beginner_interest(self):
        self.assertTrue(all(r["facts"]["teaching_interest"]["category"]=="beginner_support" for r in self.rows if r["strength"]=="strong"))

    def test_selection_and_pool_reproduce_without_model_calls(self):
        with patch("phd_resumes.api.OpenAIResponses.create") as api:
            self.assertEqual(make_pool(self.config),self.pool)
            self.assertEqual(select_allocated(self.pool,self.config),self.rows)
        api.assert_not_called()

class TAWorkflowRegressionTests(unittest.TestCase):
    def config(self):
        config=read_json(PROJECT/"configs/ta.json")
        config["pool_per_seed"]=100
        config["allocation"]={"weak":1,"borderline":1,"strong":1}
        config["mixed_allocation"]=[]
        config["max_workers"]=1
        config["generation"]["model"]=config["generation"]["review_model"]="test-only-model"
        return config

    def test_full_offline_generation_export_and_cache(self):
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            root,out=Path(directory)/"run",Path(directory)/"export"
            prepare(self.config(),root)
            api=FakeAPI();generate(root,client=api);generate(root,client=api)
            self.assertEqual(api.calls,6)
            result=export(root,out)
            self.assertEqual(result["verified_applications"],3)
            self.assertEqual(verify_export(out),result)
            for record in read_jsonl(out/"evaluator_inputs.jsonl"):
                self.assertIsNone(record["condition"])
                self.assertEqual(record["messages"][0]["content"],SYSTEM_TEMPLATE.replace("{{committee_name}}",self.config()["committee_name"]))
                self.assertNotIn("designated_mixed_pattern",str(record["messages"]))
            with self.assertRaises(ValueError):export(root,out)

    def test_repairs_keep_facts_and_do_not_replace_failed_profiles(self):
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory)/"run";prepare(self.config(),root)
            before=(root/"profiles.jsonl").read_bytes()
            api=FakeAPI(reject_first=True);generate(root,client=api)
            self.assertEqual(api.calls,12)
            self.assertEqual((root/"profiles.jsonl").read_bytes(),before)
            rejected=Path(directory)/"rejected";prepare(self.config(),rejected)
            api=FakeAPI(reject=True);generate(rejected,client=api);generate(rejected,client=api)
            self.assertEqual(api.calls,18)
            with self.assertRaises(ValueError):export(rejected,Path(directory)/"bad")

    def test_tampering_with_frozen_facts_or_output_fails(self):
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory)/"run";prepare(self.config(),root);generate(root,client=FakeAPI())
            config,rows=load_run(root)
            content_path=root/"generation"/rows[0]["profile_id"]/"content.json"
            content=read_json(content_path);content["projects"][0]["title"]="Changed title";write_json(content_path,content)
            with self.assertRaises(ValueError):generate_one(root,rows[0],config,FakeAPI(),Event())
            config["selection_seed"]+=1;write_json(root/"config.json",config)
            with self.assertRaises(ValueError):load_run(root)

class ApprovedTAReleaseTests(unittest.TestCase):
    def test_current_config_and_model_contract_match_approved_release(self):
        from ta_applicants.pipeline import contract
        source = PROJECT / "data/ta"
        config = read_json(PROJECT / "configs/ta.json")
        self.assertEqual(config, read_json(source / "config.json"))
        self.assertEqual(contract(config), read_json(source / "generation_contract.json"))

    def test_approved_export_reproduces_with_the_single_pipeline(self):
        result = verify_export(PROJECT / "data/ta")
        self.assertEqual(result["verified_applications"], 100)
        self.assertEqual(result["pool_reproduced"], 6000)

    def test_implementation_change_guard_remains_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            config = TAWorkflowRegressionTests().config()
            root = Path(directory) / "run"
            prepare(config, root)
            manifest = read_json(root / "manifest.json")
            manifest["implementation_hash"] = "different-source"
            write_json(root / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "Implementation changed"):
                load_run(root)


if __name__ == "__main__":
    unittest.main()
