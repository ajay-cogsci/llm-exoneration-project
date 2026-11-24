# LLM exoneration study

Do large language models judge an applicant more harshly when the application
mentions an academic-integrity allegation that was later **cleared**, compared
with the identical application with a clean record?

We build fictional applicant packets and ask LLMs to evaluate them. Each packet
is sent in 11 versions that differ only in a short **institutional record**
paragraph at the end:
- a clean record;
- a neutral administrative control;
- nine allegation outcomes, from "pending" and "found responsible" to "cleared", "dismissed" and "exonerated on appeal".

Everything else is identical, so a score difference between versions of the same
applicant is caused by that paragraph.

The study design is in `LLM exoneration research plan.pdf`. The team notebook is
the [LLM exoneration Google Doc](https://docs.google.com/document/d/1dgZkwce8f8iXa1Nt0kmj7WIPqrdzxcMJCaYEYm7VQ2s/edit).

## Status

| Opportunity | Applicants | Evaluation |
|---|---|---|
| Computer Science PhD | 100 | Done: pilot (7 models), full design (5 models), prompt ablation (3 models). [Results](runs/main/analysis/SUMMARY.md) |
| Graduate research fellowship | 100 | Running (5 models) |
| Introductory CS teaching assistant | 100 | Not started |
| Research assistant | 100 | Not started |

See [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) for every experiment, its inputs and its outputs.

## Main PhD findings

Across GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT, Llama 4 Maverick and
Qwen3-32B, with scores on a 0–100 scale:

- **Cleared** allegations were not penalised; explicit exonerations scored slightly *above* a clean record (+2 to +5 points).
- **Pending** allegations cost 3–14 points.
- **Found responsible** cost 15–30 points.
- **Procedural reversals** were penalised by almost every model.
- **Withdrawn** or **dismissed** allegations were penalised by some models (Llama, Qwen) but not others.
- Removing the instruction "Do not assume or infer details that are not stated." made no meaningful difference ([ablation](runs/ablation/analysis/SUMMARY.md)).

## Quick start

Python 3.10+. Applicant generation, verification and evaluation use only the
standard library.

```sh
git clone https://github.com/ajay-cogsci/llm-exoneration-project.git
cd llm-exoneration-project

python3 -m unittest discover -s tests          # offline tests; no keys needed
python3 scripts/verify_datasets.py             # checks the published PhD datasets

# Print exactly what a model is sent
python3 -m phd_eval preview --condition cleared --task advance --format rationale

# Reproduce the PhD analysis
python3 -m venv .venv && .venv/bin/pip install -r analysis/requirements.txt
.venv/bin/python analysis/analyze_main.py --plan runs/main
```

Three tests compare study text with the source PDF. They need `pdftotext` (from
poppler) and are skipped without it.

## Repository layout

| Path | Contents |
|---|---|
| `datasets/` | Published applicant banks: packets, structured facts, an HTML viewer and checksums. Read-only. |
| `configs/` | Evaluation configs (prompts and condition wordings) and generation settings. |
| `phd_eval/`, `fellowship_eval/` | Evaluation harnesses: build prompts, plan, send requests, export results. |
| `phd_resumes/`, `phd_recommendations/`, `phd_revisions/` | PhD applicant pipeline: CVs, recommendation letters, published corrections. |
| `ta_applicants/`, `fellowship_applicants/`, `ra_applicants/` | Applicant generators for the other three opportunities. |
| `analysis/` | Statistical analysis scripts. |
| `scripts/` | Dataset verification, audits and the fellowship run driver. |
| `runs/` | Experiment outputs. Ignored by git except committed result exports. |
| `tests/` | Offline unit tests with simulated API clients. |
| `docs/` | Experiment index and the fellowship run specification. |

Method documents: [RUBRIC](RUBRIC.md) (PhD CV tiers),
[RECOMMENDATIONS](RECOMMENDATIONS.md) (PhD letters),
[TA_METHOD](TA_METHOD.md), [FELLOWSHIP_METHOD](FELLOWSHIP_METHOD.md),
[RA_METHOD](RA_METHOD.md), [EVALUATION](EVALUATION.md) (running `phd_eval`) and
[VALIDATION](VALIDATION.md) (what has been checked).

## Datasets

| Dataset | Use |
|---|---|
| [`phd-applications-v4-recommendations-v2`](datasets/phd-applications-v4-recommendations-v2/) | **PhD evaluation input**: 100 CVs with three recommendation summaries each |
| [`fellowship-applicants-v2`](datasets/fellowship-applicants-v2/) | Fellowship evaluation input |
| [`ta-applicants-v2`](datasets/ta-applicants-v2/) | TA applicants |
| [`ra-applicants-v2`](datasets/ra-applicants-v2/) | Research-assistant applicants |
| `phd-cvs-v2-rubric-v1`, `phd-cvs-v3-gpa-consistency-v1`, `phd-applications-v3-recommendations-v1`, `sample-100-resume-generated/` | Earlier PhD versions. The corrected PhD inputs are rebuilt from these, so keep them. |

- **Applicants:** every opportunity has 100 fictional applicants. Each has a provisional weak, borderline or strong label from rule-based rubrics, not human ratings.
- **Viewers:** clone the repository to open a dataset's `index.html` viewer.

## How an evaluation works

1. **`plan`:** freezes the config, applicant hashes and a shuffled list of requests, 13,200 per model for the full design. A plan never overwrites an existing folder, and it refuses to run if code or data change afterwards.
2. **`preview`:** prints any prompt without sending it.
3. **`run`:** sends requests through OpenRouter, using the key in `EVAL_API_KEY`. It is resumable: valid replies are skipped. Every attempt is saved to `runs/<plan>/responses/<model>.jsonl` with the provider's reported cost.
4. **`collect`:** writes `results.csv`, one row per request with its score and decision, and `summary.json`.
5. **Analysis:** scripts in `analysis/` compare each condition with the same applicant's clean record, using intervals clustered by applicant.

Each harness has its own detailed guide:
- **PhD (`phd_eval`):** [EVALUATION.md](EVALUATION.md).
- **Fellowship (`fellowship_eval`):** [the fellowship run specification](docs/FELLOWSHIP_EVALUATION_HANDOFF.md). It adds a hard dollar cap and at most two attempts per request.

## Results and raw data

- **Committed:** `results.csv`, `summary.json` and the `analysis/` folder of each finished run in `runs/`. To add one, use `git add -f`, because `runs/` is ignored.
- **Not committed:** raw model replies (`runs/*/responses/`). They are backed up outside the repository by the person who ran the experiment.

## Ground rules

- **API keys:** never commit or print them. Code reads keys from environment variables.
- **Spending:** paid model runs need an agreed model list and dollar cap.
- **Published inputs:** don't edit prompts, condition wordings, datasets or a frozen plan. Create a new config, dataset version or run folder instead.
- **Completed work:** don't delete or overwrite completed runs.
- **Branches:** `main` is the shared branch; ask before pushing or merging.

## Limits

- **Fictional applicants:** the rubric thresholds and probabilities are study choices, not validated admissions standards.
- **Scope of the results:** the experiment measures how these models respond to the integrity paragraph in these packets. It does not show how real committees behave.
