# Running the PhD evaluation

`phd_eval` assembles the prompts from the "LLM exoneration" design document,
plans the design, sends requests to a model and exports the replies. It uses
only the Python standard library. Planning and previewing make no API calls.

Inputs are the corrected packets in
[`datasets/phd-applications-v4-recommendations-v2/`](datasets/phd-applications-v4-recommendations-v2/)
and the settings in [`configs/phd_eval_v1.json`](configs/phd_eval_v1.json).
Only the Computer Science PhD opportunity is implemented. The CVs have no
teaching, SQL, awards or proposed-research content, so they do not support the
fellowship, research-assistant or teaching-assistant opportunities.

## What a prompt contains

```sh
python3 -m phd_eval preview --condition cleared --task advance --format rationale
```

- **System message:** the shared system message, with the committee named as
  "a Computer Science PhD admissions committee".
- **User message, in order:** the opportunity description and selection
  criteria; the CV; the three recommendation summaries; the record block; the
  task prompt.
- **Record block:** the heading `INSTITUTIONAL RECORD` followed by one condition
  wording. For one applicant, task and format, this block is the only text that
  differs between conditions. A test enforces that.
- **Not in the prompt:** the internal applicant identifier, CV tier, pathway and
  every other analysis label.

Each of the three prompts (overall quality, advance, final decision) is a
separate request, as in the reference audit. The `rationale` format adds the
rationale instruction and puts `"rationale"` first in the requested JSON.

## Departures from the design document

All prompt, opportunity and condition text is copied verbatim except:

1. **Pending condition.** The phrase "shortly before the application review, "
   was removed from both wordings. Review is in 2026-11, and 24 applicants
   finished their only degree in 2026-05, so a course-assignment allegation
   shortly before review is impossible for them. "In 2026" is true for all 100
   applicants and keeps a single wording for everyone. The original wordings
   are saved in the config under `design_document_departures`.
2. **Placement.** The document does not say where the condition text goes. It
   is placed at the end of the application under a neutral heading that also
   fits the registrar control. Set `record_position` to `after_cv` to move it.
3. **Placeholders.** `next_stage` is "faculty interview", `offer_verb` is
   "admit this applicant", and the decision words are "admit" and "reject".
4. **Applicant identifier.** The line `Applicant PHDv3-…` is removed from the
   CV and the recommendation section because it encodes the sampling seed.

## Design size

The design is fully crossed within applicant: 100 applicants × 11 conditions ×
2 wordings × 3 prompts × 2 formats = 13,200 requests per model for one repeat.
Requests are sent in a seeded random order so that changes at the provider
during a run are not aligned with condition.

The reference audit ([arXiv 2405.04412](https://arxiv.org/abs/2405.04412)) ran
repeated trials per prompt and found the variance stabilized at about 40. Use
`--repeats` to add trials. Its prompt check was that scores separate inputs
that should score differently; the analogue here is that clean-record scores
rise from weak to borderline to strong CVs, which `collect` reports.

## Steps

1. **Pilot plan.** Five applicants per CV tier, clean and two other conditions:

   ```sh
   python3 -m phd_eval plan --out runs/pilot --per-tier 5 \
     --conditions clean,cleared,responsible --repeats 3
   ```

2. **Run one model.** The key is read from `EVAL_API_KEY` and is never saved.
   Any endpoint that implements `POST /chat/completions` works; set
   `EVAL_BASE_URL` or `--base-url` for a provider other than OpenAI.

   ```sh
   export EVAL_API_KEY=...
   python3 -m phd_eval run --plan runs/pilot --label "GPT-5.5" --api-model MODEL_ID
   ```

   `--label` is the name used in results. `--api-model` is the identifier the
   endpoint expects; the planned models in the config have it left blank. No
   sampling parameters are sent unless you add them, for example
   `--param temperature=1 --param max_tokens=300`. A run can be stopped and
   restarted: requests with a valid saved reply are not sent again, and failed
   or unparseable ones are retried on the next run.

3. **Export.**

   ```sh
   python3 -m phd_eval collect --plan runs/pilot
   ```

   `results.csv` has one row per request and model, with the parsed score,
   the decision coded 1 or 0, and the analysis labels. `summary.json` gives
   reply validity, clean-record scores by CV tier, and each condition's mean
   paired difference from the same applicant's clean record. The summary is a
   first look, not the analysis.

4. **Full plan.** `python3 -m phd_eval plan --out runs/main --repeats N`, then
   run each model against it with its own label.

`runs/` is ignored by git. A plan pins the config and every packet hash, and a
run stops if either changed.

## Open choices

- **Analysis.** The reference audit used mixed-effects models with a random
  effect for the manipulated unit. Here the natural unit is the applicant:
  condition as a fixed effect against clean, applicant as a random effect,
  fitted per model and prompt, with wording and format as factors.
- **CV tier.** Tiers are CV-only, and letters are assigned separately, so
  they can pull the other way (one strong-CV applicant has two limited
  letters). Each model's clean-record score is a better measure of perceived
  strength than the tier label.
- **Letter headers.** Each summary shows its strength level as a labeled field.
  That was a requested field; it is a strong signal and worth a look in the
  pilot rationales.
- **Course projects.** Every applicant lists a 2026 course project and one
  letter comes from that project's instructor, so a model may connect the
  alleged assignment to them. The rationale format will show whether it does.
