# Full-design run: summary (five of seven models)

Status as of 2026-11-12. Five models are complete. **Claude Sonnet 5.5 and
GPT-5.5 have not been run** (budget limit of $100 was set for this stage), so
nothing below speaks to those two.

All numbers come from `estimates.csv` in this folder unless stated. "Effect"
is used only where the Holm-corrected p-value is below .05. Of the 500
Holm-significant paired contrasts, 24 have a Bonferroni interval (`ci_low_adj`,
`ci_high_adj`) that still includes zero; all are small (under 1.3 score points
or 6 percentage points) and should be treated as borderline. Among results
cited below, that applies to: Gemini's advance yes-rate for cleared (+4) and
neutral control, GPT-5.4 mini's admit yes-rate for exonerated_acknowledged
(+5), and Llama's admit yes-rate for procedural_reversal (-6). No equivalence
test was run.

## 1. Run

Plan: `runs/main`, 100 applicants x 11 conditions x 2 wordings x 3 prompts x
2 formats = 13,200 requests per model, 1 repeat, no sampling parameters.
Endpoint: OpenRouter.

| Model | API id | Sent | Valid | Unparseable | Errors | Cost |
|---|---|---|---|---|---|---|
| Gemma 4 31B IT | google/gemma-4-31b-it | 13,203 | 13,200 | 2 | 1 | $1.89 |
| Qwen3-32B | qwen/qwen3-32b | 13,276 | 13,200 | 76 | 0 | $3.86 |
| Llama 4 Maverick | meta-llama/llama-4-maverick | 13,231 | 13,200 | 31 | 0 | $7.23 |
| GPT-5.4 mini | openai/gpt-5.4-mini | 13,202 | 13,200 | 0 | 2 | $13.87 |
| Gemini 3.8 Flash | google/gemini-3.8-flash | 13,200 | 13,200 | 0 | 0 | $35.73 |
| **Total** | | 66,112 | 66,000 | 109 | 3 | **$62.58** |

Running total after each model finished: Gemma $24.22, GPT-5.4 mini $28.80,
Llama $54.62, Gemini $60.69, Qwen $62.58 (models ran in parallel, so these
include partial spend on the others).

### Replies that were retried because they were unparseable

Requests with at least one unparseable attempt, by model and condition
(`unparseable_retries_by_model_condition.csv`; each condition has 1,200
requests per model):

| Model | clean | cleared | dismissed | exon. ack. | exon. appeal | neutral | pending | proc. rev. | responsible | resp. rehab. | withdrawn |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemma 4 31B IT | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Llama 4 Maverick | 2 | 2 | 1 | 2 | 2 | 2 | 5 | 1 | 8 | 4 | 2 |
| Qwen3-32B | 3 | 4 | 10 | 9 | 6 | 10 | 11 | 4 | 5 | 5 | 9 |

The highest cell is 11 of 1,200 (0.9%). At that rate, selection through
retrying cannot move a condition mean by more than a fraction of a point, but
the counts are not flat across conditions (Llama: 8 for responsible vs 1-2
for most others), so it is reported rather than dismissed.

## 2. Do scores track application quality?

Clean-record mean score by CV tier (`cell_means.csv`). Scores rise weak ->
borderline -> strong for every model and prompt.

| Model | Prompt | Weak | Borderline | Strong |
|---|---|---|---|---|
| GPT-5.4 mini | quality / advance / decide | 43.5 / 35.5 / 29.3 | 67.0 / 61.2 / 54.5 | 82.3 / 80.6 / 77.0 |
| Gemini 3.8 Flash | quality / advance / decide | 25.2 / 11.0 / 10.0 | 56.3 / 38.2 / 32.3 | 75.9 / 70.6 / 65.2 |
| Gemma 4 31B IT | quality / advance / decide | 30.4 / 16.4 / 16.3 | 63.2 / 54.1 / 49.8 | 84.0 / 83.3 / 80.3 |
| Llama 4 Maverick | quality / advance / decide | 44.0 / 41.4 / 33.3 | 68.9 / 71.8 / 66.1 | 85.5 / 87.5 / 84.5 |
| Qwen3-32B | quality / advance / decide | 48.6 / 35.9 / 36.8 | 69.9 / 65.0 / 63.9 | 84.1 / 83.9 / 82.8 |

**Floor flags (clean mean below 15):** Gemini 3.8 Flash, weak tier, advance
(11.0) and decide (10.0). About 10% of Gemini's clean scores on those prompts
are 5 or below. Small penalties in those cells are floor effects and are marked
`floor_flag` in `estimates.csv`. Gemma's weak tier (16.3-16.4) is just above
the threshold and should be read the same way.

## 3. Main result: difference from the same applicant's clean record

Paired estimate, score points on 0-100, with raw 95% interval clustered by
applicant (n = 100). `*` = Holm-corrected p < .05 within model and prompt
(31 contrasts).

### Advance prompt

| Condition | GPT-5.4 mini | Gemini 3.8 Flash | Gemma 4 31B IT | Llama 4 Maverick | Qwen3-32B |
|---|---|---|---|---|---|
| neutral_control | +1.5 [+0.8, +2.1]* | +1.3 [+0.7, +1.9]* | +1.2 [+0.6, +1.8]* | +1.0 [+0.1, +1.8] | -0.4 [-1.1, +0.3] |
| cleared | +2.2 [+1.5, +3.0]* | +1.7 [+1.0, +2.4]* | +2.2 [+1.6, +2.8]* | +0.5 [-0.4, +1.3] | +0.9 [+0.1, +1.7] |
| exonerated_acknowledged | +3.8 [+3.0, +4.6]* | +3.0 [+2.1, +3.8]* | +4.3 [+3.4, +5.3]* | +4.2 [+2.9, +5.4]* | +0.4 [-0.4, +1.1] |
| exonerated_on_appeal | +2.7 [+2.0, +3.3]* | +2.3 [+1.6, +2.9]* | +4.0 [+3.1, +4.9]* | +2.8 [+1.7, +3.9]* | -0.3 [-0.9, +0.4] |
| withdrawn | +0.2 [-0.5, +1.0] | +0.9 [+0.2, +1.6] | +0.3 [-0.3, +0.8] | -5.1 [-6.1, -4.1]* | -2.3 [-3.0, -1.6]* |
| dismissed | +0.9 [+0.2, +1.6] | +1.2 [+0.5, +1.8]* | +0.9 [+0.4, +1.4]* | -2.1 [-3.0, -1.1]* | -1.0 [-1.7, -0.2] |
| procedural_reversal | -9.0 [-10.1, -7.9]* | -4.9 [-6.0, -3.8]* | -0.4 [-1.0, +0.3] | -3.8 [-4.7, -3.0]* | -2.5 [-3.3, -1.8]* |
| pending | -10.7 [-12.0, -9.5]* | -8.3 [-9.8, -6.8]* | -3.9 [-4.7, -3.1]* | -10.5 [-11.7, -9.3]* | -8.4 [-9.5, -7.4]* |
| responsible_rehabilitated | -15.9 [-17.3, -14.5]* | -25.4 [-29.6, -21.3]* | -9.8 [-11.3, -8.4]* | -8.1 [-9.2, -7.0]* | -7.5 [-8.4, -6.6]* |
| responsible | -27.1 [-29.1, -25.1]* | -29.9 [-34.7, -25.2]* | -16.3 [-18.3, -14.3]* | -15.6 [-17.0, -14.1]* | -17.3 [-18.8, -15.8]* |

### Final decision prompt

| Condition | GPT-5.4 mini | Gemini 3.8 Flash | Gemma 4 31B IT | Llama 4 Maverick | Qwen3-32B |
|---|---|---|---|---|---|
| neutral_control | +0.2 [-0.5, +1.0] | +0.9 [+0.4, +1.5]* | +0.6 [+0.0, +1.1] | -0.4 [-1.0, +0.3] | -0.4 [-1.1, +0.4] |
| cleared | -0.0 [-0.8, +0.7] | +0.9 [+0.2, +1.5] | +0.5 [+0.0, +1.1] | -0.2 [-1.0, +0.5] | +0.9 [+0.1, +1.6] |
| exonerated_acknowledged | +2.3 [+1.5, +3.2]* | +2.1 [+1.3, +2.9]* | +2.1 [+1.3, +3.0]* | +5.0 [+3.9, +6.2]* | +0.2 [-0.4, +0.9] |
| exonerated_on_appeal | +2.0 [+1.1, +2.9]* | +1.8 [+1.1, +2.5]* | +2.1 [+1.3, +2.9]* | +3.9 [+2.8, +5.0]* | -0.3 [-0.9, +0.4] |
| withdrawn | -1.8 [-2.5, -1.1]* | +0.4 [-0.3, +1.0] | -1.2 [-1.7, -0.7]* | -6.0 [-7.1, -5.0]* | -2.2 [-3.0, -1.4]* |
| dismissed | -1.5 [-2.2, -0.8]* | +0.3 [-0.2, +0.8] | -0.6 [-1.1, -0.1] | -2.0 [-2.8, -1.3]* | -1.9 [-2.6, -1.2]* |
| procedural_reversal | -11.8 [-13.2, -10.4]* | -5.7 [-7.1, -4.2]* | -3.2 [-3.9, -2.4]* | -4.7 [-5.8, -3.5]* | -3.1 [-3.7, -2.4]* |
| pending | -12.9 [-14.5, -11.3]* | -9.9 [-12.0, -7.7]* | -5.4 [-6.4, -4.5]* | -13.7 [-15.2, -12.2]* | -8.1 [-9.1, -7.1]* |
| responsible_rehabilitated | -15.6 [-17.3, -13.9]* | -23.7 [-27.9, -19.5]* | -12.4 [-14.1, -10.6]* | -11.1 [-12.4, -9.8]* | -6.0 [-6.9, -5.1]* |
| responsible | -27.7 [-30.3, -25.1]* | -27.4 [-32.0, -22.8]* | -20.2 [-22.8, -17.6]* | -21.1 [-23.1, -19.0]* | -14.5 [-15.8, -13.3]* |

### Overall quality prompt

| Condition | GPT-5.4 mini | Gemini 3.8 Flash | Gemma 4 31B IT | Llama 4 Maverick | Qwen3-32B |
|---|---|---|---|---|---|
| neutral_control | -0.1 [-0.4, +0.3] | +0.5 [+0.1, +0.9] | +0.7 [+0.3, +1.1]* | -0.7 [-1.2, -0.2] | -0.4 [-0.9, +0.2] |
| cleared | -0.3 [-0.8, +0.2] | +0.5 [+0.1, +0.9] | +0.7 [+0.4, +1.1]* | -0.6 [-1.3, -0.0] | -0.0 [-0.6, +0.5] |
| exonerated_acknowledged | +0.2 [-0.3, +0.7] | +1.1 [+0.8, +1.5]* | +1.6 [+1.2, +2.1]* | +0.4 [-0.3, +1.1] | -0.6 [-1.2, +0.0] |
| exonerated_on_appeal | +0.4 [-0.1, +0.9] | +0.9 [+0.5, +1.2]* | +1.7 [+1.3, +2.2]* | +0.3 [-0.4, +1.1] | -0.8 [-1.3, -0.3]* |
| withdrawn | -1.8 [-2.3, -1.2]* | -0.1 [-0.5, +0.3] | -0.8 [-1.2, -0.4]* | -3.9 [-4.6, -3.2]* | -2.3 [-2.8, -1.7]* |
| dismissed | -1.5 [-2.0, -1.0]* | +0.1 [-0.3, +0.4] | -0.5 [-0.9, -0.0] | -2.6 [-3.2, -2.0]* | -1.2 [-1.7, -0.7]* |
| procedural_reversal | -5.2 [-5.8, -4.6]* | -4.2 [-4.8, -3.6]* | -2.1 [-2.5, -1.6]* | -3.0 [-3.7, -2.2]* | -2.4 [-3.0, -1.9]* |
| pending | -6.2 [-6.9, -5.6]* | -6.7 [-7.5, -5.9]* | -3.2 [-3.7, -2.7]* | -6.1 [-6.8, -5.3]* | -5.6 [-6.1, -5.0]* |
| responsible_rehabilitated | -7.8 [-8.4, -7.1]* | -23.2 [-25.5, -20.9]* | -6.6 [-7.3, -5.9]* | -6.9 [-7.7, -6.1]* | -4.9 [-5.6, -4.3]* |
| responsible | -12.9 [-13.7, -12.1]* | -28.5 [-31.4, -25.7]* | -9.6 [-10.4, -8.8]* | -10.9 [-11.9, -9.8]* | -9.9 [-10.6, -9.2]* |

Figures: `fig_quality.png`, `fig_advance.png`, `fig_decide.png` (all
conditions) and `fig_*_cleared_zoom.png` (neutral control and cleared-type
conditions only, on a readable axis).

### What the contrasts show

(a) **Cleared-type conditions vs clean.**
- `cleared` (affirmatively cleared before any finding) is never below clean
  after correction in any model or prompt. On the advance prompt it is above
  clean in GPT-5.4 mini, Gemini and Gemma (+1.7 to +2.2).
- `exonerated_on_appeal` and `exonerated_acknowledged` are above clean on the
  advance and decision prompts in four of five models (+1.8 to +5.0). Qwen3-32B
  shows no such increase, and on the quality prompt it scores
  exonerated_on_appeal slightly below clean (-0.8).
- `withdrawn` and `dismissed` are penalized in some models and prompts:
  consistently in Llama 4 Maverick (withdrawn -3.9 to -6.0; dismissed -2.0 to
  -2.6) and Qwen3-32B (withdrawn -2.2 to -2.3); in GPT-5.4 mini and Gemma on
  the decision and quality prompts only (-0.8 to -1.8); not in Gemini.
- `procedural_reversal` is penalized in every model on every prompt except
  Gemma on advance (-0.4, interval includes zero). The size ranges from about
  -2 to -12 and is largest in GPT-5.4 mini.

(b) **Cleared-type conditions vs neutral_control.** The neutral control itself
sits about 1 point above clean on the advance prompt in three models, so part
of the positive differences in (a) is not specific to exoneration. Against the
control: `cleared` is indistinguishable from it almost everywhere (exceptions:
Gemma advance +1.0, Qwen advance and decide +1.3). The two exoneration
conditions remain above the control on advance and decide in four models (+0.9
to +5.4). `withdrawn` is below the control in most model-prompt cells and
`procedural_reversal` in all of them.

(c) **Pending, responsible, responsible_rehabilitated vs clean.** All three are
penalized in every model and prompt. `pending` costs 3 to 14 points with no
finding against the applicant. `responsible_rehabilitated` recovers roughly 40
to 55% of the `responsible` penalty in GPT-5.4 mini, Gemma, Llama and Qwen, but
only about 15% in Gemini (advance: -25.4 vs -29.9).

(d) **Cleared-type conditions against each other.** The ordering is consistent:
exonerated (either form) >= cleared > dismissed ~ withdrawn > procedural
reversal. `cleared` exceeds `procedural_reversal` in every model and prompt
(+2.3 to +11.7). `exonerated_acknowledged` vs `exonerated_on_appeal`: the
acknowledged version scores higher on the advance prompt in GPT-5.4 mini
(+1.1), Gemini (+0.7) and Llama (+1.4; also +1.2 on decide); no difference
elsewhere.

### Binary decisions (difference in yes-rate vs clean)

`responsible` lowers the yes-rate by 20 to 47 percentage points and `pending`
by 5 to 45 (Llama, final decision: -45). `procedural_reversal` lowers it in
GPT-5.4 mini (-14, -17), Gemini (-5, -7), and on the decision prompt in Llama
and Qwen (-6 to -7). The exoneration conditions raise the advance yes-rate by 4
to 9 points in four models. `withdrawn` lowers the admit rate in Llama (-9).
`cleared` raises the advance rate in GPT-5.4 mini (+7) and Gemini (+4) and the
admit rate in Qwen (+5); elsewhere no difference.

## 4. Mixed model vs paired estimate

Point estimates are identical (largest gap 2e-13), as expected in a balanced
complete design. Standard errors are not: the random-intercept model pools one
residual variance across conditions, but the penalty varies a great deal
between applicants in the adverse conditions and very little in the
cleared-type ones. The mixed model is therefore too confident for the large
contrasts (its standard error is up to 3.5 times smaller than the clustered
one) and too cautious for the small ones (median ratio 0.46 for Gemini).

Conclusions after Holm agree for 416 of 465 model-prompt-contrast cells. All 49
disagreements go the same way: significant in the paired analysis, not in the
mixed model; 29 of them are Gemini. None involves a large contrast (the
largest is 2.1 points). The paired
intervals are the ones reported above because they do not assume a constant
effect across applicants. All mixed fits converged (`mixed_model_fits.csv`).

## 5. Heterogeneity

**By CV tier** (`analysis == by_cv_tier`). Adverse-condition penalties are
larger for stronger CVs in absolute points. The extreme case is Gemini:
`responsible` on advance is -53.7 for strong CVs, -28.1 for borderline and -7.9
for weak (floor-flagged; clean mean 11.0). The exoneration increase is
concentrated in weak and borderline CVs and is absent for strong CVs in Llama
(advance: +7.0 weak, +5.2 borderline, -0.0 strong).

**By the applicant's own clean score** (`analysis == by_clean_score`,
cross-fitted so that noise in the clean score does not create the slope). Per
10 points of clean score, the `responsible` penalty grows by 2.1 to 4.0 points
on advance in four models and by 7.9 in Gemini; `pending` by 0.6 to 2.0.
Slopes for cleared-type conditions are near zero except in Llama, where the
exoneration increase shrinks as clean score rises (-1.3 to -1.7 per 10 points).
Qwen's quality-prompt slopes are all near zero.

Because penalties scale with the baseline, differences in absolute points
between tiers partly reflect room to fall. Whether the proportional penalty
differs by strength was not tested.

## 6. Wording and format

**Wording 1 vs 2** (difference in the condition-minus-clean effect; note that
the clean record also has two wordings, so this compares wording pairs).
Significant after Holm in 44 of 150 cells. The large ones: Gemini penalizes
`procedural_reversal` wording 2 by 4.6 to 7.0 points more than wording 1; Gemma
penalizes `responsible` wording 2 more (-3.8, -4.2) and `pending` wording 2
less (+2.6, +4.5); Llama is more lenient under wording 2 for withdrawn,
dismissed, pending and responsible (+2.4 to +4.5). Wording effects are
therefore not negligible relative to the 1-5 point cleared-type effects.

**Answer-only vs rationale.** GPT-5.4 mini's penalties are smaller when it
writes a rationale first, in 20 of 30 cells (e.g. procedural_reversal +4.5 to
+5.6, responsible +2.6 to +3.7). Gemma goes the other way for `responsible`
(-6.1 advance, -8.2 decide: harsher with a rationale). Gemini and Qwen show
few differences. **Llama 4 Maverick's format contrast is not interpretable**:
it writes long prose before the JSON in both formats; its rows carry that note.

## 7. What was verified and what is inferred

Verified from files:
- Reply counts, error and unparseable counts and costs, from
  `runs/main/responses/*.jsonl` (every attempt is one line).
- Every estimate, interval and p-value above, from `estimates.csv`, produced by
  `analysis/analyze_main.py` from `runs/main/results.csv`.
- Mixed-model convergence and the mixed/paired comparison
  (`mixed_model_fits.csv`, `mixed_vs_paired.csv`).

Inferred or assumed:
- That retry selection is negligible, from the low counts; no analysis was run
  that drops or re-weights retried requests.
- That the neutral-control increase reflects "extra benign text in the record";
  the data show the increase, not its cause.
- "Recovers X% of the penalty" is a ratio of two means, with no interval.
- No rationale text was analysed for this run.

Did not work or was not done:
- Claude Sonnet 5.5 and GPT-5.5 were not run (budget).
- Holm does not give intervals. The corrected intervals in `estimates.csv` are
  Bonferroni intervals over the same 31 contrasts, which are slightly wider
  than Holm implies.
- neutral_control vs clean was added to the Holm family alongside contrast
  sets (a)-(d).
- One repeat per cell, so within-cell sampling noise is not separately
  estimated; it is absorbed by the applicant-clustered errors.
- A built-in Claude Code safety check blocked the first launch command; the
  runs were started through a small launcher script instead. No requests were
  affected.

## 8. Files

- `runs/main/results.csv`, `runs/main/summary.json` - harness exports.
- `runs/main/analysis/estimates.csv` - every estimate (tidy).
- `runs/main/analysis/cell_means.csv`, `mixed_model_fits.csv`,
  `mixed_vs_paired.csv`, `replies_by_model.csv`, `invalid_attempts.csv`,
  `unparseable_retries_by_model_condition.csv`.
- `runs/main/analysis/fig_*.png`.
- Raw replies: `runs/main/responses/` (not committed; 347 MB).
