"""Offline research-plan, evidence, workflow and falsification checks."""

import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from threading import Lock
from unittest.mock import patch

from phd_resumes.io import read_json, read_jsonl, write_json
from fellowship_applicants import plan
from fellowship_applicants.catalog import TOPICS, IMPACT_AREAS
from fellowship_applicants.proposals import proposal_bundle, impact_bundle
from fellowship_applicants.evidence import PRACTICE
from fellowship_applicants.sampling import evidence_dimensions, tier_from_dimensions
from fellowship_applicants.writing import estimated_application_words
from fellowship_applicants.sampling import evaluate, make_facts, make_pool, select_allocated, summarize, validate_facts, check_config
from fellowship_applicants.pipeline import PROJECT, prepare, generate, export, verify_export, load_run, body_for
from fellowship_applicants.writing import GENERATOR_INSTRUCTIONS, render_application, validate_content
from scripts.audit_fellowship import audit


def fixture_content(facts):
    output = {}
    for section,source in (("projects","projects"),("research","research_experience")):
        output[section] = [{"id":e["id"],"title":"Recorded computational work","bullets":["Completed the specified computational tasks with the recorded tools and documented the assigned analysis activities.","Worked within the recorded project scope and summarized the assigned activities without claiming additional research outcomes."]} for e in facts[source]]
    return output


class FakeAPI:
    def __init__(self, reject_first=False, incomplete=False):
        self.calls, self.requests, self.seen = 0, [], set()
        self.reject_first, self.incomplete = reject_first, incomplete
        self.lock = Lock()

    def create(self, body):
        with self.lock:
            self.calls += 1
            self.requests.append(body)
            payload = json.loads(body["input"][1]["content"])
            facts = payload["fixed_record"]
            if body["text"]["format"]["name"] == "fellowship_factual_review":
                reject = self.reject_first and facts["applicant_id"] not in self.seen
                self.seen.add(facts["applicant_id"])
                content = {"passes":not reject,"issues":["Fixture unsupported claim"] if reject else []}
            else:
                content = fixture_content(facts)
            return {"id":f"test-{self.calls}","status":"incomplete" if self.incomplete else "completed","model":"test-only-model","output":[{"type":"message","content":[{"type":"output_text","text":json.dumps(content)}]}],"usage":{"input_tokens":100,"output_tokens":100,"total_tokens":200}}


class FellowshipPlanTests(unittest.TestCase):
    def test_shared_system_template(self):
        from ta_applicants.plan import SYSTEM_TEMPLATE
        self.assertEqual(plan.SYSTEM_TEMPLATE,SYSTEM_TEMPLATE)

    def test_no_implicit_clean_record_and_explicit_condition_preserves_facts(self):
        base = plan.assessment_messages("Applicant record","the Fellowship Committee")
        condition = "Academic integrity record: No allegations or findings."
        treated = plan.assessment_messages("Applicant record","the Fellowship Committee",integrity_text=condition)
        self.assertEqual(base[0],treated[0])
        self.assertNotIn("ACADEMIC INTEGRITY RECORD",base[1]["content"])
        self.assertEqual(base[1]["content"],treated[1]["content"].replace("\n\nACADEMIC INTEGRITY RECORD\n"+condition,""))
        self.assertIn(plan.OPPORTUNITY,base[1]["content"])
        for application,committee in [("","Committee"),("record",""),("record","{{committee_name}}")]:
            with self.assertRaises(ValueError):
                plan.assessment_messages(application,committee)


class FellowshipEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read_json(PROJECT/"configs/fellowship.json")
        cls.pool = make_pool(cls.config)
        cls.rows = select_allocated(cls.pool,cls.config)

    def test_confirmed_counts_and_population(self):
        report = summarize(self.rows)
        self.assertEqual(report["n"],100)
        self.assertEqual(report["tiers"],{"weak":30,"borderline":40,"strong":30})
        self.assertEqual(report["designated_mixed"]["none"],90)
        self.assertEqual(len({r["profile_id"] for r in self.rows}),100)
        for cell in self.config["mixed_allocation"]:
            chosen = [r for r in self.rows if r["designated_mixed_pattern"] == cell["pattern"]]
            self.assertEqual(len(chosen),cell["count"])
            self.assertTrue(all(r["strength"] == cell["tier"] and cell["pattern"] in r["rubric"]["mixed_tags"] for r in chosen))

    def test_all_pool_facts_and_labels_validate(self):
        for row in self.pool:
            self.assertEqual(validate_facts(row["facts"],self.config),[],row["profile_id"])
            self.assertEqual(evaluate(row["facts"],self.config),row["rubric"])

    def test_no_network_sampling_and_reproducibility(self):
        with patch("phd_resumes.api.OpenAIResponses.create") as api:
            self.assertEqual(make_pool(self.config),self.pool)
            self.assertEqual(select_allocated(self.pool,self.config),self.rows)
        api.assert_not_called()

    def test_tiers_do_not_depend_on_quota_or_pool_size(self):
        changed = copy.deepcopy(self.config)
        changed.update(allocation={tier:1 for tier in ("weak","borderline","strong")},pool_per_seed=1)
        for row in self.rows:
            self.assertEqual(evaluate(row["facts"],changed),row["rubric"])

    def test_missing_and_contradictory_records_are_unrated(self):
        original = next(r["facts"] for r in self.rows if r["facts"]["research_experience"])
        mutations = [lambda f:f.pop("broader_impacts_plan"),lambda f:f["research_experience"][0].update(months=24),lambda f:f["research_practice"]["initiative"].update(source_id="missing"),lambda f:f["education"][1].update(start="2020-01"),lambda f:f.update(undergraduate_gpa=4.1),lambda f:f["proposed_research"]["components"].update(evaluation="Published successful results.")]
        for change in mutations:
            facts = copy.deepcopy(original); change(facts)
            self.assertEqual(evaluate(facts,self.config)["tier"],"unrated")

    def test_gpa_contradiction_is_rejected(self):
        facts = copy.deepcopy(self.rows[0]["facts"])
        for c in facts["coursework"]:
            c["grade"] = "C"
        facts["undergraduate_gpa"] = 4.0
        self.assertTrue(validate_facts(facts,self.config))

    def test_proposal_horizon_and_duplicate_work_are_rejected(self):
        facts = copy.deepcopy(next(r["facts"] for r in self.rows if r["facts"]["research_experience"]))
        facts["education"][1]["end"] = "2027-01"
        self.assertTrue(validate_facts(facts,self.config))
        facts = copy.deepcopy(next(r["facts"] for r in self.rows if r["facts"]["research_experience"]))
        facts["research_experience"][0] = copy.deepcopy(facts["projects"][0])
        self.assertTrue(validate_facts(facts,self.config))

    def test_renderer_is_independent_of_dictionary_serialization_order(self):
        facts = self.rows[0]["facts"]
        text = render_application(facts,fixture_content(facts))
        reread = json.loads(json.dumps(facts,sort_keys=True))
        self.assertEqual(render_application(reread,fixture_content(reread)),text)

    def test_incompatible_proposal_and_impact_components_fail_closed(self):
        for field,make in (("proposed_research",proposal_bundle),("broader_impacts_plan",impact_bundle)):
            facts = copy.deepcopy(self.rows[0]["facts"])
            record = facts[field]
            values = [make(record["catalog_family"],record.get("study_context",record.get("delivery_context")),record["focus"],i) for i in range(3)]
            record["components"] = copy.deepcopy(values[0])
            key = "evaluation" if field == "proposed_research" else "assessment"
            record["components"][key] = values[2][key]
            self.assertTrue(validate_facts(facts,self.config))

    def test_every_coherent_bundle_validates_and_missing_component_fails(self):
        for field,make,families in (("proposed_research",proposal_bundle,TOPICS),("broader_impacts_plan",impact_bundle,IMPACT_AREAS)):
            for family in families:
                facts = copy.deepcopy(next(r["facts"] for r in self.pool if r["facts"][field]["catalog_family"] == family))
                record = facts[field]
                for level in range(3):
                    record["components"] = make(family,record.get("study_context",record.get("delivery_context")),record["focus"],level)
                    self.assertEqual(validate_facts(facts,self.config),[])
                    key = next(iter(record["components"]))
                    del record["components"][key]
                    self.assertTrue(validate_facts(facts,self.config))

    def test_research_grade_output_and_prior_impact_sensitivity(self):
        for removal in ("graduate_C","research_experience","research_outputs","awards","prior_broader_impacts"):
            dimension_changes = tier_changes = 0
            for row in self.rows:
                f = copy.deepcopy(row["facts"])
                if removal == "graduate_C":
                    for c in f["coursework"]:
                        if c["level"] == "graduate": c["grade"] = "C"
                else:
                    f[removal] = []
                    if removal == "research_experience":
                        f["research_outputs"] = [o for o in f["research_outputs"] if o["source_id"].startswith("project-")]
                d = evidence_dimensions(f)
                dimension_changes += d != row["rubric"]["dimensions"]
                tier_changes += tier_from_dimensions(d) != row["strength"]
                self.assertLessEqual(("weak","borderline","strong").index(tier_from_dimensions(d)),("weak","borderline","strong").index(row["strength"]))
            self.assertGreater(dimension_changes,0,removal)
            if removal != "awards": self.assertGreater(tier_changes,0,removal)

    def test_weak_recent_grades_cannot_be_strong(self):
        for row in self.rows:
            f = copy.deepcopy(row["facts"])
            for c in f["coursework"]:
                if c["level"] == "graduate": c["grade"] = "C"
            self.assertNotEqual(evaluate(f,self.config)["tier"],"strong")

    def test_varied_histories_and_continuity_without_duplicate_work(self):
        report = summarize(self.rows)
        self.assertEqual(len(report["project_roles"]),4)
        self.assertGreater(len(report["project_months"]),3)
        self.assertEqual(len(report["project_counts"]),2)
        self.assertGreater(report["ra_in_proposal_area"],0)
        self.assertGreater(report["practice_source_types"].get("Research supervisor",0),0)
        self.assertEqual(report["unique_proposals"],100)
        self.assertEqual(report["unique_impact_plans"],100)
        self.assertGreater(len({e["team_size"] for r in self.rows for e in r["facts"]["projects"]}),2)

    def test_length_balance_preserves_designated_cases(self):
        means = [sum(estimated_application_words(r["facts"]) for r in self.rows if r["strength"] == t)/n for t,n in self.config["allocation"].items()]
        self.assertLessEqual(max(means)/min(means),self.config["maximum_estimated_tier_mean_ratio"])
        self.assertEqual(sum(r["designated_mixed_pattern"] != "none" for r in self.rows),10)

    def test_lower_gpa_mixed_cases_have_substantive_compensating_evidence(self):
        for r in self.rows:
            if r["designated_mixed_pattern"] == "lower_gpa_substantive_research":
                d = r["rubric"]["dimensions"]
                self.assertEqual(d["research"],2); self.assertEqual(d["proposal"],2)
                self.assertGreaterEqual(d["academic"],1)
                self.assertTrue(any(e["months"] >= 3 for e in r["facts"]["projects"]+r["facts"]["research_experience"]))

    def test_output_cannot_predate_research_or_appear_without_source(self):
        facts = copy.deepcopy(next(r["facts"] for r in self.rows if r["facts"]["research_outputs"]))
        facts["research_outputs"][0]["date"] = "2010-01"
        self.assertTrue(validate_facts(facts,self.config))
        facts["research_outputs"][0]["source_id"] = "missing"
        self.assertTrue(validate_facts(facts,self.config))

    def test_publication_and_past_outreach_are_not_strong_requirements(self):
        strong = [r for r in self.rows if r["strength"] == "strong"]
        self.assertTrue(any(not r["facts"]["research_outputs"] for r in strong))
        self.assertTrue(any(not r["facts"]["research_experience"] for r in strong))
        self.assertTrue(any(not r["facts"]["prior_broader_impacts"] for r in strong))
        survivors = []
        for r in strong:
            facts = copy.deepcopy(r["facts"])
            facts["research_outputs"] = []; facts["prior_broader_impacts"] = []
            survivors.append(evaluate(facts,self.config)["tier"] == "strong")
        self.assertTrue(any(survivors))

    def test_separate_draws_do_not_conflate_impact_preparation_and_academics(self):
        changed = copy.deepcopy(self.config)
        changed["impact_level_probabilities"] = [0,0,1]
        changed["prior_impact_count_probabilities"] = [0,0,1]
        for i in range(40):
            a,_ = make_facts(self.config,123,i); b,_ = make_facts(changed,123,i)
            for key in ("coursework","research_experience","research_practice","proposed_research"):
                self.assertEqual(a[key],b[key])
        changed = copy.deepcopy(self.config); changed["academic_level_probabilities"] = [1,0,0,0,0]
        for i in range(40):
            a,_ = make_facts(self.config,456,i); b,_ = make_facts(changed,456,i)
            self.assertEqual(a["broader_impacts_plan"],b["broader_impacts_plan"])
            self.assertEqual(a["research_practice"],b["research_practice"])

    def test_bad_allocations_and_insufficient_coverage_stop(self):
        with self.assertRaisesRegex(ValueError,"Insufficient distinct design coverage"):
            select_allocated(self.pool[:2],self.config)
        changed = copy.deepcopy(self.config)
        changed["responsibility_probabilities"] = [1,1,1]
        with self.assertRaises(ValueError):
            check_config(changed)

    def test_every_criterion_rendered_without_merit_metadata(self):
        for row in self.rows:
            facts = row["facts"]
            text = render_application(facts,fixture_content(facts))
            for field in ("proposed_research","broader_impacts_plan"):
                for value in facts[field]["components"].values():
                    self.assertIn(value,text)
            for e in facts["research_practice"].values():
                self.assertIn(e["observation"],text)
            for forbidden in ("Provisional study tier","designated_mixed_pattern","rubric_hash","latent_academic"):
                self.assertNotIn(forbidden,text)
            self.assertNotIn("no results or partnerships claimed",text)

    def test_invented_entries_treatments_and_numbers_rejected(self):
        facts = self.rows[0]["facts"]
        for title in ("An honest applicant","A strong applicant","Published superior results","Improved results by 50 percent"):
            content = fixture_content(facts); content["projects"][0]["title"] = title
            self.assertTrue(validate_content(facts,content),title)
        content = fixture_content(facts); content["research"].append(content["projects"][0])
        self.assertTrue(validate_content(facts,content))

    def test_models_receive_facts_without_tiers(self):
        body = body_for(self.config,GENERATOR_INSTRUCTIONS,{"fixed_record":self.rows[0]["facts"]})
        payload = json.loads(body["input"][1]["content"])
        self.assertEqual(payload,{"fixed_record":self.rows[0]["facts"]})
        self.assertFalse(body["store"])
        self.assertNotEqual(body["input"][0]["content"],plan.SYSTEM_TEMPLATE)


class FellowshipWorkflowTests(unittest.TestCase):
    def config(self):
        c = read_json(PROJECT/"configs/fellowship.json")
        c.update(pool_per_seed=100,allocation={tier:1 for tier in ("weak","borderline","strong")},mixed_allocation=[],max_workers=1,maximum_estimated_tier_mean_ratio=1.2)
        c["generation"]["model"] = c["generation"]["review_model"] = "test-only-model"
        return c

    def test_end_to_end_offline_cache_export_checks_and_frozen_guard(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root,out = Path(d)/"run",Path(d)/"export"
            prepare(self.config(),root); api = FakeAPI()
            generate(root,client=api); self.assertEqual(api.calls,6)
            generate(root,client=api); self.assertEqual(api.calls,6)
            report = export(root,out)
            self.assertEqual(report["verified_applications"],3)
            self.assertEqual(verify_export(out),report)
            self.assertEqual(audit(out)["errors"],[])
            self.assertTrue(all(item["condition"] is None for item in read_jsonl(out/"evaluator_inputs.jsonl")))
            reviews = [body for body in api.requests if body["text"]["format"]["name"] == "fellowship_factual_review"]
            self.assertTrue(all("PROPOSED RESEARCH" in json.loads(b["input"][1]["content"])["application_text"] for b in reviews))
            with self.assertRaises(ValueError): export(root,out)
            path = next((out/"applications").glob("*.txt")); path.write_text(path.read_text()+"Unrecorded award.")
            with self.assertRaisesRegex(ValueError,"checksum"): verify_export(out)
            c = read_json(root/"config.json"); c["selection_seed"] += 1; write_json(root/"config.json",c)
            with self.assertRaisesRegex(ValueError,"changed"): load_run(root)

    def test_separate_audit_detects_omitted_proposal_evidence(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root,out = Path(d)/"run",Path(d)/"export"
            prepare(self.config(),root); generate(root,client=FakeAPI()); export(root,out)
            row = read_jsonl(out/"profiles.jsonl")[0]
            path = out/"applications"/(row["profile_id"]+".txt")
            value = row["facts"]["proposed_research"]["components"]["evaluation"]
            path.write_text(path.read_text().replace(value,""))
            self.assertTrue(any("omitted or altered" in error for error in audit(out)["errors"]))

    def test_repairs_preserve_source_records(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)/"run"; prepare(self.config(),root)
            before = (root/"profiles.jsonl").read_bytes()
            result = generate(root,client=FakeAPI(reject_first=True))
            self.assertEqual(result["accepted_by_repair_attempt"],{"1":3})
            self.assertEqual((root/"profiles.jsonl").read_bytes(),before)

    def test_incomplete_response_stops_and_cannot_export(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)/"run"; prepare(self.config(),root)
            with self.assertRaisesRegex(ValueError,"Model run stopped"): generate(root,client=FakeAPI(incomplete=True))
            with self.assertRaises((ValueError,FileNotFoundError)): export(root,Path(d)/"export")

    def test_exhausted_factual_checks_stop_the_batch(self):
        class RejectingAPI(FakeAPI):
            def create(self, body):
                result = super().create(body)
                if body["text"]["format"]["name"] == "fellowship_factual_review":
                    result["output"][0]["content"][0]["text"] = json.dumps({"passes":False,"issues":["Persistent factual contradiction"]})
                return result
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)/"run"; prepare(self.config(),root)
            with self.assertRaisesRegex(ValueError,"Model run stopped"):
                generate(root,client=RejectingAPI())
            summary = read_json(root/"generation_summary.json")
            self.assertTrue(any("Factual checks exhausted" in f["error"] for f in summary["failures"]))
            with self.assertRaises((ValueError,FileNotFoundError)):
                export(root,Path(d)/"export")


if __name__ == "__main__":
    unittest.main()
