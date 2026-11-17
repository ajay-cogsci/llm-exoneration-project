"""Regression checks for the substantive TA v1 audit findings."""

import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from phd_resumes.io import read_json, read_jsonl, write_json
from ta_applicants.sampling import COMMUNICATION, INTEREST
from ta_applicants.plan import SYSTEM_TEMPLATE
from ta_applicants_v2.pipeline import PROJECT, export, generate, generate_one, load_run, prepare, verify_export
from ta_applicants_v2.sampling import ANCHORS, evaluate, make_facts, make_pool, select_allocated, summarize, validate_facts
from ta_applicants_v2.writing import render_application
from test_ta_pipeline import FakeAPI, fixture_content


class TAV2EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read_json(PROJECT / "configs/ta_v2.json")
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


class TAV2WorkflowTests(unittest.TestCase):
    def config(self):
        config=read_json(PROJECT/"configs/ta_v2.json")
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


if __name__=="__main__":
    unittest.main()
