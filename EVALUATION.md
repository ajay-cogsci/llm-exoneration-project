# Running the PhD evaluation (`phd_eval`)

`phd_eval` builds the evaluation prompts, freezes a request plan, sends requests
to a chat-completions endpoint and exports the replies. It uses only the Python
standard library. `preview` and `plan` make no API calls.

- **Inputs:** [`datasets/phd-applications-v4-recommendations-v2/`](datasets/phd-applications-v4-recommendations-v2/) and [`configs/phd_eval_v1.json`](configs/phd_eval_v1.json).
- **PhD packets only:** the loader expects the PhD packet format (CV plus three recommendation summaries). Use `fellowship_eval` for fellowship packets.

## What a prompt contains

```sh
python3 -m phd_eval preview --condition cleared --task advance --format rationale
```

- **System message:** the committee role, an instruction to use only the information provided, and a request for JSON only.
- **User message, in order:**
  1. the opportunity description and selection criteria;
  2. the CV;
  3. the three recommendation summaries;
  4. the `INSTITUTIONAL RECORD` block, which holds one condition wording;
  5. the task prompt.
- **Only the record block varies:** for a given applicant, task and format, it is the only text that differs between conditions. A test enforces this.
- **Never in the prompt:** applicant IDs, tier labels or other analysis fields.

## Design

| Factor | Levels |
|---|---|
| Applicants | 100 (29 weak, 41 borderline, 30 strong) |
| Conditions | clean, neutral_control, pending, responsible, responsible_rehabilitated, cleared, dismissed, withdrawn, exonerated_on_appeal, exonerated_acknowledged, procedural_reversal |
| Wordings | 2 per condition |
| Tasks | quality (score 0–100), advance (score + yes/no), decide (score + admit/reject) |
| Formats | answer_only, rationale (≤3-sentence rationale first) |

- **Size:** 13,200 requests per model per repeat.
- **Order:** requests go out in a seeded random order, so drift at the provider is not lined up with condition.
- **Separate requests:** each task is its own request.

## Differences from the design document

Prompt, opportunity and condition text is copied verbatim from the design
document, with four exceptions. Each is recorded in the config under
`design_document_departures`.

1. **Pending wording:** "shortly before the application review" was removed. Twenty-four applicants finished their only degree in May 2026, so it would be impossible for them.
2. **Placement:** the condition text goes at the end, under the neutral heading `INSTITUTIONAL RECORD`.
3. **Placeholders:**
   - `next_stage`: "faculty interview";
   - `offer_verb`: "admit this applicant";
   - decision words: admit and reject.
4. **Identifier:** the internal `Applicant PHDv3-…` line is removed.

## Commands

```sh
# 1. Freeze a plan (refuses to overwrite an existing folder)
python3 -m phd_eval plan --out runs/<name> [--per-tier N] [--conditions a,b] [--repeats N]

# 2. Run one model; repeat per model. The key comes from EVAL_API_KEY.
export EVAL_API_KEY=...
python3 -m phd_eval run --plan runs/<name> --label "GPT-5.4 mini" \
  --api-model openai/gpt-5.4-mini --base-url https://openrouter.ai/api/v1 \
  --concurrency 16 [--limit 20]

# 3. Export
python3 -m phd_eval collect --plan runs/<name>
```

**`run`:**
- **Labels:** `--label` names the model in the results; `--api-model` is the provider's model ID.
- **Sampling parameters:** none are sent. Pass `--param key=value` only if a model fails without one.
- **Resuming:** re-running skips valid replies and retries failed or unparseable ones.
- **Saved attempts:** each attempt is appended to `runs/<name>/responses/<label>.jsonl`.

**`collect`:**
- **`results.csv`:** one row per request and model, with the parsed score, the decision (1/0) and the analysis labels.
- **`summary.json`:** reply validity, clean-record means by tier, and each condition's mean difference from the clean record.

A plan pins the config and every packet hash. A run stops if either changes.

## Analysis

`analysis/analyze_main.py` produces the analysis in
[`runs/main/analysis/`](runs/main/analysis/SUMMARY.md):

- **Main contrasts:** paired applicant-level differences from the clean record, with intervals clustered by applicant.
- **Model-based check:** a mixed model (condition + wording + format, with a random intercept per applicant) as a sensitivity check.
- **Multiple comparisons:** Holm correction within each model and task.
- **Heterogeneity:** results by tier and by each model's own clean-record score.

Things to keep in mind:

- **Tier labels are CV-only.** Recommendation letters can disagree with them, so each model's own clean-record score is a better measure of perceived strength.
- **Letters show their strength level as a labelled field.** That is a strong signal.
- **Llama 4 Maverick writes prose even when asked for JSON only,** so its format comparison is not interpretable.
