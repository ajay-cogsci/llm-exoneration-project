# Graduate introductory CS TA applicants: version 2

## Scope preserved

The dataset contains 100 graduate applicants: 30 weak, 40 borderline and 30
strong under a provisional study rubric, including ten deliberately selected
mixed cases within those tiers. The role remains **Introductory Computer Science
Teaching Assistant**, as described in `LLM exoneration research plan.pdf`.

The shared assessment system message, opportunity description, selection
criteria and overall-quality prompt are reused unchanged from `ta_applicants/plan.py`.
Paragraph wrapping is normalized; only the committee placeholder is substituted.
No fellowship, RA or PhD-admissions criteria are imported into the TA rubric.
Applicant generation uses separate factual-writing instructions. This stage
creates application materials, not evaluator scores or integrity treatments.

Version 2 is the only approved TA dataset in the repository. It uses
`ta_applicants_v2/`, `configs/ta_v2.json`, and `datasets/ta-applicants-v2/`.
The unapproved version 1 applicant export has been removed. Shared TA code is
retained because version 2 imports its plan wording, schemas and utilities.
The PhD datasets remain unchanged. Future TA exports stay local until explicitly
approved for publication; other TA dataset directories are ignored by default.

## Response to the version 1 audit

| Finding | Version 2 change |
| --- | --- |
| No prior teaching automatically prevented a strong label | No history means no prior performance evidence. A strong novice is possible from preparation, communication and explicit interest in beginners. |
| Communication was sampled from teaching preparation | Communication has a separate random stream and its own joint written/oral distribution. Altering teaching-count probabilities leaves the same applicant's communication evidence unchanged. |
| Nearly identical underlying education, skills and projects | Varied degree histories and dates, individually drawn course grades, 1–3 projects from eight task families, and project-specific tools and scopes. |
| Inability to perform duties was folded into a borderline label | Availability is checked separately. All 100 selected applicants can perform all advertised duties; an unavailable input is outside the merit-tier sample. |
| Supporting judgments could be mistaken for CV facts alone | Applications clearly separate CV sections from supporting communication and teaching-performance evidence. Observations remain synthetic fixed-template inputs, not real reviews or LLM-inferred endorsements. |

These changes address the identified design problems. They do not establish
that the resulting profiles are representative of real graduate TA applicants.

## Criteria and application fields

| Plan criterion | Evidence supplied |
| --- | --- |
| Foundational CS/programming knowledge | Completed relevant courses and grades, programming skills, source-linked course projects |
| Written and oral communication | Separate instructor observations linked to a particular project's report or presentation |
| Interest in teaching beginning programmers | A fixed applicant-stated interest description |
| Prior teaching/tutoring/TA experience and satisfactory performance | Role, assigned duties, topic, term dates, weekly hours and role-linked supervisor feedback; explicitly none when absent |
| Availability for required duties | Availability for lab/discussion sections, office hours, grading/feedback and administration |

The plan does not prescribe a final applicant format. These are short application
profiles with supporting evidence, not ordinary CVs alone. Synthetic instructor
observations and performance feedback are an explicit operationalization of its
criteria. There are no added recommendation letters or essays. The fixed wording
templates control variation in those observations; they do not validate their
frequency or eliminate possible wording effects.

## Rubric rules

All rules below are provisional study choices. The plan and the admissions paper
do not supply numeric TA thresholds, component weights or calibrated labels.
The evaluator does not see these labels or explanations.

**Availability:** all four advertised duty categories must be available for
inclusion in this sample. An unavailable record returns a separate availability
failure and an unrated merit tier. This concerns the advertised duties only;
it is not a certification of every institution-specific employment requirement.
The sample therefore does not study variation in availability.

**Technical preparation:** the grade anchors are Introduction to Programming,
Data Structures and Discrete Mathematics. High means all three at least B+ and
at least two A- or higher. Low means at least two below B. All other complete
cases are adequate. Additional course grades and projects remain visible to
evaluators but do not add points to these anchor labels. Undergraduate GPA is
descriptive and defines one mixed-case contrast; it does not set a tier.

**Communication:** written and oral observations are each needs-improvement,
satisfactory or effective in the structured record. Both effective gives the
effective communication category; either needs-improvement gives a concern;
otherwise evidence is satisfactory. The visible application uses fixed
observations rather than exposing these internal category codes.

**Prior performance:** no appointment gives `no_prior_evidence`, which is neutral.
For existing appointments, any needs-improvement feedback gives a concern; if
none raises a concern, any effective feedback gives effective performance;
otherwise performance is satisfactory. Duration is reported but does not gate
strong status. Treating any recorded performance concern conservatively remains
a study assumption; improvement over successive appointments is not separately
scored in this version.

For applicants meeting the availability condition:

1. Weak: both communication observations need improvement; or technical
   preparation is low without the combination of effective prior performance
   and no communication concern.
2. Strong: technical preparation is at least adequate, neither communication
   observation raises a concern, interest explicitly concerns beginning
   programmers, and prior performance has no concern. In addition, at least
   one of technical preparation, communication, or prior performance must be
   high/effective. A high-preparation first-time applicant can therefore be
   strong with satisfactory communication and explicit beginner interest.
3. Borderline: the remaining complete cases. General or undecided teaching
   interest does not establish the explicit beginner interest needed for strong.

Missing, malformed or contradictory records are unrated and cannot be silently
substituted for weak applicants. These labels are design strata, not validated
predictions of a committee's judgment or replacements for the study's outcomes.

## Structured generation

Three fixed seeds each generate 2,000 records. Applicant-specific random streams
separate education, academic preparation, projects, teaching history, performance,
communication and interest. No seed is searched for after seeing model outcomes.

- Academic preparation controls the distribution of each individual course
  grade, rather than selecting a whole fixed transcript. GPA ranges overlap.
  A declared 40 equally weighted undergraduate-course assumption bounds GPA
  against the listed grades; unlisted courses are not generated as credentials.
  This is a compatibility assumption, not an empirical transcript model.
- Graduate enrollment includes master's and doctoral students. Bachelor's
  subjects, start/end years, gaps before graduate study and expected completion
  vary. Generic institutional names stay fixed to avoid introducing prestige
  differences. Graduate degrees remain in CS in this version.
- Projects cover record processing, data structures, graph algorithms, software
  testing, databases, browser interfaces, systems programming and discrete
  mathematics. Each has its own tasks, tools, course, date and individual/team
  scope. Some are graduate course projects. Team-project wording is restricted
  to the applicant's recorded contribution.
- Teaching history is 0–2 appointments, drawn independently of communication.
  Terms are sampled after the introductory course, within an enrolled degree
  period, and before the record snapshot, with no overlap. This construction
  restricts its university appointments to enrolled students; it does not claim
  that all possible tutoring work requires enrollment. Topics and assigned tasks vary within role-specific
  catalogues. Performance categories are drawn separately from duration.
- Communication comes from its own nine-cell written/oral joint distribution.
  Written and oral observations may correlate with each other, but there is no
  teaching-history input to their draw. This independence is an experimental
  construction choice, not a claim about real applicants. Tier quotas and mixed
  selection can still induce associations in the selected sample; diagnostics
  report both the full pool and selected sample.
- Academic and experience evidence is frozen at 2025-12-31, before the plan's
  2026 integrity treatments. Graduate enrollment continues through the November
  2026 review. This historical snapshot is explicit; the profiles do not claim
  to report every subsequent achievement or graduate grade.

All probability tables, grade anchors, counts and thresholds are in the config.
The original semi-synthetic admissions literature motivates structured sampling;
it does not provide these TA parameter values. No empirical population fit is
claimed.

## Selection and ten designated mixed cases

Labels are assigned from facts before selection. The four deliberate contrasts
are three strong first-time TAs, three borderline applicants with technical grade
gaps and effective teaching evidence, two strong applicants with GPA below 3.30
and effective teaching evidence, and two borderline applicants with high technical
preparation and one communication concern.

The selector reserves these ten cases, then fills the remaining tier quotas from
the pool without replacement. The final counts remain 30/40/30. Only those ten
receive a designated-mixed flag. Other applicants may naturally exhibit the same
or other uneven combinations; designation does not pretend that the remaining
ninety are uniform. Selection changes neither facts nor rubric judgments.

## Model calls and verification

GPT-6 Astra at medium reasoning effort writes only titles and two 12–30 word
bullets per experience/project. Fixed facts, their hashes and the full prompt
contract are saved before calls. Model inputs contain no tier, mixed-case
designation or latent academic level. Dates, grades, degrees, tools, feedback,
interest and availability are rendered directly from the source record.

A separate model context checks wording fidelity. At most two wording repairs
are allowed; failed outputs are not exported and no applicant is quietly replaced.
Cached calls support resume, three workers bound concurrency, and a run-level
`STOP` file prevents subsequent calls after the next check. API keys never enter
the saved requests. Raw responses and code snapshots remain in the local run.

```sh
python3 -m ta_applicants_v2 prepare --run runs/ta-applicants-v2-final
python3 -m ta_applicants_v2 generate --run runs/ta-applicants-v2-final --limit 3
python3 -m ta_applicants_v2 generate --run runs/ta-applicants-v2-final
python3 -m ta_applicants_v2 export --run runs/ta-applicants-v2-final --out datasets/ta-applicants-v2
python3 -m ta_applicants_v2 verify --out datasets/ta-applicants-v2
```

Only `generate` makes model calls. Tests include counterfactual changes to
teaching and communication distributions to check their separation, strong
novice cases, availability failures, chronology, GPA compatibility, unchanged
facts through repairs, failed-export rejection and caching. Export verification
reproduces the pool and selection and checks every file, rendered application,
plan message and saved diagnostic. A separate audit checks the requested
properties directly from the approved records and compares prompt files with the
source plan wording. It needs no older dataset; an optional `--previous` path can
be used for a local comparison.

Same-model factual checking is not independent human review. The remaining finite
task catalogue, generic institutions, synthetic feedback, simplified course/grade
model and chosen thresholds still limit realism. Neither passing tests nor more
varied profiles establish hiring validity or absence of evaluator bias.
