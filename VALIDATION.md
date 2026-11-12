# Verification record

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
