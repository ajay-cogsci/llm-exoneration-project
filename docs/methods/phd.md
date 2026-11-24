# PhD applicants

100 fictional Computer Science PhD applicants: 29 weak, 41 borderline and 30
strong, including ten designated mixed profiles. Each applicant has a CV and
three recommendation summaries.

- **Data:** [`data/phd/cvs`](../../data/phd/cvs/) holds the CVs and their structured facts. [`data/phd/applications`](../../data/phd/applications/) holds the full evaluation packets: CV plus letters.
- **Code:** `src/generate/phd_resumes` (CVs) and `src/generate/phd_recommendations` (letters).
- **Settings:** `configs/phd_rubric_v1.json`, `configs/phd_sampling_v3.json` and `configs/phd_recommendations_v2.json`.

## How the applicants were built

1. Sample academic and research preparation with separate conditional draws (6,000 records across seeds 123, 456 and 789).
2. Assign each CV a tier from explicit academic and research rules (below).
3. Select the 30/40/30 tier allocation, with ten mixed cases, from the pool.
4. Have a model write constrained CV descriptions, check them against the facts, and render fixed credentials (dates, grades, institutions) directly. CV wording came from GPT-6 Astra at medium reasoning effort. Ninety-one CVs passed the factual check at once; nine passed after one wording repair.
5. Attach three recommendation summaries from fixed templates, with no model calls.

## CV tier rules

The rubric reads only visible structured facts. It never reads hidden
preparation levels, quotas or cohort rank. Every rating records its evidence,
decision reason and what it could not assess. Every threshold below is a
provisional study choice.

**Academic preparation** uses four relevant courses (Linear Algebra,
Probability and Statistics, Algorithms, Machine Learning) and the 4.0-scale GPA.

| Level | Rule |
|---|---|
| High | GPA at least 3.5, at least three of the four grades A− or better, and every grade at least B+ |
| Low | GPA below 3.0, at least two relevant grades below B, or any relevant grade C or below |
| Adequate | All other fully observed cases |

**Research preparation** uses duration, hours and stated contribution.
Full-time-equivalent (FTE) months = sum(months × hours per week / 40). For
example, 18 months at 10 hours a week is 4.5 FTE months.

| Level | Rule |
|---|---|
| High | At least 18 calendar months, 4.5 FTE months, and 9 months in roles stating experiment design/analysis or research-question/method leadership |
| Adequate | At least 6 calendar months and 1.5 FTE months |
| Low | All other fully observed cases, including no research |

Publications are supporting evidence only. They neither gate a tier nor add to
it.

| Academic \ Research | Low | Adequate | High |
|---|---|---|---|
| Low | Weak | Weak | Borderline |
| Adequate | Weak | Borderline | Strong |
| High | Borderline | Borderline | Strong |

- **Unrated records:** missing or unknown fields produce *unrated*, not weak.
- **Not assessed:** faculty fit, essays, writing, motivation and course rigor.
- **Borderline:** means mixed or incomplete readiness under this rubric, not a chance of admission.

## Sampling

- **Research first:** research preparation is drawn from a five-level mixture. Academic level is then drawn from a conditional table with non-zero off-diagonal entries, so high-academic/low-research applicants and the reverse both occur.
- **Downstream draws:** course grades follow the academic level. Research duration, responsibility and outputs follow the research level. GPA is drawn from fixed bins conditional on academic level.
- **Random streams:** separate seeded streams keep the draws independent.

**Mixed profiles** are identified from visible facts, first match wins:
1. lower GPA (below 3.4) with high research;
2. high academics with low research;
3. low academics with high research;
4. high research with no publications.

Within each tier/pattern cell, selection favours under-represented pathways. If
a cell cannot be filled, the run stops with an error; it never relabels or
duplicates records.

## Recommendation summaries

Each applicant has three distinct fictional writers. Each summary is 30–100
words and shows four fields: writer type, strength level (limited, moderate or
strong), whether it compares the applicant with other students, and whether it
gives a specific example of the applicant's work.

- **Who writes:**
  - one writer for the longest research entry, if there is one;
  - one instructor for a seeded choice of graded course;
  - one instructor for the first technical course project.

  Without research, the third writer covers the longest work entry.
- **Observation period:** a writer's observation period equals the linked role's recorded period.
- **Flags:** a comparison is included with probability 0.5. An example is included with probability 0.5 where an observed activity exists. A grade alone never counts as an example.
- **Examples:** each example quotes exactly one accepted CV bullet from the writer's linked activity. Nothing new is invented.
- **Comparisons:** fixed below/at/above-typical templates, not ranks inferred from GPA.
- **Independence from tier:** letter strength is assigned independently of the CV tier, so letters can disagree with it.

Strength probabilities (limited / moderate / strong):

| Linked evidence | Limited | Moderate | Strong |
|---|---:|---:|---:|
| Research under 3 months | 0.65 | 0.35 | 0.00 |
| Longer research: assigned or routine tasks | 0.35 | 0.60 | 0.05 |
| Longer research: guided experimental design | 0.15 | 0.65 | 0.20 |
| Longer research: design/analysis or question/method leadership | 0.05 | 0.35 | 0.60 |
| Course grade A− or better | 0.00 | 0.40 | 0.60 |
| Course grade B or B+ | 0.25 | 0.75 | 0.00 |
| Course grade below B | 0.65 | 0.35 | 0.00 |
| Course project: baseline implementation | 0.35 | 0.60 | 0.05 |
| Course project: comparative implementation/evaluation | 0.15 | 0.60 | 0.25 |
| Employment role | 0.20 | 0.65 | 0.15 |

The published letters contain:
- **Strength:** 68 limited, 147 moderate and 85 strong letters, counted as originally generated; the 11 letters later changed to moderate are described below.
- **Comparisons:** 148 compare the applicant with other students.
- **Examples:** 97 give a specific example.
- **Writers:** 95 research supervisors, 200 course instructors and 5 work supervisors.

## Consistency corrections

The current data includes two corrections to an earlier release. These were
made without any model calls.

- **GPA:** 19 CVs printed a GPA that contradicted the listed course grades, so those GPAs were redrawn. One applicant changed from weak to borderline.
- **Letters:** 11 course letters gave an endorsement that contradicted the cited grade. Those letters are now moderate.

The earlier release and the correction code are in `old/`.
`old/scripts/verify_phd_history.py` rebuilds today's files from them byte for
byte.

## Verification

```sh
python3 scripts/verify_datasets.py
```

The script checks:
- **Files:** every file against its checksum.
- **Tiers:** every tier recomputes from its facts.
- **Packets:** every packet is rebuilt from its CV and three letter records.

No model calls or keys are needed.

## Generating a new sample

Wording generation is billable and needs an OpenAI key and approval. Choose a new output folder; existing ones are never overwritten.

```sh
python3 -m phd_resumes inspect-rubric
python3 -m phd_resumes sample-rubric --sampling-policy <policy.json> --out runs/<new>
python3 -m phd_resumes generate --run runs/<new> --limit 3
python3 -m phd_recommendations generate --source <accepted CV run> --out runs/<new-letters>
```

## Limits

- **Provisional settings:** the probabilities and thresholds are study choices, not admissions data. They are motivated by the [Brandeis](https://www.brandeis.edu/psychology/doctoral/how-to-apply.html) and [UW](https://grad.uw.edu/wp-content/uploads/Holistic-Admissions-2020.pdf) rubrics and [Penn CIS statistics](https://www.cis.upenn.edu/admission-statistics/), and the structure follows [Nghiem et al.](https://arxiv.org/html/2509.16400v1).
- **Templates:** fixed templates control wording, but they do not make the endorsement rates realistic.
- **Not independent:** the factual check used the same model that wrote the CVs.
- **No human review:** the CVs and letters have not been reviewed by a person.
