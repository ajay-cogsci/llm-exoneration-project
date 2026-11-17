# Introductory CS TA applicant generation

## Scope and plan fidelity

The source is `LLM exoneration research plan.pdf`, SHA-256
`7a40abe38b65d09c2a724c885d4f8e13ac8aa6015f68e58bdc5be723ad78d868`.
The TA opportunity description, selection criteria and shared assessment system
message are transcribed in `ta_applicants/plan.py`. An offline test checks their
words against the PDF. Paragraph wrapping is normalized. The only substitution
in the shared system message is its `committee_name` placeholder.

The authorized first sample contains **100 graduate students: 30 weak, 40
borderline and 30 strong**, with ten designated mixed profiles within those
tiers. Both master's and doctoral students are included. These are TA applicants;
doctoral enrollment does not make this a PhD-admissions dataset.

The shared system message is for evaluation. Applicant generation therefore uses
separate constrained instructions, as in the existing PhD pipeline. Exported
overall-quality assessment inputs preserve the plan's shared system message,
opportunity text and 0–100 rating prompt. They contain no integrity treatment;
absence of a condition is not a clean-record condition. This stage does not run
evaluations, assign an experimental condition, or select between the plan's
assessment tasks and optional rationale conditions.

## Evidence corresponding to each criterion

| Criterion in the plan | Observable application fields |
| --- | --- |
| Foundational CS and programming knowledge | Relevant undergraduate course grades, education, skills and a programming course project |
| Written and oral communication | Separate fixed course-instructor observations of the project's written report and oral presentation |
| Interest in teaching beginning programmers | A fixed applicant-stated interest description |
| Teaching, tutoring or TA experience, including satisfactory performance | Role, dates, months, weekly hours, recorded duties and fixed supervisor feedback for each experience |
| Availability for required duties | Explicit yes/no availability for lab/discussion sections, office hours, grading/feedback and administration |

The application text includes these short evidence sections because a CV alone
can omit communication, interest and availability. The statements and supervisor
observations are synthetic, assigned before wording. They are not recommendations
inferred by a model from a CV. Recommendation letters, essays, publications and
research credentials are not TA selection criteria in this plan and are not
added to this dataset.

## Provisional construction choices

The plan provides **no applicant distributions, correlations, GPA cutoffs or
strong/borderline/weak thresholds**. Every numerical choice in `configs/ta_v1.json`
is a provisional study design setting. None is attributed to the institutions
cited by the plan or treated as an empirical TA selection rule. The original
semi-synthetic admissions paper supplies a general structured-generation pattern;
it does not provide this TA schema or rubric.

Construction follows the revised PhD process: seeded structured pools, a fixed
criterion rubric, explicit allocation, constrained model wording and factual
checks. It does not reuse the original PhD composite-score quintiles.

- Three seeds create 2,000 records each. A five-level teaching preparation draw
  conditions a separate academic preparation draw through the saved matrix.
  The latent draws are generation controls, not labels or evaluator inputs.
- Academic levels determine a four-course grade pattern and a GPA range.
  Relevant coursework is Introduction to Programming, Data Structures, Discrete
  Mathematics and Computer Systems. These are study anchors, not prerequisites
  invented for the advertised position. GPA is descriptive, not a tier gate.
- Graduate pathway probabilities are 0.55 master's and 0.45 doctoral. The
  resulting selected sample need not preserve those proportions. Both pathways
  have a completed CS bachelor's degree and current graduate enrollment.
- Teaching months, communication observations and supervisor performance are
  conditional draws. Duration does not itself imply effective performance.
  Teaching intervals do not overlap; an empty list explicitly means no prior
  experience. Previous roles may predate graduate enrollment.
- Each applicant has one modest undergraduate programming course project, using
  Python and Git. Its report and presentation supply the source for the separate
  communication observations. These are not extra teaching appointments.
- Teaching interest has three explicit descriptions. Availability is drawn
  separately; full availability has probability 0.9, otherwise one duty is
  unavailable. No personal reason for unavailability is invented.
- Academic and experience records use the fixed 2025-12-31 snapshot, before
  the plan's 2026 integrity treatments. Graduate enrollment continues through
  the November 2026 review. Duty availability describes the advertised role.

All institutions and organisations are generic fictional entities. Identity
attributes and institutional prestige are not varied. The constrained course
patterns, restricted programming tools, small task catalogue, synthetic feedback
and conditional dependence between evidence fields limit realism and diversity.

## Rubric used before allocation

`evaluate(facts, config)` uses only visible factual evidence. Missing or invalid
evidence is **unrated**, not automatically weak.

Technical preparation is high when all four course grades are B+ or better and
at least two are A- or better; low when at least two are below B; otherwise
adequate. Overall GPA does not override the relevant-course evidence.

Teaching evidence is adequate when at least one experience is recorded and all
supervisor feedback is satisfactory or effective. It is high when those
conditions hold, total exposure is at least six calendar months and at least
one supervisor observation is effective. Otherwise the evidence is low. These
are evidence categories, not claims about innate ability or formal eligibility.
Months are exposure, not full-time-equivalent work or an effectiveness measure.

| Technical evidence | Low teaching evidence | Adequate teaching evidence | High teaching evidence |
| --- | --- | --- | --- |
| Low | weak | weak | borderline |
| Adequate | borderline | borderline | strong |
| High | borderline | strong | strong |

The provisional tier is capped at borderline if either communication observation
needs improvement, any required duty is unavailable, or interest in teaching
beginners is explicitly undecided. Low technical evidence combined with a
communication concern is weak. Availability is represented, not silently
assumed; a borderline label does not claim that an unavailable applicant could
actually satisfy the appointment's schedule.

Prior experience is not a formal eligibility requirement. This particular
conservative rubric places a well-prepared applicant with no prior teaching at
borderline. That is a study assumption open to substantive review, not a rule
stated in the plan. These labels are not model-generated hiring judgments.

## Allocation and mixed profiles

The sampler first labels the entire pool. Selection then takes the following
nonoverlapping cells; it never adjusts facts or labels to fill a quota.

| Tier | Designated pattern | Count |
| --- | --- | ---: |
| Weak | No designated mixed pattern | 30 |
| Borderline | No designated mixed pattern | 32 |
| Strong | No designated mixed pattern | 28 |
| Borderline | Technical course gaps with high teaching evidence and no communication concern | 3 |
| Borderline | High technical preparation with no teaching history, adequate communication and full availability | 3 |
| Strong | GPA below 3.30 with high teaching evidence and otherwise sufficient preparation | 2 |
| Borderline | High technical and teaching evidence, adequate communication, but incomplete availability | 2 |

The ten are **designated** contrasts. Other applicants can also have uneven
attributes. No claim is made that all remaining profiles are uniform or that
these quotas estimate real applicant frequencies. Patterns have an explicit
priority order in code to keep the selection cells disjoint.

## Model use, preservation and checks

The configurable default is GPT-6 Astra at medium reasoning effort, matching the
revised PhD sample. The model's documented support for Responses and structured
outputs was checked at
https://developers.openai.com/api/docs/models/gpt-6-astra.

The model receives the fixed facts, not research labels or latent levels. It
writes only short project/teaching titles and two 12–30 word bullets per entry.
All activities must come from the fixed task record. Grades, dates, role details,
supervisor feedback, communication observations, interest and availability are
rendered deterministically. A separate model context checks factual consistency;
it does not score merit or use the committee assessment prompt.

At most two wording repairs are allowed per applicant. Repairs preserve every
source fact and selected ID. Rejected material is not exported. Requests and
responses are cached in the ignored working run; repeated execution reuses
cached outputs. Three concurrent workers are permitted. A `STOP` file in the run
directory stops further calls at the next check. In-flight requests may finish.
No source credentials or API keys are written into the dataset.

Code, configuration, selected facts and generation instructions are hashed before
model calls. Changed contracts fail on resume. Public exports contain accepted
wording, model-check results and usage totals; full raw API responses remain in
the local working run. The viewer's labels are administrative annotations and
are absent from the application texts and evaluator messages.

## Commands

```sh
python3 -m ta_applicants prepare --run runs/ta-applicants-v1
python3 -m ta_applicants generate --run runs/ta-applicants-v1 --limit 3
python3 -m ta_applicants generate --run runs/ta-applicants-v1
python3 -m ta_applicants export --run runs/ta-applicants-v1 --out datasets/ta-applicants-v1
python3 -m ta_applicants verify --out datasets/ta-applicants-v1
```

Only `generate` makes model calls and requires `OPENAI_API_KEY`. Preparation and
export refuse existing output directories. `verify` reconstructs the pool and
selection, checks file hashes, source facts, labels, application rendering and
exact assessment messages without calling a model.

Automated checks establish internal consistency and reproducibility. They do not
establish agreement with real TA hiring judgments, empirically realistic feature
frequencies, or absence of stylistic influence. Same-model factual checking is not
independent human validation. No human validation is claimed for this new sample.
