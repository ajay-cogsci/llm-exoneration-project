# Graduate Research Fellowship applicants

100 fictional early-stage CS graduate applicants.
Study allocation: {'weak': 30, 'borderline': 40, 'strong': 30}. Mixed-case allocation:
[{'tier': 'strong', 'pattern': 'lower_gpa_substantive_research', 'count': 3}, {'tier': 'borderline', 'pattern': 'intellectual_merit_impact_gap', 'count': 3}, {'tier': 'borderline', 'pattern': 'limited_preparation_promising_proposal', 'count': 2}, {'tier': 'strong', 'pattern': 'no_publication_substantive_potential', 'count': 2}].

This is the final fellowship v2 release, approved for repository publication on
18 November 2026. Earlier fellowship versions and pilots are excluded.
Fellowship evaluation runs are not included in this approval.
The fellowship is fictional. Actual NSF eligibility, award amounts, award duration,
reference-letter requirements and essay formats are not imposed.

## Contents

- `applications/`: complete CV-style records, supervisor observations, structured
  research proposals and broader-impact plans.
- `profiles.jsonl`: source facts plus provisional tier and sampling metadata.
- `evaluator_fields.jsonl`: facts without tier or sampling metadata.
- `evaluator_inputs.jsonl`: exact shared system and fellowship opportunity wording
  with the overall-quality question. `condition: null` means untreated base input,
  not an assigned clean-record treatment. No evaluation calls were made.
- `generation/`: accepted experience wording and separate-context factual checks.
- `config.json`, `source_map.json`, `generation_contract.json`: assumptions,
  parameters and frozen generation instructions.
- `sampling_report.json`, `validation.json`, `checksums.json`: diagnostic and
  reproducibility records. `index.html` is a local review viewer.

The underlying facts, proposal components and impact-plan components are generated
before wording. Models paraphrase only completed project/research tasks. The
fixed renderer preserves grades, chronology, outputs, observations and all
proposal/impact components. Proposed results are never counted as achievements.

Tiers use provisional academic, completed-research, proposal and broader-impact
rules. They are assigned before allocation and do not depend on cohort percentiles.
Neither publications nor past outreach is required for a strong tier. Ten mixed
cases are deliberately selected; other naturally mixed records may also appear.
Complete proposal and impact bundles are distinct. Non-designated candidates may
be replaced by same-tier pool candidates before wording to keep estimated tier
mean lengths within 4%; no model outcomes enter selection. Actual lengths and
evidence-removal sensitivity are reported in the audit.

The numerical distributions, course-credit assumption, fixed templates and rubric
are study choices, not NSF thresholds or measured fellowship-population estimates.
There are eight CS topic families, four impact-plan families, generic institutions
and a finite catalogue of varied project and research episodes. Full proposal and
impact bundles are unique in the selected sample, but shared template components
remain. This bounds realism and diversity.
Supervisor observations are synthetic application evidence, not real letters.
Automated checks cannot validate whether a real selection committee would agree
with these tiers. This export has not received independent human validation.

Model usage: 200 saved responses;
535934 reported tokens.
Generation model: gpt-6-astra.
Factual review model: gpt-6-astra.
A separate call to the same model is a consistency check, not an independent judge.

Verify offline from the project root:

```sh
python3 -m fellowship_applicants verify --out data/fellowship
python3 scripts/audit_fellowship.py --out data/fellowship
```

The original structured-profile method is described in
[Nghiem et al., Section 3 and Appendix D](https://arxiv.org/html/2509.16400v1).
The paper addresses undergraduate admissions; fellowship criteria, rubric labels,
fixed proposal templates and optional model wording are adaptations.
The plan's source for fellowship criteria is the
[NSF review process](https://www.nsf.gov/funding/initiatives/grfp/review-process).

## Verification results

The final sample contains 64 MS and 36 PhD students, all early-stage CS graduate
applicants at the plan's review date. The allocation is 30 weak, 40 borderline,
30 strong, including ten designated mixed cases. The 6,000-candidate pool and final
selection reproduce offline. All 151 tests passed, all 100 applications passed
separate-context factual checks without repairs, and the independent structural
and rendering audit found no errors. The viewer has 100 cards and no broken local
links. The plan's system, opportunity and assessment wording are unchanged.

Actual mean word counts are 710.2 (weak), 711.0 (borderline) and 726.6 (strong), a
2.3% largest-to-smallest mean difference versus 12.3% in v1. Individual lengths
still range from 571 to 975 words. The new packets are longer overall because
contributions, deliverables and complete study rationales are explicit. There
are 100 distinct complete proposal bundles and 100 distinct impact bundles,
compared with 69 and 42 previously; shared sentences and themes remain.

| Evidence ablation | Dimension changes | Final tier changes |
| --- | ---: | ---: |
| Set both graduate grades to C | 74 academic ratings | 58 |
| Remove research appointments and their linked outputs | 19 research ratings | 9 |
| Remove posters/preprints | 17 research ratings | 5 |
| Remove academic awards | 3 academic ratings | 0 |
| Remove past broader-impact activities | 12 impact ratings | 5 |

These ablations show sensitivity of the implemented rules, not external validity.
Awards affect academic evidence but do not move a final tier in this particular
sample. A four-month independent study can meet the provisional substantive
research anchor when a diagnostic contribution and deliverable are recorded;
that threshold remains a study choice, not a verified fellowship standard.

The template review identified and resolved eight concrete issues, including
claims exceeding the proposed measurements, a full-suite execution-budget
contradiction and an unspecified downstream forecasting model. Its final round
reported no further contradictions. Reading the three-applicant pilot then
identified subject-verb agreement and unclear output references. Those wording
issues were corrected before freezing the final run; the superseded pilot remains
under ignored `runs/fellowship-debug/v2-pilot-wording-correction/`.

The final applicant run used 200 saved API responses and 535,934 reported tokens.
Including three catalogue-review calls and six responses from the superseded
pilot, v2 work used 209 saved responses and 585,614 reported tokens. No applicant
evaluation calls were made. The same configured model supplied generation and
factual review, so these are not independent committee judgments.

All 3,309 protected tracked files and earlier fellowship-run/export files remained
byte-identical during generation verification. The approved release preserves
the application text, facts, prompts and generation records from that verified
export. Only publication documentation and release metadata were updated.

Detailed records: [method](METHOD.md), [audit](audit_report.json),
[verification](verification_report.json), [usage](usage_report.json),
and [v1 comparison](comparison_with_v1.json).
