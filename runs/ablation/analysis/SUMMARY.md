# No-infer ablation: does "Do not assume or infer details that are not stated." matter?

## What was run

- **Question:** does deleting the sentence "Do not assume or infer details that are not stated." from the system message change how models score the same applications?
- **Arm A** used the original config (`configs/phd_eval_v1.json`). **Arm B** used `configs/phd_eval_v1_no_infer.json`, which is identical except that this one sentence is deleted. I rebuilt every prompt in both plans and compared them in pairs: all 2,400 pairs differ only by that sentence.
- **Design:** 100 applicants (29 weak, 41 borderline, 30 strong) × 4 conditions (clean, cleared, pending, responsible) × 2 wordings × 3 prompts (quality, advance, decide), answer-only format, one repeat. That is 2,400 requests per model per arm.
- **Models:** Gemma 4 31B IT, Qwen3-32B and GPT-5.4 mini, with the same labels and settings as the main run: no request parameters, concurrency 16, 32 and 16. Requests went through OpenRouter.
- **Run date:** 2026-11-13.
- **Version field:** the ablated config keeps `"version": "phd-eval-v1"` because the harness accepts no other value (`phd_eval/design.py:31`). Its `status` field and a new `design_document_departures` entry mark it as the ablation instead.

## Parse, valid and error rates

| Model | Arm | Attempts | Valid requests | Unparseable attempts (retried) | Request errors | Cost (from replies) |
|---|---|---|---|---|---|---|
| Gemma 4 31B IT | A | 2,400 | 2,400 | 0 | 0 | $0.32 |
| Gemma 4 31B IT | B | 2,400 | 2,400 | 0 | 0 | $0.32 |
| Qwen3-32B | A | 2,415 | 2,400 | 15 | 0 | $0.74 |
| Qwen3-32B | B | 2,416 | 2,400 | 16 | 0 | $0.73 |
| GPT-5.4 mini | A | 2,400 | 2,400 | 0 | 0 | $1.97 |
| GPT-5.4 mini | B | 2,400 | 2,400 | 0 | 0 | $1.98 |

- **Completeness:** every request got a valid reply in both arms.
- **Errors:** there were no request errors.
- **Spend:** about $6.06 in total, with the arm A costs including the 20-request smoke tests. OpenRouter's usage total for the key went from $94.15 to $100.16, which agrees once you allow for its reporting lag.

## How to read the tables

- **Gap vs clean:** the mean, over the 100 applicants, of the applicant's score in that condition minus the same applicant's clean score. Each applicant's score is averaged over the two wordings. Scores run 0–100. Brackets are 95% intervals clustered by applicant.
- **Removal effect:** the gap in arm B minus the gap in arm A, paired by applicant. A negative removal effect for cleared means the cleared applicant does slightly worse relative to clean once the sentence is gone.
- **Re-run noise:** arm A's gap minus the same gap in the original full run (`runs/main/results.csv`, answer-only, same four conditions). Arm A's prompts are byte-identical to the main run's, so this difference is pure run-to-run variation. It is the yardstick for whether a removal effect is more than noise.

## Results by prompt

### quality

| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B − A | Re-run noise (A vs main) |
|---|---|---|---|---|---|
| Gemma 4 31B IT | clean (mean score) | 59.1 | 58.2 | −0.9 [−1.5, −0.2] (level shift) | |
| Gemma 4 31B IT | cleared | +1.0 [+0.4, +1.6] | +0.6 [+0.0, +1.2] | −0.4 [−1.2, +0.4] | −0.1 |
| Gemma 4 31B IT | pending | −2.6 [−3.3, −2.0] | −2.7 [−3.4, −2.0] | −0.1 [−0.9, +0.7] | +0.0 |
| Gemma 4 31B IT | responsible | −8.3 [−9.2, −7.5] | −8.6 [−9.6, −7.6] | −0.2 [−1.2, +0.7] | +0.0 |
| Qwen3-32B | clean (mean score) | 68.4 | 68.8 | +0.3 [−0.4, +1.1] (level shift) | |
| Qwen3-32B | cleared | +0.6 [−0.2, +1.4] | −0.0 [−0.7, +0.7] | −0.6 [−1.6, +0.4] | +0.9 |
| Qwen3-32B | pending | −4.9 [−5.8, −3.9] | −5.2 [−6.1, −4.4] | −0.4 [−1.5, +0.7] | +1.6 |
| Qwen3-32B | responsible | −9.5 [−10.6, −8.4] | −10.2 [−11.3, −9.1] | −0.7 [−2.2, +0.8] | +1.4 |
| GPT-5.4 mini | clean (mean score) | 64.3 | 64.7 | +0.4 [−0.3, +1.0] (level shift) | |
| GPT-5.4 mini | cleared | −1.0 [−1.7, −0.3] | −0.9 [−1.5, −0.2] | +0.1 [−0.8, +1.1] | −0.1 |
| GPT-5.4 mini | pending | −7.6 [−8.7, −6.6] | −7.4 [−8.2, −6.6] | +0.2 [−1.0, +1.4] | +0.5 |
| GPT-5.4 mini | responsible | −15.1 [−16.3, −13.9] | −15.2 [−16.3, −14.1] | −0.1 [−1.2, +1.0] | −0.3 |

### advance

| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B − A | Re-run noise (A vs main) |
|---|---|---|---|---|---|
| Gemma 4 31B IT | clean (mean score) | 52.6 | 51.7 | −0.8 [−1.5, −0.2] (level shift) | |
| Gemma 4 31B IT | cleared | +1.6 [+0.7, +2.5] | +1.4 [+0.7, +2.1] | −0.3 [−1.4, +0.9] | −0.4 |
| Gemma 4 31B IT | pending | −3.0 [−3.7, −2.2] | −3.4 [−4.3, −2.5] | −0.4 [−1.4, +0.5] | −0.2 |
| Gemma 4 31B IT | responsible | −13.9 [−15.7, −12.1] | −14.1 [−16.0, −12.1] | −0.1 [−1.4, +1.1] | −0.7 |
| Qwen3-32B | clean (mean score) | 64.9 | 65.0 | +0.2 [−0.9, +1.2] (level shift) | |
| Qwen3-32B | cleared | −0.7 [−1.8, +0.5] | −0.6 [−1.6, +0.4] | +0.1 [−1.5, +1.7] | −1.5 |
| Qwen3-32B | pending | −9.0 [−10.2, −7.8] | −8.6 [−9.7, −7.4] | +0.4 [−1.1, +1.9] | −0.9 |
| Qwen3-32B | responsible | −16.3 [−17.9, −14.7] | −17.4 [−18.9, −15.9] | −1.1 [−2.9, +0.7] | +0.1 |
| GPT-5.4 mini | clean (mean score) | 62.4 | 62.7 | +0.3 [−0.8, +1.4] (level shift) | |
| GPT-5.4 mini | cleared | +1.4 [+0.3, +2.5] | +1.3 [+0.3, +2.3] | −0.1 [−1.6, +1.3] | −0.3 |
| GPT-5.4 mini | pending | −11.6 [−13.0, −10.2] | −11.0 [−12.5, −9.5] | +0.6 [−0.9, +2.1] | −0.6 |
| GPT-5.4 mini | responsible | −29.9 [−32.5, −27.4] | −29.2 [−31.2, −27.2] | +0.8 [−1.0, +2.5] | −1.4 |

### decide

| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B − A | Re-run noise (A vs main) |
|---|---|---|---|---|---|
| Gemma 4 31B IT | clean (mean score) | 49.6 | 48.9 | −0.8 [−1.6, +0.0] (level shift) | |
| Gemma 4 31B IT | cleared | +0.8 [−0.1, +1.7] | +0.2 [−0.5, +0.9] | −0.6 [−1.6, +0.4] | +0.2 |
| Gemma 4 31B IT | pending | −5.2 [−6.3, −4.2] | −4.9 [−5.8, −3.9] | +0.4 [−0.7, +1.5] | −1.1 |
| Gemma 4 31B IT | responsible | −16.4 [−18.4, −14.4] | −15.6 [−17.5, −13.7] | +0.8 [−0.4, +2.1] | −0.3 |
| Qwen3-32B | clean (mean score) | 63.6 | 63.4 | −0.2 [−1.3, +0.9] (level shift) | |
| Qwen3-32B | cleared | +0.8 [−0.3, +1.9] | +0.8 [−0.2, +1.8] | +0.0 [−1.4, +1.4] | −0.0 |
| Qwen3-32B | pending | −7.0 [−8.1, −5.9] | −7.1 [−8.2, −5.9] | −0.0 [−1.5, +1.5] | +1.1 |
| Qwen3-32B | responsible | −14.0 [−15.4, −12.5] | −14.8 [−16.3, −13.3] | −0.8 [−2.3, +0.7] | +0.5 |
| GPT-5.4 mini | clean (mean score) | 56.5 | 57.7 | +1.3 [+0.1, +2.5] (level shift) | |
| GPT-5.4 mini | cleared | −0.1 [−1.3, +1.1] | −0.6 [−1.8, +0.5] | −0.6 [−2.1, +1.0] | +0.8 |
| GPT-5.4 mini | pending | −14.2 [−16.1, −12.3] | −13.5 [−15.2, −11.8] | +0.7 [−1.2, +2.6] | −0.4 |
| GPT-5.4 mini | responsible | −29.2 [−32.0, −26.5] | −29.3 [−31.9, −26.6] | −0.0 [−1.9, +1.9] | −0.2 |

## Noise level

The noise level is the absolute difference in condition-vs-clean gaps between arm A and the main run, taken over 9 gaps per model (3 conditions × 3 prompts).

| Model | Median ("typical") | Mean | Max |
|---|---|---|---|
| Gemma 4 31B IT | 0.18 | 0.34 | 1.15 |
| Qwen3-32B | 0.94 | 0.89 | 1.59 |
| GPT-5.4 mini | 0.41 | 0.53 | 1.45 |

- **Gemma** is close to deterministic at default settings, so its noise level is very small.
- **Qwen** varies the most from run to run.

## Ordering of conditions

- **Same ordering in both arms** in 8 of 9 model × prompt cells. The exception is Qwen on quality, where cleared goes from +0.6 above clean in arm A to −0.0 in arm B. That shift is smaller than Qwen's typical re-run noise of 0.9.
- **The strict ordering clean > cleared > pending > responsible holds in only 3 of 9 cells in arm A and 4 of 9 in arm B.** The extra cell is the Qwen quality flip above. The ordering breaks because cleared often scores at or slightly above clean, as in the main run. That is not something the sentence causes.
- **The part of the ordering that carries the result holds in all 18 arm × model × prompt cells:** clean and cleared above pending, and pending above responsible.

## Verified vs inferred

**Verified** (by looking at the files and recomputing):
- The two arms' prompts differ only by the one sentence, in all 2,400 pairs.
- Arm A's prompts match the main run's prompts exactly.
- Every request has a valid reply, and there were no request errors.
- All 27 removal effects (3 models × 3 prompts × 3 conditions) have 95% intervals that include zero. The largest is −1.1 points (Qwen, responsible, advance).

**Inferred:**
- That this rules out an effect of practical size. With 100 applicants per condition, the removal-effect intervals are about ±1 to ±2 points, so an effect smaller than about 1–2 points could not be detected here.
- That the small level shifts in clean scores are run-to-run drift and not a response to the instruction. These are Gemma about 0.8–0.9 points lower in arm B, and GPT-5.4 mini 1.3 points higher on decide. Both move every condition together and leave the gaps unchanged.

**Not done:**
- Only the answer-only format, four conditions and three models.
- No rationale text, so nothing shows how the models used or ignored the instruction.
- No equivalence test.

## Verdict

Removing "Do not assume or infer details that are not stated." moved the cleared-vs-clean gap by at most 0.6 points in any model or prompt, and none of the nine cleared shifts has an interval that excludes zero.

By the agreed rule, two models exceed their noise level:
- **Gemma 4 31B IT:** the cleared gap shrinks by 0.3–0.6 points on all three prompts, against a noise level of 0.18.
- **GPT-5.4 mini:** the cleared gap shrinks by 0.6 points on decide, against a noise level of 0.41.

Without the sentence, the cleared bonus gets very slightly smaller in both cases. Qwen stays within its noise level on all three prompts.

These shifts pass the rule only because Gemma and GPT-5.4 mini are so repeatable that their typical noise is a few tenths of a point. Each shift is still smaller than the largest re-run difference for the same model (1.15 and 1.45). With 100 applicants per condition, I read this as no evidence that the sentence matters, not as an effect.

I recommend keeping the sentence in the human survey intro rather than dropping it. The model data were collected with it, matching instructions keeps the human–model comparison clean, and at most it would explain a fraction of a point of the cleared-vs-clean gap.

## Files

All paths are relative to the repository root.

- `analysis/ablation.py`: the analysis. Run it with `python analysis/ablation.py`.
- `configs/phd_eval_v1_no_infer.json`: the ablated config.
- `runs/ablation/plan_A/`, `runs/ablation/plan_B/`: the plans, `results.csv` and `summary.json`. Raw replies are in `responses/`, which is not committed.
- `runs/ablation/analysis/`: the analysis outputs.
  - `estimates.csv`: all estimates in tidy form.
  - `cell_means.csv`: mean score per model, prompt, arm and condition.
  - `noise.csv`: the noise level per model.
  - `rates.csv`: attempts, valid replies, errors and cost per model and arm.
  - `ordering.csv`: the condition ordering per model, prompt and arm.
  - `verdict_inputs.csv`: the inputs to the verdict rule.
  - `tables.md`: the tables above, generated from the CSVs.
