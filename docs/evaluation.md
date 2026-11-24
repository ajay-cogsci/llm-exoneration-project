# Running an evaluation

Two harnesses send the study's prompts to models and export the replies:

| Harness | Opportunity | Inputs |
|---|---|---|
| `phd_eval` | Computer Science PhD | `data/phd/applications`, `data/phd/cvs`, `configs/phd_eval_v1.json` |
| `fellowship_eval` | Graduate research fellowship | `data/fellowship`, `configs/fellowship_eval_v1.json` |

Both use only the Python standard library, and both share the same design,
conditions, wordings, tasks and formats. `fellowship_eval` adds a hard dollar
cap and at most two attempts per request. A TA or RA harness should be built
like `fellowship_eval`.

## What a prompt contains

```sh
python3 -m phd_eval preview --condition cleared --task advance --format rationale
python3 -m fellowship_eval preview --condition cleared --task advance --format rationale
```

- **System message:** the committee role, an instruction to use only the information provided ("Do not assume or infer details that are not stated."), and a request for JSON only.
- **User message, in order:**
  1. the opportunity description and selection criteria;
  2. the application;
  3. the `INSTITUTIONAL RECORD` block, holding one condition wording;
  4. the task prompt.
- **Only the record block varies:** for a given applicant, task and format, it is the only text that differs between conditions. Tests enforce this.
- **Never in the prompt:** applicant IDs, tier labels or other analysis fields.

## Design

| Factor | Levels |
|---|---|
| Applicants | 100 |
| Conditions | clean, neutral_control, pending, responsible, responsible_rehabilitated, cleared, dismissed, withdrawn, exonerated_on_appeal, exonerated_acknowledged, procedural_reversal |
| Wordings | 2 per condition |
| Tasks | quality (score 0–100), advance (score + yes/no), decide (score + admit/reject or award/decline) |
| Formats | answer_only, rationale (≤3-sentence rationale first) |

- **Size:** 13,200 requests per model per repeat.
- **Order:** requests go out in a seeded random order, so drift at the provider is not lined up with condition.
- **Separate requests:** each task is its own request.
- **No sampling parameters:** models run at their providers' defaults.

**Differences from the design document.** Prompt, opportunity and condition
text is copied verbatim, with four exceptions. Each is recorded in the config
under `design_document_departures`:
1. **Pending wording:** "shortly before the application review" was removed, because it is impossible for applicants who finished their degree in May 2026.
2. **Placement:** the condition text goes at the end, under the neutral heading `INSTITUTIONAL RECORD`.
3. **Placeholders:** committee name, next stage and decision words are filled in for each opportunity.
4. **Identifier:** the internal `Applicant …` line is removed.

## Commands

```sh
# 1. Freeze a plan. A plan refuses to overwrite an existing folder, and refuses
#    to run if the code, config or data change afterwards.
python3 -m phd_eval plan --out runs/<name> [--per-tier N] [--conditions a,b] [--repeats N]

# 2. Run one model. The key is read from EVAL_API_KEY and never saved.
export EVAL_API_KEY=...
python3 -m phd_eval run --plan runs/<name> --label "GPT-5.4 mini" \
  --api-model openai/gpt-5.4-mini --base-url https://openrouter.ai/api/v1 --concurrency 16 [--limit 20]

# The fellowship harness also needs a cap and a per-request worst-case cost:
python3 -m fellowship_eval run --plan runs/fellowship/<name> --label "..." --api-model ... \
  --budget-cap-usd 100 --request-cost-ceiling-usd 0.5 --concurrency 16

# 3. Export
python3 -m phd_eval collect --plan runs/<name>
```

**Runs:**
- **Resumable:** re-running skips valid replies.
- **Saved attempts:** every attempt is appended to `runs/<name>/responses/<label>.jsonl`, with the provider's reported cost.

**`collect` writes:**
- **`results.csv`:** one row per request, with the score, the decision (1/0) and the analysis labels.
- **`summary.json`:** validity, clean means by tier, and each condition's mean difference from clean.
- **Fellowship extras:** `first_attempt_results.csv` and `attempt_summary.json`.

When a run is finished:
1. Copy `results.csv`, `summary.json` and the analysis into `results/<name>/` and commit them.
2. Back up the whole run folder, including the raw replies, outside the repository.

## Running a paid evaluation: practical notes

These lessons come from the PhD and fellowship runs.

- **Approval first.** Agree a model panel and a dollar cap first, and check current model IDs and prices on OpenRouter.
- **Smoke test.** Send 20 requests per model and read every reply before the full run.
- **Concurrency.** Use 16–32 for most models. Reasoning models (Qwen, Gemini) take about 25 seconds per request, so a concurrency of 4 means days. Llama 4 Maverick's only provider rejects more than about 4 requests at once (HTTP 429).
- **Sleep.** A laptop that sleeps stops the run. Keep it plugged in and awake (`sudo pmset -a disablesleep 1`, undone with `0`) or run on a server.
- **Connection drops.** A dropped connection leaves a request's cost unknown. The fellowship tooling in `old/scripts/fellowship-run/` handles this:
  - **Settling:** unknown costs are charged at worst case, then re-settled from OpenRouter's account total.
  - **Waiting:** runs pause until the network returns.
  - **Parallel runs:** several models can run at once with exact cap slices.

## Analysis

| Script | Reads | Writes |
|---|---|---|
| `analysis/analyze_main.py` | `results/phd-main/results.csv` | `results/phd-main/analysis/` |
| `analysis/fellowship.py` | `results/fellowship-main/` | `results/fellowship-main/analysis/` |

Install the analysis packages with `pip install -e ".[analysis]"`. Both scripts:
- **Main contrasts:** paired applicant-level differences from the clean record, with intervals clustered by applicant.
- **Sensitivity:** a mixed model (condition + wording + format, random intercept per applicant).
- **Multiple comparisons:** Holm correction within each model and task, plus Bonferroni intervals.
- **Heterogeneity:** results by tier (descriptive) and by each model's own clean score, cross-fitted.
- **Moderation:** wording and format effects.

`analysis/fellowship.py` also:
- compares only matched applicant/wording/format/repeat cells;
- analyses the first-attempt export alongside the final one;
- screens the rationales;
- compares with the PhD results.

Things to keep in mind:

- **Tiers are provisional labels.** Each model's own clean score is a better measure of perceived strength.
- **Llama 4 Maverick writes prose even when asked for JSON only,** so its format comparison is not interpretable.
- **Award decisions sit at the floor for some models.** With a clean record, Gemini, Gemma and GPT-5.4 mini award the fellowship to 0–4% of applicants, so use their scores rather than their award rates.
