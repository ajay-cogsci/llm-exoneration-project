"""RA plan, evidence, allocation and generation workflow checks."""

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
from ra_applicants import plan
from ra_applicants.catalog import WORK_EVIDENCE, INTEREST, FAMILIES, technical_bundle, implementation_support
from ra_applicants.sampling import evaluate, evidence_dimensions, tier_from_dimensions, make_facts, make_pool, select_allocated, summarize, validate_facts, check_config, work_signature, portfolio_signature
from ra_applicants.pipeline import PROJECT, prepare, generate, export, verify_export, load_run, body_for
from ra_applicants.writing import GENERATOR_INSTRUCTIONS, render_application, validate_content, estimated_application_words
from scripts.audit_ra import audit, sensitivity


def fixture_content(facts):
    return {section:[{'id':e['id'],'title':'Recorded computational work','bullets':[{'domain':domain,'text':'Completed the recorded computational tasks within the stated scope and documented the specified work using the supplied materials.'} for domain in ('programming','nlp','data_analysis') if domain in e['technical_evidence']]} for e in facts[source]] for section,source in (('projects','projects'),('research','research_experience'))}


class FakeAPI:
    def __init__(self,reject_first=False,incomplete=False):
        self.calls,self.requests,self.seen=0,[],set()
        self.reject_first,self.incomplete=reject_first,incomplete
        self.lock=Lock()

    def create(self,body):
        with self.lock:
            self.calls+=1;self.requests.append(body)
            facts=json.loads(body['input'][1]['content'])['fixed_record']
            if body['text']['format']['name']=='ra_factual_review':
                reject=self.reject_first and facts['applicant_id'] not in self.seen
                self.seen.add(facts['applicant_id'])
                content={'passes':not reject,'issues':['Fixture unsupported claim'] if reject else []}
            else: content=fixture_content(facts)
            return {'id':f'test-{self.calls}','status':'incomplete' if self.incomplete else 'completed','model':'test-only-model','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(content)}]}],'usage':{'input_tokens':100,'output_tokens':100,'total_tokens':200}}


class RAPlanTests(unittest.TestCase):
    def test_shared_system_template(self):
        from ta_applicants.plan import SYSTEM_TEMPLATE
        self.assertEqual(plan.SYSTEM_TEMPLATE,SYSTEM_TEMPLATE)

    def test_untreated_inputs_and_explicit_condition(self):
        base=plan.assessment_messages('Applicant record','the RA Committee')
        condition='Academic integrity record: No allegations or findings.'
        treated=plan.assessment_messages('Applicant record','the RA Committee',integrity_text=condition)
        self.assertEqual(base[0],treated[0]);self.assertNotIn('ACADEMIC INTEGRITY RECORD',base[1]['content'])
        self.assertEqual(base[1]['content'],treated[1]['content'].replace('\n\nACADEMIC INTEGRITY RECORD\n'+condition,''))
        for application,committee in [('', 'Committee'),('record',''),('record','{{committee_name}}')]:
            with self.assertRaises(ValueError):plan.assessment_messages(application,committee)


class RAEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=read_json(PROJECT/'configs/ra.json');cls.pool=make_pool(cls.config);cls.rows=select_allocated(cls.pool,cls.config)

    def test_confirmed_counts_and_mixed_population(self):
        report=summarize(self.rows)
        self.assertEqual(report['n'],100);self.assertEqual(report['tiers'],{'weak':30,'borderline':40,'strong':30})
        self.assertEqual(report['designated_mixed']['none'],90)
        self.assertEqual(report['unique_portfolios'],100)
        for cell in self.config['mixed_allocation']:
            group=[r for r in self.rows if r['designated_mixed_pattern']==cell['pattern']]
            self.assertEqual(len(group),cell['count']);self.assertTrue(all(r['strength']==cell['tier'] and cell['pattern'] in r['rubric']['mixed_tags'] for r in group))
        for r in self.rows:self.assertIn(r['facts']['education'][-1]['degree'],{'MS in Computer Science','PhD in Computer Science'})

    def test_full_pool_validity_and_label_consistency(self):
        for r in self.pool:
            self.assertEqual(validate_facts(r['facts'],self.config),[],r['profile_id'])
            self.assertEqual(evaluate(r['facts'],self.config),r['rubric'])

    def test_reproducible_without_api(self):
        with patch('phd_resumes.api.OpenAIResponses.create') as api:
            self.assertEqual(make_pool(self.config),self.pool)
            self.assertEqual(select_allocated(self.pool,self.config),self.rows)
        api.assert_not_called()

    def test_tiers_independent_of_pool_and_allocation(self):
        changed=copy.deepcopy(self.config);changed.update(pool_per_seed=1,allocation={t:1 for t in ('weak','borderline','strong')})
        for r in self.rows:self.assertEqual(evaluate(r['facts'],changed),r['rubric'])

    def test_invalid_facts_fail_closed(self):
        original=next(r['facts'] for r in self.rows if r['facts']['research_experience'])
        mutations=[lambda f:f.pop('work_evidence'),lambda f:f['research_experience'][0].update(months=99),lambda f:f['work_evidence']['teamwork'].update(source_id='missing'),lambda f:f['education'][1].update(start='2000-01'),lambda f:f.update(undergraduate_gpa=4.1),lambda f:f['technical_skills'].append('Unsupported language'),lambda f:f['projects'][0]['technical_evidence']['programming']['tasks'].append('Invented publication'),lambda f:f['projects'][0].update(end='2026-10')]
        for change in mutations:
            f=copy.deepcopy(original);change(f);self.assertEqual(evaluate(f,self.config)['tier'],'unrated')

    def test_gpa_contradiction_rejected(self):
        f=copy.deepcopy(self.rows[0]['facts'])
        for c in f['coursework']:c['grade']='C'
        f['undergraduate_gpa']=4.0
        self.assertTrue(validate_facts(f,self.config))

    def test_canonical_technical_bundles_and_support(self):
        for family in FAMILIES:
            original=next(r['facts'] for r in self.pool if r['facts']['projects'][0]['family']==family)
            for domain in original['projects'][0]['technical_evidence']:
                for level in range(3):
                    f=copy.deepcopy(original);e=f['projects'][0]
                    e['technical_evidence'][domain]=copy.deepcopy(technical_bundle(domain,family,level))
                    e['implementation_support']=implementation_support(e['technical_evidence'])
                    f['technical_skills']=sorted({t for entry in f['projects']+f['research_experience'] for b in entry['technical_evidence'].values() for t in b['tools']})
                    self.assertEqual(validate_facts(f,self.config),[])
                    if e['implementation_support']:
                        e['implementation_support']=None;self.assertTrue(validate_facts(f,self.config))

    def test_first_time_ra_and_nlp_gap(self):
        self.assertTrue(any(r['strength']=='strong' and not r['facts']['research_experience'] for r in self.rows))
        gaps=[r for r in self.rows if r['designated_mixed_pattern']=='strong_programming_limited_nlp']
        for r in gaps:
            self.assertEqual(r['rubric']['dimensions']['programming'],2);self.assertEqual(r['rubric']['dimensions']['nlp'],0)
            self.assertEqual(r['strength'],'borderline')

    def test_all_dimensions_have_nonpromoting_sensitivity(self):
        results=sensitivity(self.rows)
        for field,result in results.items():
            self.assertGreater(sum(result['dimension_changes'].values()),0,field)
            self.assertGreater(result['tier_changes'],0,field)
            for change in result['changes']:
                self.assertLess(('weak','borderline','strong').index(change['after']),('weak','borderline','strong').index(change['before']))

    def test_recent_poor_grades_preclude_strong(self):
        for row in self.rows:
            f=copy.deepcopy(row['facts'])
            for c in f['coursework']:
                if c['level']=='graduate':c['grade']='C'
            self.assertNotEqual(evaluate(f,self.config)['tier'],'strong')

    def test_separate_interest_and_work_draws_preserve_technical_facts(self):
        changed=copy.deepcopy(self.config);changed['interest_probabilities']=[1,0,0];changed['work_level_probabilities']=[1,0,0]
        for i in range(30):
            a,_=make_facts(self.config,123,i);b,_=make_facts(changed,123,i)
            for field in ('education','coursework','projects','research_experience','technical_skills'):self.assertEqual(a[field],b[field])

    def test_varied_histories_and_length_balance(self):
        report=summarize(self.rows)
        self.assertEqual(len(report['project_roles']),4);self.assertEqual(len(report['research_counts']),3)
        self.assertEqual(len(report['work_families']),6);self.assertEqual(len(report['work_observation_sources']),2)
        means=[sum(estimated_application_words(r['facts']) for r in self.rows if r['strength']==t)/n for t,n in self.config['allocation'].items()]
        self.assertLessEqual(max(means)/min(means),self.config['maximum_estimated_tier_mean_ratio'])

    def test_invalid_probabilities_and_insufficient_coverage_stop(self):
        changed=copy.deepcopy(self.config);changed['work_level_probabilities']=[1,1,1]
        with self.assertRaises(ValueError):check_config(changed)
        with self.assertRaisesRegex(ValueError,'Insufficient coverage'):select_allocated(self.pool[:2],self.config)

    def test_rendering_all_evidence_without_researcher_metadata(self):
        for r in self.rows:
            f=r['facts'];text=render_application(f,fixture_content(f))
            for e in f['projects']+f['research_experience']:
                for b in e['technical_evidence'].values():self.assertIn(b['artifact'],text)
                if e['implementation_support']:self.assertIn(e['implementation_support'],text)
            for obs in f['work_evidence'].values():self.assertIn(obs['observation'],text)
            self.assertIn(f['research_interest']['statement'],text)
            for forbidden in ('rubric_hash','designated_mixed_pattern','latent_academic','PROPOSED RESEARCH','BROADER IMPACTS','ACADEMIC INTEGRITY RECORD'):self.assertNotIn(forbidden,text)
            f2=json.loads(json.dumps(f,sort_keys=True));self.assertEqual(render_application(f2,fixture_content(f2)),text)

    def test_model_content_fields_and_forbidden_claims(self):
        f=self.rows[0]['facts']
        for title in ('An honest applicant','Published findings','Improved by 50 percent','A strong applicant'):
            c=fixture_content(f);c['projects'][0]['title']=title;self.assertTrue(validate_content(f,c))
        c=fixture_content(f);c['projects'][0]['bullets'].pop();self.assertTrue(validate_content(f,c))
        c=fixture_content(f);c['research'].append(c['projects'][0]);self.assertTrue(validate_content(f,c))

    def test_sql_and_dataframe_routes_are_equivalent(self):
        for row in self.rows:
            original=row['facts']; baseline=evaluate(original,self.config)
            for variant in ('sql','dataframe'):
                f=copy.deepcopy(original)
                for e in f['projects']+f['research_experience']:
                    from ra_applicants.catalog import technical_level
                    level=technical_level('data_analysis',e['family'],e['technical_evidence']['data_analysis'])
                    e['technical_evidence']['data_analysis']=copy.deepcopy(technical_bundle('data_analysis',e['family'],level,variant))
                    e['implementation_support']=implementation_support(e['technical_evidence'])
                f['technical_skills']=sorted({t for e in f['projects']+f['research_experience'] for v in e['technical_evidence'].values() for t in v['tools']})
                result=evaluate(f,self.config)
                self.assertEqual(result['tier'],baseline['tier'])
                self.assertEqual(result['dimensions'],baseline['dimensions'])
        strong=[r for r in self.rows if r['strength']=='strong']
        self.assertTrue(any('SQL' not in r['facts']['technical_skills'] for r in strong))
        self.assertTrue(any('SQL' in r['facts']['technical_skills'] for r in strong))

    def test_duplicate_work_rejected_across_family_names(self):
        original=next(r for r in self.pool if len(r['facts']['projects'])==2 and r['facts']['projects'][0]['family']=='visual_reporting' and r['facts']['projects'][1]['family']=='data_integration')
        f=copy.deepcopy(original['facts']);a,b=f['projects']
        for key in ('input_context','provided_materials','technical_evidence','implementation_support'):b[key]=copy.deepcopy(a[key])
        self.assertEqual(work_signature(a),work_signature(b))
        self.assertTrue(any('Duplicate substantive work' in e for e in validate_facts(f,self.config)))
        before=portfolio_signature({'facts':f});a['family']='data_integration'
        self.assertEqual(before,portfolio_signature({'facts':f}))

    def test_varied_courses_and_explicit_nlp_practice(self):
        report=summarize(self.rows)
        self.assertGreater(report['course_area_sets'],10)
        self.assertGreater(report['course_title_sets'],30)
        self.assertGreater(len(report['graduate_course_dates']),1)
        self.assertGreater(report['no_nlp_course'],0)
        self.assertGreater(report['nlp_course_assessments']['practical'],0)
        self.assertGreater(report['nlp_course_assessments']['written'],0)
        for r in self.rows:
            f=r['facts'];text=render_application(f,fixture_content(f))
            for c in f['coursework']:
                if c['area']=='nlp':self.assertIn(c['assessment'],text)
                if c['practical_source_id']:
                    e=next(e for e in f['projects'] if e['id']==c['practical_source_id'])
                    self.assertIn('nlp',e['technical_evidence'])
                    self.assertLessEqual(e['end'],c['date'])
                    self.assertIn('Practical evidence:',text)

    def test_practical_course_cannot_invent_project_or_predate_completion(self):
        original=next(r['facts'] for r in self.rows if any(c['practical_source_id'] for c in r['facts']['coursework']))
        for change in ('bad_link','bad_date','unlinked_practical'):
            f=copy.deepcopy(original);c=next(c for c in f['coursework'] if c['practical_source_id'])
            if change=='bad_link':c['practical_source_id']='missing'
            elif change=='bad_date':c['date']='2020-01'
            else:c['practical_source_id']=None
            self.assertTrue(validate_facts(f,self.config),change)

    def test_model_receives_only_fixed_facts(self):
        f=self.rows[0]['facts'];body=body_for(self.config,GENERATOR_INSTRUCTIONS,{'fixed_record':f})
        self.assertEqual(json.loads(body['input'][1]['content']),{'fixed_record':f});self.assertFalse(body['store'])
        self.assertNotEqual(body['input'][0]['content'],plan.SYSTEM_TEMPLATE)

    def test_publication_metadata_is_not_a_publication_credential(self):
        f=next(r['facts'] for r in self.pool if 'publication metadata' in r['facts']['projects'][0]['input_context'])
        c=fixture_content(f)
        c['projects'][0]['bullets'][0]['text']='Parsed the provided news records and checked their publication metadata within the recorded supervised project scope.'
        self.assertEqual(validate_content(f,c),[])
        c['projects'][0]['bullets'][0]['text']+=' This led to a publication.'
        self.assertTrue(validate_content(f,c))
        other=next(r['facts'] for r in self.pool if 'publication metadata' not in r['facts']['projects'][0]['input_context'])
        c=fixture_content(other)
        c['projects'][0]['bullets'][0]['text']='Parsed the provided news records and checked their publication metadata within the recorded supervised project scope.'
        self.assertTrue(validate_content(other,c))


class RAWorkflowTests(unittest.TestCase):
    def config(self):
        c = read_json(PROJECT/"configs/ra.json")
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
            reviews = [body for body in api.requests if body["text"]["format"]["name"] == "ra_factual_review"]
            self.assertTrue(all("WORK AND COMMUNICATION OBSERVATIONS" in json.loads(b["input"][1]["content"])["application_text"] for b in reviews))
            with self.assertRaises(ValueError): export(root,out)
            path = next((out/"applications").glob("*.txt")); path.write_text(path.read_text()+"Unrecorded award.")
            with self.assertRaisesRegex(ValueError,"checksum"): verify_export(out)
            c = read_json(root/"config.json"); c["selection_seed"] += 1; write_json(root/"config.json",c)
            with self.assertRaisesRegex(ValueError,"changed"): load_run(root)

    def test_separate_audit_detects_omitted_work_evidence(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            root,out = Path(d)/"run",Path(d)/"export"
            prepare(self.config(),root); generate(root,client=FakeAPI()); export(root,out)
            row = read_jsonl(out/"profiles.jsonl")[0]
            path = out/"applications"/(row["profile_id"]+".txt")
            value = row["facts"]["work_evidence"]["organization"]["observation"]
            path.write_text(path.read_text().replace(value,""))
            self.assertTrue(any("missing or unlinked" in error for error in audit(out)["errors"]))

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
                if body["text"]["format"]["name"] == "ra_factual_review":
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
