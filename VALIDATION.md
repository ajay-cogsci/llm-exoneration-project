# Verification record

## Published update — 2026-11-12

The update contains 100 revised CVs, 300 recommendation summaries and 100
complete CV-plus-recommendation packets in the documented `datasets/` folders.
The existing historical sample is unchanged.

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
