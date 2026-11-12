# Recommendation summaries

Each PhD applicant has three short summaries, with a writer type, strength
level, comparison-to-other-students yes/no and specific-work-example yes/no.
The summaries use fill-in templates with source-linked facts.

The 2026-11-12 output is
[`datasets/phd-applications-v3-recommendations-v1/`](datasets/phd-applications-v3-recommendations-v1/index.html):
100 unchanged copies of the revised CVs, 300 summaries, and 100 complete
CV-plus-recommendation packets. Each summary is 30–100 words, excluding its
four field labels. No model calls were made for this stage.

**Policy v2 (2026-11-11).** `configs/phd_recommendations_v2.json` changes two
rows of the strength table below: a course grade of A− or better is 0 / 0.40 /
0.60 and a grade of B or B+ is 0.25 / 0.75 / 0. This removes letters that
contradict the grade they cite. The seed is unchanged, so 11 letters differ
from v1. The v2 output is
[`datasets/phd-applications-v4-recommendations-v2/`](datasets/phd-applications-v4-recommendations-v2/).
The rest of this document describes v1, which is otherwise identical.

## Usage

Python 3.10+ and the standard library are sufficient. The separate package leaves
the existing CV pipeline and its frozen generation contracts unchanged.

```sh
python3 -m phd_recommendations generate \
  --source datasets/phd-cvs-v2-rubric-v1 \
  --out NEW_DIRECTORY \
  --policy configs/phd_recommendations_v1.json

python3 scripts/verify_datasets.py
```

The input must be an accepted CV run with `profiles.jsonl`,
`resume_manifest.json`, accepted content/status files and rendered CVs. Generation
validates every source and every summary before exporting. Existing output
directories and outputs nested inside the source run are rejected. Repeating
`--applicant-id ID` creates a pilot subset; omission includes the whole source.
An applicant receives the same letters in a pilot and full run under one policy.

`applications/` contains the evaluator packets. Reuse the exact file for an
applicant across integrity conditions; do not regenerate a letter per condition.
Packet hashes are saved in `manifest.json`. This stage does not run evaluations.

## Provisional implementation settings

These choices are explicit in `configs/phd_recommendations_v1.json`. They are
provisional study choices, not frequencies or thresholds supplied by an admissions
source or the original semi-synthetic admissions paper.

- Letter strength uses **limited / moderate / strong**. These describe the
  letter's endorsement, independently of the existing CV tier. Limited means
  qualified support; it does not invent misconduct, bad character or a failure.
- Assign one writer to the longest research entry if present, one instructor to
  a seeded choice of graded course, and one instructor to the first recorded
  technical course project. Without research, fill the third position with the
  longest work entry. Missing sources fall back to distinct graded courses.
- The three fictional writer identities are distinct. Their relationships and
  endorsement/comparison judgments are synthetic additions, clearly recorded.
  A project instructor observes that course project; no link to a named graded
  course is invented. Unknown teaching dates/durations stay unspecified.
- A research/work writer's observation period equals the linked role's recorded
  period, not the applicant's total experience across other roles.
- Comparison presence is drawn with probability 0.5. Example presence is drawn
  with probability 0.5 only where an observed activity exists. Separate seeded
  streams control selection, strength, and the flags. No balancing quotas or
  independent effects of flags are claimed.
- A grade alone is not a specific work example. Grade-only letters always have
  that flag set to No. Examples in other letters quote exactly one accepted CV
  bullet from the writer's linked activity. No new accomplishment is generated.
- Comparisons use the same fixed below/at/above-typical templates for each
  strength level, with a writer-appropriate group of other students. These are
  assigned judgments, not ranks inferred from GPA. No numeric percentiles,
  best-ever claims or exceptional-case overrides are used in v1.

The strength assignment table is:

| Linked evidence | Limited | Moderate | Strong |
| --- | ---: | ---: | ---: |
| Research under 3 months | 0.65 | 0.35 | 0.00 |
| Longer research: assigned/routine tasks | 0.35 | 0.60 | 0.05 |
| Longer research: guided experimental design | 0.15 | 0.65 | 0.20 |
| Longer research: design/analysis or question/method leadership | 0.05 | 0.35 | 0.60 |
| Course grade A− or better | 0.05 | 0.35 | 0.60 |
| Course grade B or B+ | 0.25 | 0.60 | 0.15 |
| Course grade below B | 0.65 | 0.35 | 0.00 |
| Course project: baseline implementation | 0.35 | 0.60 | 0.05 |
| Course project: comparative implementation/evaluation | 0.15 | 0.60 | 0.25 |
| Employment role | 0.20 | 0.65 | 0.15 |

The short-research restriction is a conservative v1 choice implementing the
constraint against unsupported praise. It does not prevent that applicant
from receiving a strong course/project letter, and is not asserted to be a real
admissions rule. The four requested fields are visible in both JSON and text;
the applicant's CV tier is not shown in a letter or used to assign its strength.

## Validation and limits

Automated checks cover three distinct writers, source acceptance and hash checks,
observation periods, role-specific examples, exact templates, both Boolean fields,
reproducible assignments, exported packets, and unchanged source files. The
test suite includes deliberately invalid durations, cross-writer examples,
altered flags, rejected input CVs, tampered exports and forbidden output paths.
Full working runs retain implementation snapshots and reject code drift. The
published datasets have portable checksums and are verified with
`python3 scripts/verify_datasets.py`.

A nine-applicant pilot covered all flag combinations, no-research and one-month
cases, long research and GPA extremes. Its saved recommendation records match
the full run exactly. This is a reproducibility check rather than independent
validation of the strength distribution.

Observed output: 68 limited, 147 moderate and 85 strong letters; 148 contain an
explicit student comparison and 97 contain a concrete example. There are 95
research supervisors, 200 course instructors and five work supervisors. Examples
are unavailable for the 100 grade-only instructors, so flag distributions are
not balanced across writer types. Templates control wording but do not establish
realistic endorsement distributions or eliminate evaluator bias. Existing CV
labels remain CV-only; endorsements can change perceived overall merit.
