# Verification record

## Revised graduate TA dataset, version 2 — 2026-11-17

`datasets/ta-applicants-v2/` contains 100 graduate applicants: 30 weak, 40
borderline and 30 strong, including ten designated mixed profiles. There are
55 master's students and 45 doctoral students. The introductory CS TA role,
selection criteria and shared assessment messages remain those in the research
plan. Version 2 is the only approved TA dataset in the current repository.
The earlier PhD datasets remain unchanged.

The unapproved TA version 1 export was removed following the publication
correction. The standalone audit now checks the approved records and source plan
wording without an earlier dataset. Only the v2 README, audit report and their
checksums changed during cleanup; applicant facts, application texts, evaluator
inputs, generation records and provenance are unchanged. Other TA dataset
directories are ignored by default. Future publication requires explicit approval.
After removal, all 118 tests passed, including standalone auditing, rejection of
altered plan wording and the TA publication ignore policy. Export verification
passed for all 100 approved applications. Hash checks confirmed that all 1,554
protected approved TA and PhD files were unchanged.

The corrections address the construction problems found in the unapproved draft.
The following aggregate comparison records the earlier audit findings; the draft
applicant records are no longer included:

| Check | Version 1 | Version 2 |
| --- | ---: | ---: |
| Strong applicants with no teaching history | 0 | 6 |
| Communication concern among first-time applicants | 22/26 (84.6%) | 6/26 (23.1%) |
| Communication concern among experienced applicants | 15/74 (20.3%) | 21/74 (28.4%) |
| Applicants unavailable for a required duty | 6 | 0 |
| Distinct education histories | 2 | 74 |
| Distinct foundational-course grade patterns | 5 | 70 |
| Distinct skill sets | 1 | 25 |
| Distinct project task sets | 1 | 73 |

No prior teaching now means no prior performance evidence, rather than adverse
evidence. Separate random streams generate communication and teaching history.
Counterfactual tests change one distribution while checking that the same
applicants retain their draws from the other. Independence is a construction
choice; the selected sample's proportions are not population estimates.
Availability is handled separately from merit, with all selected applicants
available for the advertised duties. Fixed supporting observations are clearly
separated from CV sections in the application text.

### Generation and checks

- The frozen 6,000-record pool and selected 100 reproduce exactly. Selection
  keeps source facts unchanged. The ten designated mixed cases are three strong
  first-time applicants, three borderline applicants with technical gaps and
  effective teaching evidence, two strong applicants with lower GPA and effective
  teaching evidence, and two borderline applicants with high technical
  preparation and a communication concern. Other records can naturally have
  uneven strengths without being designated mixed cases.
- The full 100-test suite passed, including 19 version 2 tests. These cover the
  separation of evidence draws, strong novice cases, availability failures,
  chronology, GPA compatibility, unchanged facts through repairs, caching,
  rejected exports and tamper detection. Test API responses are simulated.
- GPT-6 Astra generated the production wording and checked fidelity in separate
  contexts. All 100 passed without a wording repair. There are 200 saved
  production responses reporting 311,247 tokens.
- Direct pilot inspection caught a university appointment during a gap between
  degree enrollments. The model check had not detected it because the prose
  matched the source facts. The sampler and validator were corrected to require
  university appointments within enrolled study periods. A fresh frozen run
  replaced that three-applicant pilot before full generation. The discarded
  pilot used six saved responses and 9,966 reported tokens; none of its wording
  was reused in the final dataset. Combined saved-response usage is 206
  responses and 321,213 tokens, not a billing estimate. The revision history
  retains this distinction.
- Export verification passed for all 100 applications: full file inventory and
  checksums, pool and sample reproduction, rubric labels, diagnostic summaries,
  deterministic rendering and assessment messages. The three plan prompt files
  are byte-identical to version 1. No integrity treatments or evaluations ran.
- `scripts/audit_ta_v2.py` independently reads exported records and texts without
  importing the sampler or renderer. Its checks passed for counts, graduate
  enrollment, availability, appointment periods, fixed evidence in text,
  designated mixed cases, assessment inputs and unchanged plan messages.
  Current results are saved in `audit.json`. The audit checks prompt files against
  the source wording and does not require the unapproved v1 export.
- Direct inspection covered all four designated mixed-case types and a graduate
  course project, including team-contribution wording. An additional keyword
  scan of all 578 generated bullets found none of its screened numeric or
  superlative claims; this limited scan is not a semantic proof of fidelity.
- The HTML viewer contains 100 applicant cards and 101 valid local links.
  Credential and attribution scans passed. Visual browser testing is not claimed.
- All 953 files in the earlier PhD/TA dataset and implementation preservation
  inventory retain their original hashes. The earlier dataset verifiers passed.
- Before publication, the TA update was integrated with current `main` at
  `ac2c596`, preserving the later PhD corrections, results and documentation.
  All 115 tests in the combined checkout passed. The TA export, separate audit
  and PhD dataset verifier passed, including identical reconstruction of the
  corrected PhD datasets. All 2,052 previously published dataset files retained
  their Git blob hashes. That initial publication also included the v1 baseline;
  the subsequent publication correction removes it and makes the audit standalone.

### Remaining limits

The finite task catalogue, generic institutions, synthetic instructor/supervisor
observations and provisional rubric remain deliberate simplifications. The
numeric assumptions are not calibrated against real TA hiring. The profile is
an explicit 2025-12-31 evidence snapshot for a 2026 review, not a complete current
CV. All applicants meet the availability condition, so this sample cannot test
availability effects. Applications are not matched for length: mean word counts
are 340.5 weak, 347.4 borderline and 372.0 strong. A separate-context check by the
same model and passing software tests do not establish independent human
agreement, empirical hiring validity or absence of wording effects. Full rules
and assumptions are documented in `TA_V2_METHOD.md`.

## Published update — 2026-11-12

The update contains 100 revised CVs, 300 recommendation summaries and 100
complete CV-plus-recommendation packets in the documented `datasets/` folders.
The existing historical sample is unchanged.

## Corrections — 2026-11-11

- **GPA consistency.** Nineteen version 2 CVs had a GPA more than 0.6 grade
  points from the mean of their four listed course grades. Their GPA was
  redrawn under `configs/phd_gpa_consistency_v1.json`. Verification confirms
  that no other field changed, that the other 81 CV files are byte-identical,
  and that all 100 CVs now satisfy the rule. One applicant moved from weak to
  borderline; the sample is 29/41/30.
- **Letter consistency.** Recommendation policy v2 gives zero probability to a
  limited letter on an A-range grade and a strong letter on a B-range grade.
  Eleven of 300 letters changed, all to moderate; the rest are identical.
- **Not rerun.** The model factual review was not repeated for the 19 changed
  GPA lines. The line is rendered by code and the reviewed prose does not
  mention GPA. Human review of CVs and letters is still pending.
- **Evaluation harness.** Fifteen added tests cover the corrections and
  `phd_eval`, including that conditions differ only in the record block, that
  no identifier or label reaches a prompt, reply parsing, and resumable runs.
  They use a simulated model. No real model has been called with these prompts.
- The suite now has 72 tests.

## Revised CV sample

- The pool contains 6,000 records across three seeds. Pool construction and the
  selected 100 applicants reproduce exactly from the saved configuration.
- Allocation is 30 weak, 40 borderline and 30 strong, including ten designated
  mixed profiles. Tiers follow a fixed academic/research rubric rather than
  cohort quintiles.
- GPT-6 Astra produced 91 first-pass acceptances. Nine CVs passed after one
  wording repair; fixed credentials and selected applicants were retained.
- There were 209 saved API responses with 288,504 reported tokens. These are
  saved-response usage totals, not a billing estimate.
- Accepted CVs passed chronology, field/count, wording and separate-context
  factual checks. Exported CV files are byte-identical to the retained revised run.

## Recommendation summaries

- Each applicant has three distinct fictional writers and the four specified
  letter fields. Summary bodies contain 30–100 words.
- Fixed templates and separate random streams determine endorsement and flags.
  Examples repeat accepted CV activities within each writer's linked role.
- Output contains 68 limited, 147 moderate and 85 strong recommendations, with
  148 comparisons and 97 specific examples. Grade-only letters do not have
  specific work examples.
- The stage made zero model calls. All 300 records pass relationship, observation
  period, example, flag, template and reproducibility checks.
- Complete-packet hashes support reuse of identical materials across conditions.

## Software and export checks

The 57-test suite covers the sampler, rubric, bounded generation/cache behavior
and recommendation constraints. Deliberately inconsistent supervision periods,
cross-writer examples, altered flags, rejected inputs and changed exports are
rejected. Tests use simulated API responses.

`python3 scripts/verify_datasets.py` checks the published file inventories and
SHA-256 hashes, reproduces the pool and selection, recomputes rubric labels,
checks all CVs and reproduces recommendation records and complete packets.
The HTML viewers have verified relative links and counts; visual browser testing
is not part of this release's validation evidence.

## Limits

Numeric PhD probabilities and tier boundaries are provisional. Recommendation
relationships and endorsements are synthetic judgments, not ranks inferred from
GPA. Publication/research coupling, generic institutions, restricted coursework
patterns and absent faculty-fit evidence remain limitations. The checks establish
internal consistency and reproducibility, not calibration against admissions
outcomes, independent human agreement, or neutrality of model decisions.
