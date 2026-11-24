# Data and Text Analysis Research Assistant applicants

100 fictional current CS graduate students, generated for the
research plan's Data and Text Analysis Research Assistant opportunity.
Version: ra-cs-graduate-v2.
Allocation: {'weak': 30, 'borderline': 40, 'strong': 30}; 10 designated mixed cases within these tiers.
This is the final RA v2 release, approved for repository publication on
18 November 2026. Earlier RA versions and pilots are excluded.
Applicant evaluation runs are not included in this approval.

## Contents

- `applications/`: CV-style records and source-linked work/communication evidence.
- `profiles.jsonl`: fixed facts, provisional tiers and sampling metadata.
- `evaluator_fields.jsonl`: facts without researcher labels or latent variables.
- `evaluator_inputs.jsonl`: exact shared system, RA opportunity and quality prompt;
  `condition: null` denotes untreated base input. No evaluations have been run.
- `generation/`: accepted work descriptions and factual-review status records.
- `config.json`, `generation_contract.json`, `source_map.json`: reproducible settings,
  model instructions, source mapping and provisional assumptions.
- `sampling_report.json`, `validation.json`, `checksums.json`: verification records.
- `index.html`: local research viewer; administrative labels appear only in the viewer.

The configurable model writes one short bullet per recorded technical domain in
each episode. Grades, dates, tools, work products, scope, source-linked observations
and research interest are rendered from frozen facts. All evidence used in the
rubric is available in the application. No publications, letters, research
proposals or broader-impact plans are required by this opportunity.

A strong first-time RA is possible from project work. Programming proficiency does
not substitute automatically for NLP experience. Communication, independence,
teamwork, organization and interest each have separate evidence. Designated mixed
profiles follow the allocation above; other applicants can naturally have uneven evidence too.

Version 2 offers SQL and pandas data-analysis routes with equivalent evidence
ratings. Duplicate-work checks compare actual inputs, materials, tasks, tools
and outputs regardless of category names. Academic records vary by subject,
title and plausible completed term; these are selected courses, not full transcripts.
NLP course assessment distinguishes written analysis from practical work linked
to an actual course-project entry. Grades alone do not create practical experience.

The plan supplies criteria, not numerical priors or hiring thresholds. These
rubric anchors and the graduate population are study choices. The source Penn
listing concerns undergraduates; the plan's adapted opportunity leaves degree
stage open, and the user selected graduate CS students. Neither actual employer
eligibility nor a minimum GPA is imposed.

Provisional labels are assigned before allocation, not from cohort quintiles.
Selection preserves distinct work portfolios and limits estimated mean length
imbalance across tiers to four percent before wording. Individual records and
actual rendered lengths still vary. Generic institutions, finite task templates
and synthetic supervisor observations limit realism. Structural and same-model
factual checks do not establish agreement with real hiring committees.

Model: gpt-6-astra; review model: gpt-6-astra.
Usage: 200 saved responses and
610117 reported tokens.
Raw API responses and unused candidate pools remain in the ignored working run.

Verify without model calls:

```sh
python3 -m ra_applicants verify --out data/ra
python3 scripts/audit_ra.py --out data/ra
```

Sources: the local research plan and its
[Penn textual-analysis RA listing](https://curf.upenn.edu/rd/research-assistant-textual-analysis).
The [structured-profile paper](https://arxiv.org/html/2509.16400v1) supplies the
sampling pattern; it does not provide RA distributions, this rubric or model
wording. This is an adaptation of that method, not an empirical RA calibration.

## Version 2 verification results

The sample contains 53 MS and 47 PhD students, with 30 weak, 40 borderline and
30 strong applicants and ten designated mixed profiles. All 100 applications
passed structural and separate-request model factual checks on the first attempt.
The full project suite passed 180 tests. Generation/review used 200 saved API
responses and 610,117 reported tokens. No committee evaluations were run.

The three requested corrections were checked directly:

- Fifteen of the thirty strong applicants have no SQL in their recorded skills.
  Across 200 SQL/dataframe substitutions at matched evidence levels, no rubric
  dimension or tier changed. This verifies tool equivalence in the implemented
  rubric; it is not a real hiring experiment.
- No applicant repeats an identical substantive work bundle. Duplicate checks
  use inputs, materials, tasks, tools and products, ignoring family names, roles
  and dates. Complete work portfolios are distinct across all 100 applicants.
- There are 86 subject combinations and 99 course-title sets. Graduate course
  completion dates span three terms. Thirty NLP courses link to completed
  practical projects; fifty describe written assessment without assessed coding.
  These are course counts, not applicant counts. The list is selected coursework,
  not a full transcript; grades alone do not create practical experience.

Mean application lengths are 678.4 words (weak), 690.2 (borderline) and 700.7
(strong), a largest/smallest ratio of 1.0329. Individual records range from 439
to 1,143 words. The viewer contains 100 cards and 101 verified local links.
All 3,650 protected files from the existing tracked project and RA v1 run/export
remained unchanged during generation verification. This release preserves the
reviewed application text, facts, prompts and generation records byte-for-byte.
Only publication documentation and release metadata were updated.

See [audit_report.json](audit_report.json) for full checks, criterion sensitivity
and inspected example IDs. Priors, rubric thresholds, course comparability and
same-model factual review remain limitations. Shared templates remain intentional;
the checks establish reproducibility and internal consistency, not population
representativeness or agreement with real RA hiring decisions.

The canonical pipeline is `ra_applicants/`, configured by `configs/ra.json`.
See the [method documentation](../../docs/methods/ra.md) for the complete construction
and verification procedure. Drafts and raw generation runs remain excluded.
