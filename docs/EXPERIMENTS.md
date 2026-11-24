# Experiments

Each experiment has its own folder in `runs/`. Its folder holds:
- the frozen plan: `config.json`, `plan.json` and `design.jsonl`;
- the raw replies, in `responses/` (not committed);
- the exports: `results.csv` and `summary.json`;
- an `analysis/` folder for finished runs.

## PhD

All PhD experiments use [`datasets/phd-applications-v4-recommendations-v2`](../datasets/phd-applications-v4-recommendations-v2/)
and the `phd_eval` harness. See [EVALUATION.md](../EVALUATION.md).

| Experiment | Folder | Design | Models | Write-up |
|---|---|---|---|---|
| Pilot | `runs/pilot/` | 15 applicants (5 per tier) × 3 conditions (clean, cleared, responsible) × 2 wordings × 3 tasks × 2 formats × 3 repeats = 1,620 requests per model | GPT-5.5, GPT-5.4 mini, Claude Sonnet 5.5, Gemini 3.8 Flash, Llama 4 Maverick, Qwen3-32B, Gemma 4 31B IT | `results.csv`, `summary.json` |
| Full design | `runs/main/` | 100 applicants × 11 conditions × 2 wordings × 3 tasks × 2 formats = 13,200 requests per model | GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT, Llama 4 Maverick, Qwen3-32B | [SUMMARY.md](../runs/main/analysis/SUMMARY.md) |
| No-infer ablation | `runs/ablation/plan_A`, `plan_B` | 4 conditions, answer-only format, 2,400 requests per model per arm. Arm B removes "Do not assume or infer details that are not stated." from the system message (`configs/phd_eval_v1_no_infer.json`) | Gemma 4 31B IT, Qwen3-32B, GPT-5.4 mini | [SUMMARY.md](../runs/ablation/analysis/SUMMARY.md) |

GPT-5.5 and Claude Sonnet 5.5 were in the pilot but have not run the full design.

Analysis code:
- **Full design:** `analysis/analyze_main.py`.
- **Ablation:** `analysis/ablation.py`.
- **Dependencies:** listed in `analysis/requirements.txt`.

## Graduate research fellowship

| Experiment | Folder | Design | Models | Status |
|---|---|---|---|---|
| Full design | `runs/fellowship/main/` | Same 11-condition design as the PhD study: 13,200 requests per model | Gemma 4 31B IT, Qwen3-32B, Llama 4 Maverick, GPT-5.4 mini, Gemini 3.8 Flash | Done; 65,997 of 66,000 valid; $72.82. [SUMMARY.md](../runs/fellowship/main/analysis/SUMMARY.md) |

- **Inputs:** [`datasets/fellowship-applicants-v2`](../datasets/fellowship-applicants-v2/) with `configs/fellowship_eval_v1.json`.
- **Harness:** `fellowship_eval`, run through `scripts/fellowship_run_driver.py` (parallel per-model copies: `scripts/fellowship_parallel.py`).
- **Analysis:** `analysis/fellowship.py`.
- **Rules:** [FELLOWSHIP_EVALUATION_HANDOFF.md](FELLOWSHIP_EVALUATION_HANDOFF.md) defines how the run is controlled: budget, retries and the analysis plan.

## Teaching assistant and research assistant

Applicant banks exist ([TA](../datasets/ta-applicants-v2/), [RA](../datasets/ra-applicants-v2/)),
but there is no evaluation harness for them yet. A future harness should reuse
the same 11 conditions, 2 wordings, 3 tasks and 2 formats, following
`fellowship_eval/`.

## Conventions

- **New folder per experiment:** never write into a finished run's folder.
- **Keep raw replies:** copy each finished run, including `responses/`, to a dated backup outside the repository.
- **Compare like with like:** compare conditions within an applicant (paired differences against `clean`). Don't pool results from different experiments.
