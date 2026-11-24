# Graduate research fellowship: results

Five models evaluated 100 fictional fellowship applicants, each in 11 versions
that differ only in the `INSTITUTIONAL RECORD` paragraph. Every version was run
with 2 wordings, 3 prompts and 2 response formats: 13,200 requests per model
and 66,000 in total. The design, prompts and conditions are the same as in the
PhD study ([PhD results](../../phd-main/analysis/SUMMARY.md)). Only the
opportunity and the applicants differ.

- **Run dates:** 19–24 November 2026.
- **Analysis code:** `analysis/fellowship.py`.
- **Scores:** every score is on a 0–100 scale.
- **Paired differences:** each is a condition minus the same applicant's clean record, compared within matched applicant, wording, format and repeat cells. Brackets are 95% intervals clustered by applicant.
- **Significance:** `*` marks Holm-corrected p < .05 within model × prompt.

## Run

| Model (OpenRouter ID) | Valid / planned | Attempts | First-attempt valid | Transport errors | Unparseable | Reported cost |
|---|---|---|---|---|---|---|
| Gemma 4 31B IT (`google/gemma-4-31b-it`) | 13,200 / 13,200 | 13,250 | 13,170 | 50 | 0 | $2.51 |
| Qwen3-32B (`qwen/qwen3-32b`) | 13,200 / 13,200 | 13,329 | 13,071 | 115 | 14 | $6.97 |
| Llama 4 Maverick (`meta-llama/llama-4-maverick`) | **13,197** / 13,200 | 13,458 | 12,973 | 244 | 17 | $9.46 |
| GPT-5.4 mini (`openai/gpt-5.4-mini`) | 13,200 / 13,200 | 13,200 | 13,200 | 0 | 0 | $13.31 |
| Gemini 3.8 Flash (`google/gemini-3.8-flash`) | 13,200 / 13,200 | 13,216 | 13,184 | 16 | 0 | $40.57 |

- **Missing cells:** three Llama requests returned unparseable replies on both allowed attempts. They are incomplete and were not retried further. Every contrast uses only matched cells, and `n_cells` gives the count; it is 400 per contrast everywhere except where those three cells fall.
- **Transport errors:** these are connection drops, timeouts, Llama rate limits (HTTP 429) and requests cut off by restarts. None reached a parse step. 54 requests (20 Gemma, 34 Llama) used both attempts this way and got one extra attempt with the user's approval; all 54 succeeded. Each record of these extra attempts is flagged `extra_attempt`.
- **Costs:** the costs above are reported per-reply costs plus each model's share of interrupted-request billing, and sum to OpenRouter's total of $72.82.
- **Retries by condition:** a table of first-attempt failures by model and condition is in `attempts_by_model_condition.csv`.
  - The clean condition has the most retries for Llama (43) and Qwen (24). The clean-record calibration ran first, during the connection blips and rate limits, so this reflects when those requests ran, not the condition.
  - Unparseable first attempts were spread thinly across conditions: at most 4 per cell (Llama pending; Qwen clean).

## Does each model separate applicants?

Clean-record means by original provisional tier:

| Model | quality (weak / borderline / strong) | advance | decide |
|---|---|---|---|
| GPT-5.4 mini | 53.0 / 60.5 / 62.6 | 45.1 / 52.9 / 53.4 | 39.2 / 44.6 / 45.6 |
| Gemini 3.8 Flash | 40.2 / 50.2 / 55.1 | 23.4 / 30.4 / 34.8 | 21.6 / 26.9 / 30.2 |
| Gemma 4 31B IT | 42.0 / 51.6 / 55.9 | 30.1 / 40.0 / 47.5 | 25.1 / 32.8 / 40.2 |
| Llama 4 Maverick | 62.4 / 69.3 / 72.0 | 64.0 / 72.4 / 73.2 | 58.8 / 66.9 / 69.5 |
| Qwen3-32B | 58.9 / 62.9 / 65.1 | 51.3 / 58.8 / 61.0 | 50.6 / 57.2 / 60.2 |

- **Tier order:** the order is weak < borderline < strong in every model and prompt. The tiers are the original provisional generation labels, so this is a sanity check, not validation.
- **Floor and ceiling:** no clean tier mean is below 15 or above 85.
- **Binary decisions:** the final award decision is near the floor for three models. With a clean record, Gemini awards 0% of applicants, Gemma 1% and GPT-5.4 mini 4%, so award-rate contrasts for those models carry almost no information. The 0–100 scores do.

## Results: condition minus clean

**Quality** (overall strength):

| Condition | GPT-5.4 mini | Gemini 3.8 Flash | Gemma 4 31B IT | Llama 4 Maverick | Qwen3-32B |
|---|---|---|---|---|---|
| neutral control | −0.4 | +0.2 | −0.8 | −0.8 | −0.9 |
| cleared | −1.0* | −0.1 | −1.1* | −0.5 | −0.7 |
| dismissed | −2.8* | −0.3 | −3.3* | −3.6* | −2.0* |
| withdrawn | −3.4* | −0.3 | −3.6* | −5.8* | −2.8* |
| exonerated on appeal | −0.7 | −0.0 | +0.7 | +1.0 | −1.6* |
| exonerated, acknowledged | −1.4* | +0.4 | +1.0 | +1.8* | −1.7* |
| procedural reversal | −6.6* | −4.3* | −5.9* | −6.1* | −3.0* |
| pending | −7.9* | −3.2* | −5.3* | −9.3* | −6.2* |
| responsible, rehabilitated | −9.7* | −23.8* | −10.9* | −11.3* | −6.0* |
| responsible | −15.7* | −27.7* | −13.1* | −19.3* | −14.3* |

**Advance** to final fellowship selection review:

| Condition | GPT-5.4 mini | Gemini 3.8 Flash | Gemma 4 31B IT | Llama 4 Maverick | Qwen3-32B |
|---|---|---|---|---|---|
| neutral control | −1.1 | +1.4* | −0.0 | −0.1 | −0.7 |
| cleared | +0.5 | +1.4* | +1.8* | +1.0* | +0.5 |
| dismissed | +0.6 | +1.8* | −1.4* | −4.4* | −1.9* |
| withdrawn | −1.5* | +2.3* | −1.4 | −6.5* | −4.1* |
| exonerated on appeal | +2.3* | +3.0* | +7.0* | +3.6* | −0.7 |
| exonerated, acknowledged | +2.2* | +3.6* | +6.5* | +5.6* | +1.0 |
| procedural reversal | −10.1* | −3.3* | −3.4* | −6.0* | −4.7* |
| pending | −11.0* | −2.7* | −4.8* | −17.0* | −12.1* |
| responsible, rehabilitated | −17.2* | −18.9* | −12.3* | −16.6* | −11.9* |
| responsible | −30.5* | −22.3* | −16.0* | −28.9* | −23.6* |

**Decide** (award the fellowship):

| Condition | GPT-5.4 mini | Gemini 3.8 Flash | Gemma 4 31B IT | Llama 4 Maverick | Qwen3-32B |
|---|---|---|---|---|---|
| neutral control | −1.8* | +0.5 | −0.9 | −1.0 | −1.6 |
| cleared | −2.3* | +0.4 | −0.2 | −0.5 | −0.4 |
| dismissed | −2.5* | −0.4 | −2.2* | −6.3* | −3.1* |
| withdrawn | −2.1* | +0.0 | −2.9* | −9.1* | −3.9* |
| exonerated on appeal | +0.8 | +0.5 | +1.9* | +3.6* | −1.9* |
| exonerated, acknowledged | +1.1 | +1.3* | +2.9* | +5.9* | −0.5 |
| procedural reversal | −7.7* | −4.0* | −6.3* | −9.4* | −5.2* |
| pending | −10.5* | −2.9* | −6.1* | −19.4* | −10.5* |
| responsible, rehabilitated | −15.1* | −16.8* | −13.3* | −19.2* | −10.4* |
| responsible | −25.4* | −20.0* | −16.4* | −34.2* | −19.3* |

Advance yes-rate, in percentage points versus clean: pending costs −35 (GPT-5.4 mini), −37 (Llama) and −41 (Qwen); responsible costs −44, −80 and −52. Full rates are in `estimates.csv` (`outcome = decision_yes_rate`).

## What the evidence supports

Only differences whose Bonferroni-adjusted interval excludes zero are called established.

- **Cleared is mostly not penalised.**
  - **Established:** GPT-5.4 mini scores a cleared applicant 2.3 points lower on the final decision (Bonferroni interval −3.9 to −0.7).
  - **Borderline:** Holm-significant but Bonferroni interval reaches zero. These are GPT-5.4 mini −1.0 and Gemma −1.1 on quality.
  - **Small positive on advance:** cleared is +1.0 to +1.8 above clean on advance for Gemini, Gemma and Llama. Only Gemini's Bonferroni interval excludes zero.
  - **Everything else:** all other cleared contrasts are within about ±1 point and not significant.
  - **Difference from the PhD study:** in the PhD study, cleared was never below clean after correction. Here one small penalty (GPT-5.4 mini, decide) is established.
- **Withdrawn and dismissed are penalised more widely than in the PhD study.**
  - **Quality:** four of five models score them 2–6 points below clean; Gemini is the exception.
  - **Decide:** GPT-5.4 mini, Gemma, Llama and Qwen penalise them on decide too.
  - **PhD comparison:** in the PhD study this was mainly Llama and Qwen.
  - **Gemini:** it is the one model that does not penalise them on any prompt; on advance it slightly favours them.
- **Explicit exoneration scores above clean in four models** on advance (+2.2 to +7.0). Gemma shows the largest effect. Qwen shows no bonus, as in the PhD study.
- **Procedural reversal, pending and responsible findings are penalised by every model on every prompt:**
  - **Procedural reversal:** −3 to −10.
  - **Pending:** −3 to −19.
  - **Responsible:** −13 to −34.
- **Rehabilitation recovers only part of the responsible penalty.** On advance it recovers 43–50% for GPT-5.4 mini, Llama and Qwen, but only 15–23% for Gemini and Gemma.
- **Penalties grow with the applicant's own clean score.**
  - **Responsible:** the cross-fitted slope is −3.6 to −7.7 points per 10 points of clean score, significant for every model on advance.
  - **Pending:** significant for four models.
  - **Cleared:** Gemini's slope is slightly positive (+1.4), and Llama's is slightly negative (−1.1).
- **Neutral control:** the administrative control is close to clean everywhere (within ±1.8). The small negatives for GPT-5.4 mini (−1.8, decide) and Gemini (+1.4, advance) are the only significant ones.

## Robustness

- **Mixed model versus paired:** the two analyses agree on 454 of 465 contrasts. All 11 disagreements are small effects that are significant in only one analysis, and 10 of the 11 are significant only in the paired analysis.
- **First attempt versus eventual reply:** analysed on first attempts only, every estimate moves by at most 0.31 points (median 0.01), and 2 of 465 conclusions change. Contrasts there use at least 371 matched cells. Retries do not drive the results.
- **Bonferroni:** of 333 Holm-significant score contrasts, 17 have a Bonferroni interval that includes zero. They are all small and are treated as borderline above.
- **Wording:** the two wordings change a condition's effect in 44 of 150 model × prompt × condition cells. Llama accounts for 17 of them.
- **Format:** the rationale format changes it in 33 of 150 cells, most often for GPT-5.4 mini (12). Llama's 10 format differences should be read with caution, because it wrote prose in both formats in the PhD run.

## Rationales

These figures come from a keyword screen of the 600 rationale-format replies per model and condition. The screen is coarse.

- **Mentions:** rationales almost always mention a responsible finding (90–100%). Mentions of a cleared allegation vary by model: 2–4% for Gemini and Gemma, about 22% for GPT-5.4 mini, Llama and Qwen.
- **Linking the allegation to listed work:** some rationales tie the allegation to the applicant's own projects, research or proposal. This is mostly Llama, for responsible (45%), pending (34%) and procedural reversal (24%). For cleared it is 0–5%.
- **What the screen cannot show:** the screen cannot tell an explicit inference from a passing mention. Reading the flagged rationales is still to do.

## Comparison with the PhD study

Same models, prompts and conditions; different fictional applicants and opportunity. Shown for description only (`phd_comparison.csv`).

- **Cleared:** cleared versus clean is within ±1.7 points of the PhD estimate for every model.
- **Opportunity effects:**
  - **Llama** penalises pending (−6.4) and responsible (−13.3) more for the fellowship.
  - **Gemini** penalises them less (+5.6, +7.7).
  - **Interpretation:** these are not matched applicants, so the differences cannot be attributed to the opportunity alone.

## Spend

- **OpenRouter:** OpenRouter shows **$72.82** billed between the start of this plan and the end of the run, against a cap of $100. The cap was raised from $80 to $90 to $100 during the run, with the user's approval each time.
- **Reported per reply:** $72.70.
- **Unattributed:** $0.12 billed by OpenRouter is not covered by any recorded reply cost; it was most likely work finished on OpenRouter's side for replies that never reached us. It is shared equally across the 426 interrupted requests, and the ledger then matches OpenRouter exactly.

## Verified versus interpretation

**Verified** (by reading the files):
- **Counts:** the counts, costs and missing cells above.
- **Frozen plan:** the plan verifies against its frozen hashes after the merge.
- **Contrast basis:** every contrast uses matched cells.
- **Tier order:** clean scores rise from weak to strong.
- **Extra attempts:** all 54 extra attempts succeeded.

**Interpretation:**
- **Withdrawn and dismissed:** the reading that some models treat them as "probably did it" is an inference from score patterns. The rationale screen supports it only weakly for Llama.
- **Fellowship versus PhD:** differences between the two studies may come from the applicants, the opportunity text, or both.

## How this run differed from the run specification

All of these were approved by the user during the run.

- **Parallel runs:** to finish in hours instead of days, the remaining four models ran in parallel. Each ran in its own copy of the frozen plan with a slice of the cap, and the copies were merged back afterwards (`old/scripts/fellowship-run/fellowship_parallel.py`). The frozen harness code was not modified.
- **Concurrency:** it was raised from 4 to 8–32 per model, matching the PhD run where possible. Llama stayed at 4 because its only provider rate-limited it.
- **Interrupted requests:** these were first charged their full worst-case cost against the cap, then re-settled at OpenRouter's actual billed cost (`old/scripts/fellowship-run/fellowship_resettle.py`).
- **Extra attempts:** the 54 extra attempts described under Run.

## Limits

- **Fictional applicants:** all applicants are fictional, and tier labels are provisional generation labels.
- **One reply per request:** each request got one reply at default sampling settings. There was no formal test–retest study.
- **Panel:** the five models are cheaper or open-weight models. No frontier model (GPT-5.5, Claude Sonnet 5.5) has run the full design.
- **Applicants across studies:** PhD and fellowship applicants are different people, so cross-opportunity differences are descriptive.

## Files

All in `results/fellowship-main/analysis/`. Run metadata (frozen config, plan, budget history, model settings, calibration checks) is in `results/fellowship-main/run/`; raw replies are local only, in `runs/fellowship/main/`, and backed up outside the repository.

| File | Contents |
|---|---|
| `estimates.csv` | Every estimate: input (eventual or first attempt), model, prompt, outcome, analysis, contrast, interval, Holm p and denominators |
| `cell_means.csv` | Mean score and decision rate per cell |
| `mixed_model_fits.csv`, `mixed_vs_paired.csv` | Mixed-model sensitivity analysis and its agreement with the paired estimates |
| `attempts_by_model_condition.csv` | First-attempt validity and retries by model and condition |
| `rationale_scan.csv` | Rationale keyword screen |
| `phd_comparison.csv` | Fellowship estimates beside the PhD estimates |
| `fig_{quality,advance,decide}.png`, `*_cleared_zoom.png` | One figure per prompt, plus zoomed views of the cleared-type conditions |
