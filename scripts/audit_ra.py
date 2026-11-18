"""Offline evidence, chronology, allocation and rubric sensitivity audit of RA exports."""

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ra_applicants.catalog import WORK_EVIDENCE, INTEREST, technical_bundle
from ra_applicants.plan import assessment_messages
from ra_applicants.sampling import evidence_dimensions, tier_from_dimensions
from ra_applicants.writing import estimated_application_words


def sensitivity(rows):
    report = {}
    interventions = ['academic', 'programming', 'nlp', 'data_analysis', *WORK_EVIDENCE, 'research_interest']
    for field in interventions:
        changed, dimensions = [], Counter()
        for row in rows:
            facts = deepcopy(row['facts'])
            before = evidence_dimensions(facts)
            if field == 'academic':
                for course in facts['coursework']:
                    if course['level'] == 'graduate': course['grade'] = 'C'
            elif field in ('programming', 'nlp', 'data_analysis'):
                for entry in facts['projects'] + facts['research_experience']:
                    if field in entry['technical_evidence']:
                        entry['technical_evidence'][field] = deepcopy(technical_bundle(field, entry['family'], 0))
            elif field in WORK_EVIDENCE:
                facts['work_evidence'][field]['observation'] = WORK_EVIDENCE[field][0]
            else:
                facts['research_interest']['statement'] = INTEREST[0]
            after = evidence_dimensions(facts)
            dimensions.update(k for k in before if before[k] != after[k])
            tier = tier_from_dimensions(after)
            if tier != row['strength']:
                changed.append({'profile_id': row['profile_id'], 'before': row['strength'], 'after': tier})
        report[field] = {'dimension_changes': dict(dimensions), 'tier_changes': len(changed), 'changes': changed}
    return report


def audit(root):
    root = Path(root)
    rows = [json.loads(line) for line in (root/'profiles.jsonl').read_text().splitlines()]
    config = json.loads((root/'config.json').read_text())
    packets = [json.loads(line) for line in (root/'evaluator_inputs.jsonl').read_text().splitlines()]
    errors, lengths, estimates = [], {t: [] for t in config['allocation']}, {t: [] for t in config['allocation']}
    def check(value, message):
        if not value: errors.append(message)
    def month(value):
        y, m = map(int, value.split('-')); return y*12+m
    points = {'C': 2, 'C+': 2.3, 'B-': 2.7, 'B': 3, 'B+': 3.3, 'A-': 3.7, 'A': 4}
    check(len(rows) == sum(config['allocation'].values()), 'Applicant count differs')
    check(dict(Counter(r['strength'] for r in rows)) == {k:v for k,v in config['allocation'].items() if v}, 'Tier allocation differs')
    check(len({r['profile_id'] for r in rows}) == len(rows), 'Duplicate applicant identities')
    check(len(packets) == len(rows) and len({p['profile_id'] for p in packets}) == len(rows), 'Evaluator input count differs')
    portfolio_signatures = set()
    for row in rows:
        pid, f = row['profile_id'], row['facts']
        text = (root/'applications'/(pid+'.txt')).read_text()
        content = json.loads((root/'generation'/(pid+'.content.json')).read_text())
        titles = {e['id']: e['title'] for section in content.values() for e in section}
        lengths[row['strength']].append(len(text.split()))
        estimates[row['strength']].append(estimated_application_words(f))
        undergrad, grad = f['education']
        check(grad['degree'] in {'MS in Computer Science', 'PhD in Computer Science'}, pid+': not a CS graduate')
        check(undergrad['end'] <= grad['start'] <= f['record_as_of'][:7] < f['review_month'] < grad['end'], pid+': education/snapshot chronology')
        check(grad['status'] == 'enrolled' and undergrad['status'] == 'completed', pid+': degree status')
        ug = [c for c in f['coursework'] if c['level'] == 'undergraduate']
        n = config['gpa_compatibility_course_count']
        remainder = n*f['undergraduate_gpa'] - sum(points[c['grade']] for c in ug)
        check(-.005*n <= remainder <= 4*(n-len(ug))+.005*n, pid+': GPA incompatible with courses')
        for c in f['coursework']:
            degree = grad if c['level'] == 'graduate' else undergrad
            check(degree['start'] <= c['date'] <= min(degree['end'], f['record_as_of'][:7]), pid+': course chronology')
            check(f"{c['course']}: {c['grade']} | {c['level']}, {c['date']}" in text, pid+': omitted course evidence')
        entries = f['projects'] + f['research_experience']; emap = {e['id']: e for e in entries}
        check(len(emap) == len(entries) and len({json.dumps({k:e[k] for k in ('input_context','provided_materials','technical_evidence')},sort_keys=True) for e in entries}) == len(entries), pid+': duplicate substantive work')
        portfolio_signatures.add(tuple(sorted(json.dumps({k:e[k] for k in ('input_context','provided_materials','technical_evidence')},sort_keys=True) for e in entries)))
        for c in f['coursework']:
            if c['area']=='nlp':
                check(c['assessment'] in text, pid+': missing NLP assessment mode')
                if c['practical_source_id']:
                    source=emap.get(c['practical_source_id'])
                    check(source is not None and 'nlp' in source['technical_evidence'] and source['role']==('Graduate course project' if c['level']=='graduate' else 'Undergraduate course project') and source['end']<=c['date'],pid+': invalid practical NLP course link')
                    if source:check("Practical evidence: '"+titles[source['id']]+"', listed below." in text,pid+': omitted practical NLP project attribution')
                else:check('no assessed coding component' in c['assessment'],pid+': theoretical NLP course implies unrecorded practice')
            else:check(c['practical_source_id'] is None,pid+': unexpected practical course link')
        skill_union = set()
        for e in entries:
            check(month(e['end'])-month(e['start']) == e['months'] > 0, pid+': duration mismatch')
            check(e['end'] <= f['record_as_of'][:7], pid+': completed work after snapshot')
            check(any(d['start'] <= e['start'] < e['end'] <= d['end'] for d in f['education']), pid+': work outside enrollment')
            for value in (e['input_context'],e['provided_materials'],e['scope'],titles[e['id']]): check(value in text,pid+': omitted source work')
            if e['implementation_support']: check(e['implementation_support'] in text, pid+': omitted implementation support')
            for domain, evidence in e['technical_evidence'].items():
                skill_union.update(evidence['tools'])
                check(evidence['artifact'] in text, pid+': omitted technical work product')
                check(all(tool in text for tool in evidence['tools']), pid+': omitted tools')
            check(e['communication_artifacts']['written'] in text and e['communication_artifacts']['oral'].lower() in text, pid+': omitted communication work')
        check(set(f['technical_skills']) == skill_union, pid+': unsupported skill')
        for m in range(month(undergrad['start']),month(f['record_as_of'][:7])):
            check(sum(e['hours_per_week'] for e in entries if month(e['start']) <= m < month(e['end'])) <= 30, pid+': excessive workload')
        for a,b in zip(f['research_experience'],f['research_experience'][1:]): check(a['end'] <= b['start'], pid+': overlapping appointments')
        for observation in f['work_evidence'].values():
            source = emap.get(observation['source_id'])
            check(source is not None and observation['observation'] in text, pid+': missing or unlinked work observation')
            if source:
                expected = f"{observation['source']} on '{titles[source['id']]}' ({source['start']} to {source['end']})"
                check(expected in text, pid+': source attribution omitted')
        check(f['research_interest']['statement'] in text, pid+': omitted research interest')
        for forbidden in ('rubric_hash','designated_mixed_pattern','latent_academic','Provisional study tier','ACADEMIC INTEGRITY RECORD','PROPOSED RESEARCH','BROADER IMPACTS','RECOMMENDATION LETTER'):
            check(forbidden not in text, pid+': researcher metadata, treatment or unrelated requirement leaked')
        check(not re.search(r'\b(strong applicant|weak applicant|borderline applicant)\b',text,re.I), pid+': tier leaked')
        packet = next((p for p in packets if p['profile_id']==pid), None)
        check(packet == {'profile_id':pid,'condition':None,'assessment':'overall_quality','messages':assessment_messages(text,config['committee_name'])}, pid+': evaluator packet differs')
        if row['strength']=='strong':
            check(all(points[c['grade']]>=2.7 for c in f['coursework'] if c['level']=='graduate'), pid+': poor recent grades in strong tier')
    mixed = Counter(r['designated_mixed_pattern'] for r in rows if r['designated_mixed_pattern']!='none')
    check(dict(mixed)=={c['pattern']:c['count'] for c in config['mixed_allocation'] if c['count']},'Mixed allocation differs')
    check(len(portfolio_signatures)==len(rows),'Repeated complete work portfolio')
    stats={t:{'min':min(v),'max':max(v),'mean':round(sum(v)/len(v),1)} for t,v in lengths.items() if v}
    means=[sum(v)/len(v) for v in lengths.values() if v]; estimates=[sum(v)/len(v) for v in estimates.values() if v]
    ratio=max(means)/min(means)
    check(max(estimates)/min(estimates)<=config['maximum_estimated_tier_mean_ratio'],'Pre-wording length imbalance')
    check(ratio<=config['maximum_estimated_tier_mean_ratio']+.04,'Rendered length imbalance exceeds tolerance')
    return {'applicants':len(rows),'tiers':dict(Counter(r['strength'] for r in rows)),'designated_mixed':dict(mixed),'errors':errors,'word_counts_by_tier':stats,'largest_to_smallest_tier_mean_ratio':round(ratio,4),'unique_portfolios':len(portfolio_signatures),'course_area_sets':len({tuple(sorted((c['level'],c['area']) for c in r['facts']['coursework'])) for r in rows}),'course_title_sets':len({tuple(sorted(c['course'] for c in r['facts']['coursework'])) for r in rows}),'graduate_course_dates':dict(Counter(c['date'] for r in rows for c in r['facts']['coursework'] if c['level']=='graduate')),'nlp_course_assessments':dict(Counter('practical' if c['practical_source_id'] else 'written' for r in rows for c in r['facts']['coursework'] if c['area']=='nlp')),'without_sql_by_tier':{t:sum(r['strength']==t and 'SQL' not in r['facts']['technical_skills'] for r in rows) for t in config['allocation']},'first_time_ra_by_tier':{t:sum(r['strength']==t and not r['facts']['research_experience'] for r in rows) for t in config['allocation']},'evidence_sensitivity':sensitivity(rows),'sensitivity_interpretation':'Each dimension is downgraded separately while other evidence stays fixed. These are rubric diagnostics, not new valid application records or external hiring validation. Sensitivity shares the rubric functions; chronology, coverage and workload checks above are separately implemented.','limitations':['Provisional priors, templates and rubric; no empirical RA hiring calibration.','Complete portfolios are unique, but task templates, institutions and observation wording repeat.','Evidence comes from projects and appointments completed before 2026; later work is intentionally absent.','Tier mean length balance does not eliminate individual length or writing-style effects.','Same-model factual review is not independent human validation.'],'api_calls':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--out',required=True)
    report=audit(parser.parse_args().out); print(json.dumps(report,indent=2)); raise SystemExit(bool(report['errors']))
