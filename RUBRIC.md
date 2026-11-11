# CV-only rubric revision — provisional v1

The revised sampler separates label definition, profile construction and sample
allocation. The published 100-CV sample is in
[`datasets/phd-cvs-v2-rubric-v1/`](datasets/phd-cvs-v2-rubric-v1/).
The original sampler and historical sample remain available for comparison.

## What is supported by the references

[Nghiem et al., Section 3 and Appendix D](https://arxiv.org/html/2509.16400v1)
provide the structured conditional construction, oversampling and weighted
selection pattern. Their performance quintiles describe relative position in a
cohort. They are not PhD readiness categories. The paper's empirical grounding
does not transfer to this project's provisional PhD probabilities.

The [Brandeis psychology rubric](https://www.brandeis.edu/psychology/doctoral/how-to-apply.html)
supports considering relevant coursework, quantitative preparation, intellectual
research participation and outputs. A publication is not a mandatory high-category
condition. Its full assessments also require evidence absent from a CV. This is
a psychology rubric, not a current CS/ML admissions rule.

The [UW 2020 sample rubric](https://grad.uw.edu/wp-content/uploads/Holistic-Admissions-2020.pdf)
supports examining research responsibility, duration and outputs. Its illustrative
time anchors are not converted into universal cutoffs. The
[Penn admitted-student statistics](https://www.cis.upenn.edu/admission-statistics/)
do not supply applicant distributions or numerical tier boundaries. The older
CMU secondary repost remains excluded from calibration.

**Every numeric threshold, conditional probability and overall decision rule
below is a provisional study choice.** These are observable CV proxies, not a
claim to fully implement Brandeis/UW high-category requirements. No thresholds
were tuned to produce a desired number of borderline applicants.

## Fixed rubric rules

The complete machine-readable policy is `configs/phd_rubric_v1.json`.
`evaluate(facts, policy)` receives only visible structured facts. It never reads
the old score, old label, cohort size, hidden preparation levels, or quota.
Every result includes the policy hash, fact hash, component ratings, evidence,
decision reason, missing evidence and unassessed dimensions.

Academic preparation uses four relevant courses: Linear Algebra, Probability
and Statistics, Algorithms and Machine Learning, plus the 4.0-scale GPA.

- **High:** GPA at least 3.5, at least three of the four grades A− or better,
  and every grade at least B+.
- **Low:** GPA below 3.0, at least two relevant grades below B, or any relevant
  grade C or below.
- **Adequate:** the remaining fully observed cases. A single B−/C+ can therefore
  remain adequate with a visible concern. Quantitative grades below B are
  reported explicitly; the same grades are not counted again as a separate score.

These academic proxies cannot establish course difficulty, a complete
transcript, or explanations for grades. In particular, a low GPA alone does not
prove low research potential.

Research preparation uses duration, hours and stated contribution:

- **High:** at least 18 calendar months, 4.5 full-time-equivalent months,
  and nine months in roles explicitly stating experiment design/analysis or
  research-question/method leadership.
- **Adequate:** at least six calendar months and 1.5 full-time-equivalent months,
  if the high conditions are not met. This can include sustained routine work.
- **Low:** the remaining fully observed cases, including explicitly no research.

Full-time-equivalent months = sum(months × hours per week / 40). This is only an
exposure measure. **Eighteen months at ten hours/week is 4.5 FTE months, not
eighteen full-time months, proof of a thesis, or two years of postbac research.**
Unknown contribution wording requires review; arbitrary prose is not interpreted
as proof of independence. Research intervals may not overlap in this version.
All roles in the retained template still share their research-level contribution
description; richer within-applicant progression is not modeled.

Publications are supporting evidence in the audit, not a gate or a point bonus.
Publication count alone cannot rescue weak preparation, and a research-strong
applicant can be strong without publications. This conservative rule avoids
pretending that generic venue labels quantify output quality. It also means
publication differences alone do not change tiers in this version.

| Academic evidence | Low research | Adequate research | High research |
| --- | --- | --- | --- |
| Low | Weak | Weak | Borderline |
| Adequate | Weak | Borderline | Strong |
| High | Borderline | Borderline | Strong |

This table makes compensation explicit: strong research can compensate for
adequate academics, while serious academic gaps plus high research remain
borderline. Excellent grades with limited research also remain borderline.
Research remains central to the generic research PhD opportunity. GPA need not
separate every tier; enforcing that separation would be another assumption.

Missing required fields, unknown grades/contributions, invalid exposure or
unreconciled overlapping research produce **unrated**, not weak. Faculty fit,
letters, essays, writing ability, motivation, course rigor and thesis equivalence
are unassessed. Technical/nontechnical work does not automatically upgrade or
downgrade a candidate. “Borderline” means mixed or incomplete readiness evidence
under this study rubric, not an estimated chance at a named program.

## Revised conditional sampler

`configs/phd_sampling_v3.json` retains conditional structured construction and
the existing chronology/credential validators, while changing two dependencies:

1. Research preparation is drawn from the existing five-level mixture. An
   academic level is then drawn from a five-by-five conditional table with
   nonzero off-diagonal entries. Relevant course patterns follow the academic
   level; research duration, responsibility and outputs follow the research level.
2. GPA is drawn from the existing bin boundaries using new probabilities
   conditional on academic level. The old GPA rank coefficient and unconditional
   bin masses are superseded. The new distribution is not asserted to preserve
   the old marginal or represent real applicants.

All probabilities are inspectable assumptions. Positive dependence remains,
but high academic/low research and low academic/high research cases are possible.
Domain-separated random streams prevent academic draws from replaying profile
or selection draws. `PHDv3-` IDs avoid collision with historical cached CVs.
The old composite is saved only inside `legacy_diagnostic` in new records.

New rubric metadata never enters evaluator facts or the model's writing/review
payload. The existing constrained writer remains unchanged. It can still invent
technical details within the allowed scope, so perceived-strength preservation
requires human review of the eventual prose, not only this structured audit.

## Allocation and mixed profiles

The reusable default `allocation` remains **null**; `sample-rubric` requires
explicit counts before creating a sample. The published dataset uses 30/40/30
with ten mixed cases, saved in its `sampling_policy.json`. These are design
quotas rather than population frequencies.

Each future allocation cell has `tier`, `pattern`, and integer `count`, with a
separate allocation `seed`. Counts are exact across the pooled cohorts, not per
cohort. There are no guaranteed per-pathway or per-seed totals.

The following eligible mixed-profile patterns are identified from visible facts:

1. `lower_gpa_strong_research`: GPA below 3.4 and high research.
2. `high_academics_limited_research`: high academics and low research.
3. `academic_gaps_strong_research`: low academics and high research.
4. `strong_research_without_publications`: high research and zero publications.

A profile may have several descriptive tags. For mutually exclusive allocation
cells, the **first matching pattern in that order** wins; otherwise it is `none`.
This prevents overlapping mixed quotas from double-counting records. The last
pattern is a publication-sparse research case, not necessarily a conflict between
academic and research dimensions. The pattern itself never changes the tier.

Within each requested tier/pattern cell, inverse pathway-frequency selection
without replacement improves pathway coverage. It does not guarantee equal
pathways or preserve population frequencies. Insufficient support raises an
error with available counts; no relabeling, duplication, unbounded retries or
threshold adjustment is used to fill a quota. Review pool and selected
descriptives/correlations separately after allocation.

## Commands and outputs

Inspect only:

```sh
python3 -m phd_resumes inspect-rubric
```

Audit existing data, copying their prose into a blind review pack and discarding
local simulated coverage fixtures:

```sh
python3 -m phd_resumes audit-rubric \
  --source sample-100-resume-generated --out audits/rubric-v1
```

Choose a new output path for a repeat audit; existing directories are not
overwritten. This audit does not change existing labels or make model calls.

For future replacements, set allocation in a separate policy file
and run `sample-rubric --sampling-policy PATH --out NEW_RUN`. It writes facts,
proposed labels, original and revised settings, policy hashes, source mappings,
and pool/selection diagnostics. Optional wording is then an explicit separate
`generate --run NEW_RUN --limit N --model MODEL` invocation. Both policy files
are checked for drift before API generation. Small generation limits cover
tiers but do not guarantee the full sample's mixed-pattern allocation; use the
entire allocated sample for the experiment.

Historical `sample`/`inspect` commands retain v2 behavior for reproducibility.
Do not use them to create the corrected experimental sample. Old generation
contracts intentionally reject changed implementation hashes; use the preserved
historical implementation snapshot to reproduce a historical contract, or a new
run/batch for intentional new work. Do not remove the drift checks.

## Validation limits and human review

The audit covers the original 150 records, all retained 100 CVs, 12 one-at-a-time
threshold variations, and 6,000 discarded structured fixtures across three seeds.
Fixtures test software support, chronology and coverage; they are not replacement
CVs or empirical population validation. Tests additionally use simulated model
responses to exercise future generation/cache integration without API charges.

The blind pack hides proposed labels and original identifiers. It cannot hide
credentials or prevent a reviewer recognizing a familiar CV. Share only the
`blind_review/` folder. Reviewers should first assess plausibility and tiers
independently, then compare disagreements with the proposed rules, especially
mixed cases and thresholds. Human review is **pending**, not an automated pass.

The revised sampler fixes the academic/research lockstep and makes quota design
explicit. It does not eliminate research-side coupling, five-template coursework,
generic institutions/venues, missing admissions evidence, provisional calibration,
or possible merit changes introduced by model prose.
