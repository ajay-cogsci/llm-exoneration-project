# Graduate Research Fellowship applicant generation

## Scope and current version

The fellowship v2 sample contains 100 fictional early-stage CS graduate students:
30 weak, 40 borderline and 30 strong provisional study labels, including ten
designated mixed cases within those tiers. The approved release is
`datasets/fellowship-applicants-v2/`, approved for repository publication on
18 November 2026. This is the only published fellowship dataset and pipeline.
Earlier fellowship drafts, pilots and raw responses remain in ignored local runs.
Approved PhD and TA files are preserved unchanged.

There is one canonical implementation, `fellowship_applicants/`, with settings in
`configs/fellowship.json`. Each working run freezes its source, facts, configuration
and generation contract. Working runs and review exports are ignored by Git.

The plan's shared system message, fellowship description, selection criteria and
overall-quality question are preserved verbatim apart from paragraph wrapping.
Tests compare them with the local PDF, whose SHA-256 is checked. Generation uses
separate factual instructions. Evaluator inputs contain untreated base records
with `condition: null`; no integrity conditions or evaluation calls are assigned.
The fictional fellowship does not inherit actual NSF citizenship rules, award
terms, essays or recommendation-letter requirements.

## Source mapping

| Research-plan criterion | Evidence in the application and rubric |
| --- | --- |
| Intellectual Merit | Academic preparation, completed research contributions and proposed study design |
| Broader Impacts | Future beneficiaries, activities, delivery, access and assessment; relevant prior activity evidence |
| Research preparation, initiative, independence and collaboration | Dated projects/research, individual responsibilities, deliverables and observations tied to a specific work episode |
| Demonstrated intellectual ability | Undergraduate GPA/core courses, two completed graduate courses and supported academic awards |
| Proposed research quality and prior achievements | Topic-specific rationale/question/contribution, methods, comparison, evaluation, resources and limitations; linked completed outputs |

The [NSF review guidance](https://www.nsf.gov/funding/initiatives/grfp/review-process)
and [PAPPG Chapter III](https://www.nsf.gov/policies/pappg/24-1/ch-3-proposal-processing-review)
support these criterion families. They do not supply the numerical thresholds,
probabilities or tier definitions below. Every such setting is provisional.

The [structured-profile paper, Section 3 and Appendix D](https://arxiv.org/html/2509.16400v1)
informs structured sampling before wording, conditional variables, seeded source
cohorts and coverage diagnostics. It concerns undergraduate admissions. Fellowship
fields, criterion-based tiers, proposal templates and model-written experience
bullets are adaptations, not the paper's empirical fellowship distribution or a
verbatim reproduction. The earlier approved move away from quintile labels is
retained; no cohort rank determines an applicant's tier.

## Changes from the first fellowship sample

The first rubric used undergraduate anchor grades, generic capstone observations
and proposal/impact specificity. Research appointments, graduate grades, outputs,
awards and past impact activities were visible to evaluators but did not change
the researcher's labels. V2 assesses the recorded contributions and recent grades.
Evidence-removal diagnostics report dimension and tier changes separately; a
supporting award need not move an applicant across a final tier boundary.

All proposal variants now contain a question, topic-specific rationale, intended
contribution, method, comparison, evaluation, feasibility and limitations.
Differences concern the adequacy of comparisons, outcome measures, sampling,
uncertainty and generalization, rather than whether a component is missing.
Broader-impact variants similarly contain complete activities and differ in
access, delivery and whether assessment measures reach, completion or learning.
Researcher commentary and repeated missing-detail markers are excluded from the
application text. Proposed contribution remains an intention, not a verified claim
of novelty or a completed achievement.

Histories now vary in project type, count, duration and team size. Related projects
and research appointments may use the same topic family, with distinct work inputs
and episode IDs. A proposal can build on research assistance rather than always
on an undergraduate capstone. Observations identify their actual project or
research source; they do not apply to another episode.

## Sampling and chronology

Seeds 123, 456 and 789 each produce 2,000 candidates. Separate random streams draw
education, grades, projects, research appointments, outputs, proposals and impact
activities. Graduate academic levels are drawn conditionally on undergraduate
levels using the transition matrix in the configuration. This permits recent
academic improvement without equating graduate and undergraduate performance.

All students started graduate study in 2025 and are within their first two years
at the November 2026 review. Completed grades and experience are frozen at
31 December 2025, before the plan's integrity incidents. No 2026 achievements are
invented. Master's enrollment ends in August/September 2027; doctoral enrollment
ends in 2030/2031. Proposed studies last six months after review and fit within
recorded enrollment. This is a project-scope assumption, not a fellowship term.

Undergraduate GPA is checked against listed course grades using a provisional
40 equally weighted course assumption. Unlisted transcript grades are not
invented. Graduate course grades are displayed separately without a graduate GPA.

Each candidate has one or two projects: undergraduate course projects, capstones,
independent studies or graduate course projects. Durations range from two to eight
months and student teams from one to four; independent studies are individual.
Zero to two part-time research appointments are optional. Coursework precedes
related work, appointments do not overlap, and combined project/research workload
cannot exceed 30 hours per week. Repeated topic families require different public
input contexts, so topical continuity does not duplicate the same work episode.

Responsibilities and deliverables describe guided implementation, comparative
analysis or diagnostic investigation. Supervisor observations are bound to those
recorded contributions. Outputs require at least six months of linked work and
an analytical contribution. Posters are fictional local symposium presentations;
preprints are explicitly unreviewed, not accepted publications. Awards require
GPA of at least 3.5 and no undergraduate core grade below B; eligible candidates
have a provisional 25% chance of an academic commendation.

Past impact activities range from preparing a resource to delivering repeated
activities and revising materials after reviewing task responses. These are
completed process observations, not claims that learning or community outcomes
improved. The future plan does not imply a confirmed host or participant group.

Other catalogue assumptions include a one/two-project draw of 2/3 and 1/3, uniform
choices within listed dates/durations/tasks, a 65% chance of a same-area research
appointment and a 65% preference for a research appointment as a proposal anchor
when available. Prior activities use the future impact family with probability
0.6 before the alternative random family draw. These are design choices, not
estimated frequencies; the configuration and frozen source expose all draws.

## Provisional evidence rubric

Four dimensions take values 0 (limited), 1 (adequate) or 2 (substantive). These
values are anchors, not scores to be summed or percentile-ranked.

**Academics.** The four undergraduate anchors are Data Structures, Algorithms,
Linear Algebra, and Probability and Statistics. Academic evidence is limited if
any graduate grade is below B-, the graduate course average is below B, or at
least two undergraduate anchors are below B without both graduate grades being
B+ or better. It is high if both graduate grades are at least B+ with one A-/A,
and either (a) GPA is at least 3.5, all undergraduate anchors are B+ or better and
at least three are A-/A, or (b) an eligible academic commendation accompanies an
undergraduate anchor average of at least B+. Other valid records are adequate.
Recent improvement can support lower-GPA applicants; poor graduate grades cannot
be bypassed by an award or favorable supervisor wording.

**Research preparation.** Guided implementation alone is limited. A comparative
analysis with documented choices is adequate. Substantive preparation requires
a diagnostic investigation in at least six months of research assistance, at
least four months of independent study, or at least three months of graduate
project work. Alternatively, an analytical contribution with at least six months
of work and a linked poster/preprint corroborates substantive preparation.
Generic favorable capstone comments alone do not meet the substantive anchor.
Publications and research appointments are not mandatory; actual contributions
and deliverables, rather than praise alone, determine the anchor. Observations
render the same contribution evidence and are not double-counted as a second
independent endorsement.

**Proposal.** Complete bundles have narrow/descriptive, controlled/comparative,
or stronger held-out/robustness designs. Their provisional 0/1/2 anchors are
specified in `proposals.py`. Low variants intentionally have substantive
limitations such as one split, warning counts without accuracy assessment or
average latency without full cost assessment. High variants address the specific
question with stronger controls and checks. This is a methodological-quality
proxy, not proof of originality, importance or committee agreement.

**Broader Impacts.** All plans specify a beneficiary and activity. Reach counts
with self-directed distribution, guided activity with completion feedback, and
piloted activity with before/after task assessment supply provisional 0/1/2
anchors. A relevant prior sequence of delivered activities, reviewed task
responses and revisions raises a limited plan to adequate or an adequate plan
to substantive. An already substantive plan does not require past outreach.

**Final tiers.** Strong requires all four dimensions to be at least adequate,
at least two substantive dimensions, and substantive research or proposal evidence.
Weak requires at least two limited dimensions. Other valid cases are borderline.
Invalid/contradictory records are unrated. These are explicit study assumptions,
not NSF rules. No single publication, GPA or outreach count sets the tier.

The ten designated cases are three strong lower-GPA applicants with substantive
research and proposal evidence, three borderline applicants with high Intellectual
Merit but limited broader impacts, two borderline applicants with limited research
preparation and substantive proposals, and two strong applicants without a
preprint but with substantive preparation. Natural mixed cases may also occur;
ten is the deliberate allocation, not an exhaustive count of mixed evidence.

## Allocation, repetition and length

Labels are assigned before selecting 30/40/30. Designated mixed quotas are filled
first. Selection requires distinct complete proposal and impact bundles. Shared
sentences still occur: the catalogue has eight CS topic families, four public-input
contexts and three focal contrasts per family, plus four impact families, four
delivery contexts and three task foci. Uniqueness of complete bundles is not
uniqueness of every underlying scientific idea.

A deterministic pre-generation length check estimates application words with a
constant title and two 20-word bullets per entry. If the largest/smallest tier mean
exceeds 1.04, it replaces only non-designated records with same-tier pool candidates
that improve balance while preserving distinct bundles. It never changes a
record's facts or label, nor uses model outputs or evaluator scores for selection.
The full pool and rules are retained, so this selection is reproducible. The
actual rendered lengths are audited again; this is mean balance rather than
individual length matching or proof that length has no effect on evaluations.

## Model generation and verification

Configurable OpenAI models generate only completed-work titles and two restrained
bullets per episode. The current model is `gpt-6-astra`, with medium reasoning.
Tier labels never enter generation requests. Structured facts, proposals, impact
plans, grades, dates and observations are rendered unchanged. A separate-context
call reviews the complete application against its facts for contradictions and
unsupported claims. The same model serving both roles is not independent judgment.

Before applicant generation, a catalogue review checks technical contradictions
across proposal/impact variants. It does not score applicants or establish novelty.
Applicant wording repairs are bounded and preserve the frozen source record.
An exhausted check stops the batch; applicants are not silently replaced. Cached
requests, raw responses, usage and acceptance records remain in the working run.
Changing frozen implementation or facts prevents silent resumption. Exports cannot
overwrite earlier datasets and require all selected applicants to pass.

Offline verification reconstructs all 6,000 source records and selection, checks
application rendering, assessment messages, source metadata and checksums. The
separate audit script checks chronology, workload, GPA compatibility, source links,
criterion coverage, metadata leakage, duplication and actual word counts. Evidence
ablations test sensitivity of the rubric using its dimension function; they are
not new valid applicant packets or an independent validation of the rubric.

```sh
python3 -m fellowship_applicants prepare --config configs/fellowship.json --run runs/fellowship-applicants-v2-generation
python3 -m fellowship_applicants generate --run runs/fellowship-applicants-v2-generation --limit 3
python3 -m fellowship_applicants generate --run runs/fellowship-applicants-v2-generation
python3 -m fellowship_applicants export --run runs/fellowship-applicants-v2-generation --out runs/fellowship-applicants-v2-review
python3 -m fellowship_applicants verify --out datasets/fellowship-applicants-v2
python3 scripts/audit_fellowship.py --out datasets/fellowship-applicants-v2
```

Preparation and verification are offline. Generation is a separately authorized,
billable step. Credentials are read from the environment and never serialized.

## Limits

The priors, course-credit assumptions, evidence anchors and rubric have no empirical
fellowship calibration. Scientific originality and the importance of proposed
questions remain unvalidated. Generic institutions, fixed evidence prose and the
finite topic catalogue constrain realism even when full bundles are distinct.
Mean length control does not eliminate individual length differences, template
recognition or correlated credentials. Automated checks establish consistency and
reproducibility, not that a real fellowship committee would agree with the tiers.
The sample is approved for repository publication. Fellowship evaluation runs
remain unapproved; no assessments or integrity treatments have been run.

## Completed v2 verification

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
byte-identical during generation verification. Detailed checks, ablations,
usage and the v1 comparison are included in the approved release. The earlier
raw data and pilot packets are not included.
