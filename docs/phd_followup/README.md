# Focused PhD follow-up (draft)

Status: **offline preparation only**. The user must review the exact wordings
and explicitly approve the model run and budget before any API request. Approval
to prepare, commit, and push these files is not approval to collect responses.

## What changes

| Design component | Original full design | Proposed follow-up |
|---|---|---|
| Opportunity | CS PhD | Same CS PhD |
| Applicants | 100 | Same 100 (29 weak, 41 borderline, 30 strong) |
| Allegation / concern topics | Unauthorized AI use | AI use, made-up results, calculation mistake |
| Record conditions | 11 | 20 |
| Wordings per condition | 2 | 2 |
| Tasks | Quality, advance, decide | Quality and advance |
| Formats | Answer-only and rationale | Answer-only |
| Repeats per cell | 1 | 1 |
| Requests per model | 13,200 | 8,000 |
| Completed / planned models | Five completed; two not run in full | Four proposed |

A **condition** is one institutional-record version. It is not a separate
applicant or an opportunity. Each condition has two wording variants.

The follow-up has six states for each of three topics, plus two shared controls:

1. Work checked during normal grading, without a prior allegation or concern.
2. Pending review.
3. Confirmed misconduct or calculation mistake.
4. Cleared before an adverse finding.
5. Cleared on appeal, with the finding and record consequences corrected.
6. The same appeal or grade-review outcome plus written acknowledgment of the wrong decision.

The shared controls are the original clean record and neutral administrative
error. This is `3 × 6 + 2 = 20` conditions, not 20 allegation topics.

Seven conditions repeat original wording: clean, neutral control, AI pending,
AI confirmed, AI cleared, AI appeal, and AI acknowledged. Thirteen are new:
AI routine verification plus all six states in each of the other two topics.
At 100 applicants × two wordings × two prompts, the follow-up has 2,800 repeated
bridge cells and 5,200 new cells per model.

Dismissed, withdrawn, procedural reversal, and rehabilitation remain in the
original study. This follow-up does not repeat them. Preserve all original
results. Collect the seven bridge conditions contemporaneously with the new
conditions so provider changes are not confounded with the new treatments.

## Review materials

- [All 40 exact wordings and review cautions](WORDINGS.md).
- [Literature rationale and the November 16 wording revision](RATIONALE.md).
- [Draft executable config](../../configs/phd_eval_followup_v1.json).
- [Condition-to-scenario mapping](../../analysis/phd_followup_conditions.csv).
- [Offline validation report](offline_validation.json).
- [Shared Google Doc wording-review tab](https://docs.google.com/document/d/1dgZkwce8f8iXa1Nt0kmj7WIPqrdzxcMJCaYEYm7VQ2s/edit?tab=t.9bo1infb7b0j).

The verification controls now describe an instructor checking submitted work
during normal grading for the class. They supply the same favorable factual
conclusion as clearing, without accusation history. This improves the comparison
with the short clean record but does not hold every word or reviewing authority
constant. The original AI clearing decision still comes from the integrity office.

The two new cases concern a course report based on supplied data. Fabrication
means deliberately making up results; the competence comparison concerns an
incorrectly calculated average. The latter uses an ordinary 10-mark deduction
from a 100-mark report and a departmental grade review. There is no disciplinary
hearing or zero for the calculation mistake. A successful grade review restores
the marks because the original work was correct, not because it was improved.
Fabrication retains a zero and an integrity-office decision. Consequences,
reviewing authorities, perceived seriousness, and text length therefore differ.
Cross-case differences cannot isolate a pure integrity-versus-competence mechanism.

Calculation-mistake records explicitly rule out alleged dishonesty; that sentence
may itself reassure the evaluator. The original clean baseline refers only to
integrity, so the case-specific verification control is the more relevant
reference. The competence example remains a draft comparison, not a validated
measure. Before freezing it, obtain a short human comprehension and plausibility
review and check perceived dishonesty, ability, seriousness, and certainty of
clearing. This review is proposed; no participants have been contacted.

The original system message, selected task prompts, CVs, letters, opportunity,
record heading, placement, and request parameters remain unchanged. The new
config omits unused task and format definitions so its default in-memory design
has 8,000 requests. This does not alter any text of the retained prompts. Its
version stays `phd-eval-v1`, as required by the harness. No harness edits are needed.

## Models and budget proposal

| Label | API model ID | Approximate API budget |
|---|---|---|
| GPT-5.4 mini | `openai/gpt-5.4-mini` | $8–10 |
| Llama 4 Maverick | `meta-llama/llama-4-maverick` | $8–10 |
| Qwen3-32B | `qwen/qwen3-32b` | $3–4 |
| Gemma 4 31B IT | `google/gemma-4-31b-it` | $2–3 |

Total estimate: **$21–27 (about $25)**. Proposed cap: **$35**, awaiting launch
approval. This is API inference cost, excluding coding-editor subscriptions,
human recruitment, taxes, and any credit-purchase fees.

The estimate uses the completed run's answer-only quality/advance token usage
and cost, including saved retries, repriced against the OpenRouter catalog
checked on 2026-11-16. At 8,000 cells each, the greater of historical cost and
repriced cost is approximately $7.19, $7.37, $2.49, and $1.98 respectively:
$19.03 before a 30% allowance ($24.74). This is a forecast, not an upper bound.
Llama's cost includes its long unsolicited prose. Longer new records, routing,
reasoning tokens, failed calls, and price changes can change actual charges.

Before a later launch: recheck IDs/prices and current key limits without printing
the key; obtain explicit wording/run/budget approval; establish a provider-side
spending cap including in-flight charges; and use small resumable batches. A
20-request smoke test per model counts toward its 8,000 requests. Keep defaults
and no `--param`. Stop and report unexpected parsing or cost behavior. No live
runner or automatic launch is added in this preparation change.

## Analysis specification

Primary outcome: advancement score. For each topic, pre-specify these pairs:

- Cleared minus routine verification.
- Appeal exoneration minus routine verification.
- Acknowledgment minus otherwise-identical appeal exoneration.

There are nine primary contrasts per model and **36 across the four models**.
This statistical family is unchanged by the wording revision. Including the
calculation case in this family does not validate it as a competence measure;
the cross-case mechanism comparison remains secondary and qualified.
Average the two wordings within applicant, then calculate the paired mean and
Student t standard error over applicants. Missing wording cells exclude that
applicant from the relevant contrast; do not silently average only the available
wording. The nominal independent unit is the applicant, not the number of API
requests. Report actual pair counts. The reused applicant bank limits external
generalization, and wording variants are not independent allegation examples.

Report raw 95% intervals, Holm-adjusted p-values, and Bonferroni simultaneous
95% intervals across the fixed family. Holm p-values and Bonferroni intervals
are different corrections. Do not call a small difference an effect unless the
corrected interval excludes zero. Retain all planned tests in the correction
family if some models or cells are unavailable. No equivalence test is planned.

Separate secondary families, each fixed across models:

| Family | Planned comparisons |
|---|---:|
| Same nine pairs, quality score | 36 |
| Same nine pairs, advancement yes-rate | 36 |
| Every other condition versus clean, per score task | 76 each |
| Every other condition versus neutral control, per score task | 76 each |
| Fabrication minus technical-error differences in the three paired gaps, per score task | 12 each |
| Wording 2 minus wording 1 differences in the nine paired gaps, per score task | 36 each |

Binary contrasts are proportion differences (multiply by 100 for percentage
points). Report condition means by CV tier and flag clean means below 15 as
possible floor limitations, not proof that a penalty is caused by the floor.
Raw attempt logs supply errors, unparseable attempts, retry counts by condition,
known costs, and missing-cost counts. Repeat estimates using first attempts as
a separately labeled sensitivity analysis. It does not fix selection bias from
missing or unparseable responses.

The original paired results remain exploratory context. These fixed follow-up
comparisons concern new outcomes on a reused applicant bank. They cannot establish
human-model differences or identify internal model mechanisms. A later historical
bridge comparison must keep original observations separate from the new data.

## Offline tools

These commands do not send model requests:

```sh
python3 scripts/check_phd_followup.py --write-review --report docs/phd_followup/offline_validation.json
python3 -m unittest discover -s tests
python3 scripts/verify_datasets.py
.venv/bin/python -m unittest discover -s tests -p 'test_phd_followup*.py'
```

The validator assembles the design only in memory. It checks all 8,000 prompt
cells, all 2,800 exact bridge matches, and all six acknowledgment additions.
The analysis tests use synthetic fixtures in temporary directories. They require
SciPy from `analysis/requirements.txt`; the standard-library test run skips those
analysis tests if SciPy is absent. No new dependencies were added.

Offline check on 2026-11-16: all 85 tests passed using the existing `.venv`,
including 13 new follow-up tests. The dataset verifier reproduced all 100 CVs,
300 recommendation summaries and 100 application packets. No model calls were
made. The Google Doc's draft tab was checked against all 40 exact config wordings.

The future analyzer is `analysis/analyze_phd_followup.py`. It requires an explicit
plan and a new output directory, verifies pinned config/design hashes, and rejects
incomplete studies unless `--allow-incomplete` is supplied. Provisional analyses
retain the complete correction families. It writes estimates, cell means, attempt
counts, status metadata, and a methods summary. It cannot call a model API.

## Keeping reviews synchronized

Edit the draft config first, then regenerate `WORDINGS.md` with the offline
validator. Update the shared Google Doc review wording from that same config.
Review notes and condition IDs are not inserted into the model prompts. Any
change to approved stimulus text requires another wording review before launch.
