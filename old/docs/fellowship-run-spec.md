# Fellowship evaluation: finalized setup and Claude Code handoff

Status: offline preparation finalized on 19 November 2026. No generation or
paid evaluation was run. A model panel and a new dollar cap remain unapproved.
Implementation is on local branch `codex/fellowship-eval-prep`; do not assume
these files are already on remote `main`.

## Frozen study choices

- Use all 100 published applications in `datasets/fellowship-applicants-v2/`.
- Preserve application bytes. Remove only the exact internal `Applicant FEL-v2-...`
  line during prompt assembly. Save original and transformed-text hashes.
- Use `fellowship_eval/` and `configs/fellowship_eval_v1.json`. Applicant-generation
  config `configs/fellowship.json` is not an evaluation config.
- Copy all 11 condition objects, both wordings, the system template, task templates,
  both formats, empty request parameters, and order seed from `configs/phd_eval_v1.json`.
- Retain the sentence `Do not assume or infer details that are not stated.`
- Put `INSTITUTIONAL RECORD` after the complete application and before the task.
- Use the corrected PhD pending wording. Do not restore the superseded PDF phrase.
- Preserve the original PhD harness, datasets, configurations and results.

| Design dimension | Values |
| --- | --- |
| Applicants | All 100 published fellowship v2 applicants |
| Conditions | clean, pending, responsible, cleared, dismissed, withdrawn, exonerated_on_appeal, neutral_control, exonerated_acknowledged, responsible_rehabilitated, procedural_reversal |
| Wordings | 1 and 2 |
| Tasks | quality, advance, decide |
| Formats | answer_only, rationale |
| Repeats | 1 |
| Size | 13,200 planned requests per model; 66,000 for a five-model panel, before retries |

The fellowship opportunity description and criteria come verbatim from
`fellowship_applicants/plan.py`. The opportunity substitutions are:

```json
{
  "committee_name": "the Graduate Research Fellowship Selection Committee",
  "next_stage": "final fellowship selection review",
  "offer_verb": "award this applicant the fellowship",
  "yes_word": "award",
  "no_word": "decline"
}
```

Quality returns `score`; advance returns `advance_score` and `advance: yes/no`;
final decision returns `decision_score` and `decision: award/decline`.
The score column always uses the task's requested 0–100 field. The rationale
format retains the original three-sentence instruction and first JSON key.
No interview requirement or recommendation letters are invented.

## Tier and review decision

Keep the published 30 weak / 40 borderline / 30 strong labels as **original
provisional generation labels**. The CSV calls this field `cv_tier` for PhD
analysis compatibility; it is the fellowship generation tier, not a CV-only
rating or a human-validated category.

One researcher reviewed condensed examples: the PhD ordering matched the
existing labels; the strongest fellowship example ranked first, while the other
two were close. This supports an informal plausibility check. It is not an
independent two-rater review or validation of all 100 records.

The proposed 30/25/25/20 research/academics/proposal/impact rubric was not applied
to the bank. No new numerical scores or tier cutoffs are asserted. The primary
estimand is the mean within-applicant condition contrast over all 100 applicants.
Original-tier results are descriptive sensitivity analyses. Also examine strength
using each model's own clean scores with the cross-fitting used in the PhD
analysis; reusing the same clean measurement on both sides can create spurious
moderation. Do not change applicant selection or labels after seeing allegation
results. Do not insert numerical researcher weights into evaluator prompts.

## Offline commands and safeguards

```sh
python3 -m unittest discover -s tests
python3 scripts/verify_datasets.py
python3 -m fellowship_applicants verify --out datasets/fellowship-applicants-v2
python3 scripts/audit_fellowship.py --out datasets/fellowship-applicants-v2
python3 -m fellowship_eval preview --condition clean --task advance --format answer_only
```

A plan has been prepared locally in `runs/fellowship/main/`. It has no replies.
For an existing plan, run:

```sh
python3 -m fellowship_eval verify-plan --plan runs/fellowship/main
```

Only if that directory is absent, create it:

```sh
python3 -m fellowship_eval plan --config configs/fellowship_eval_v1.json \
  --out runs/fellowship/main --repeats 1
```

Plans refuse overwrite. Config, design, implementation and dataset hashes are
frozen. Original and identifier-stripped application hashes are stored separately.
The loader checks every published checksum. All condition changes are tested to
be confined to the institutional-record block for every applicant/task/format.

Preparation diagnostics and assembled prompt examples are under
`runs/fellowship/prep/` locally. These directories are ignored by Git. On another
clone, recreate the plan from the same reviewed implementation; do not copy an
old plan while substituting new code or data. Tests use fake clients only.

The preparation check ran 192 tests: 189 passed and three source-PDF tests
skipped because `pdftotext` was unavailable. A separate `pypdf` check verified
all 12 source passages and the source PDF hash. Dataset verification, fellowship
verification and the fellowship audit passed. All 2,244 protected tracked files
were byte-identical. The full plan contains 13,200 unique requests and zero saved
evaluation replies. There are 72 complete clean/cleared prompt previews. See
`runs/fellowship/prep/verification.json` for the local check record.

### Request and spending policy

The adapter sends only `model` and `messages`; no sampling parameters are added.
Use one process per plan. The runner prevents simultaneous model processes while
permitting request concurrency within one model. Proposed concurrency is 1 for
smoke tests, then 4. Prior PhD response records confirm empty parameters but do
not record concurrency, so exact concurrency equivalence is not claimed.

There are at most two recorded attempts per request, including transport failures.
There are no hidden HTTP retries. Valid replies are skipped on resumption. Every
attempt is retained. Never retry until a desired score appears or change parsing
to accept a particular treatment's reply. A model label cannot be reused with a
different API ID, request cost ceiling or retry policy.

The cumulative cap covers every model in this plan, including smoke tests,
clean calibration and retries. `--request-cost-ceiling-usd` is a **verified upper
bound per attempt**, not an average expected cost. Before sending each request,
the runner reserves that amount, including requests already in flight. It then
replaces the reservation with reported usage cost. Missing billing, a timeout,
an interrupted request or an exceeded ceiling stops further dispatch. Preserve
unresolved reservations until provider accounting resolves them. The budget is
frozen in `budget.json`; do not increase it without fresh authorization.

Use a dedicated OpenRouter key with an appropriate provider-side spending limit
for a hard cap. Confirm that the key is not shared with unrelated jobs. The local
reservation check depends on a correct upper bound and provider billing. Compute
that bound from current documented input/output/context maxima and all billable
rates, including reasoning tokens and request charges where applicable. Empty
parameters must remain empty. If a finite conservative bound cannot be established
without setting a token limit, stop and present the change for approval. Do not
silently add `max_tokens` or `temperature`, or call an average-cost watchdog a
hard cap. If verification is impossible, stop before paid calls.

The runner reads only `EVAL_API_KEY`, uses `https://openrouter.ai/api/v1`, and
rejects a conflicting `EVAL_BASE_URL`. It never falls back to another key.
No credential is needed for offline work.

## Prompt to paste into Claude Code

```text
Work in ajay-cogsci/llm-exoneration-project. Run the finalized fellowship
extension after the execution gate below. Preserve the original PhD experiment.

Read docs/FELLOWSHIP_EVALUATION_HANDOFF.md, EVALUATION.md, FELLOWSHIP_METHOD.md,
configs/fellowship_eval_v1.json, and fellowship_eval/ before doing anything paid.
Use the local codex/fellowship-eval-prep checkout containing these files. Do not
reset it to origin/main or discard uncommitted preparation changes. If the
adapter is missing on another machine, obtain the reviewed preparation files.
Do not reconstruct them from this prompt or silently change study wording.

1. Verify the setup offline.
Run the documented test suite, dataset verification and fellowship audit.
Report skips accurately. Verify runs/fellowship/main if it exists. Otherwise
create that plan using the documented command. Expect 100 applicants and
13,200 unique requests per model. Confirm there are no existing unexpected
responses. Keep all 11 conditions, two wordings, three tasks, two formats and
one repeat. Preserve published applications and original provisional labels.
Do not regenerate, rescore or rebalance the bank. Do not insert numeric rubric
weights into prompts. Show the resolved clean advance and final-decision prompts.

2. Resolve the execution gate before any paid request.
Recommend the same five models that completed the PhD full design:
Gemma 4 31B IT -> google/gemma-4-31b-it
Qwen3-32B -> qwen/qwen3-32b
Llama 4 Maverick -> meta-llama/llama-4-maverick
GPT-5.4 mini -> openai/gpt-5.4-mini
Gemini 3.8 Flash -> google/gemini-3.8-flash
These are historical recorded IDs, not a claim of current availability.
Check availability and prices against official provider documentation. Do not
substitute an unavailable model. Estimate smoke, clean calibration and full-run
costs using the actual prompts, expected output lengths and retry allowance.
Record assumptions and conservative per-request upper bounds separately.
Ask the user to approve the model panel and a new total dollar cap. Earlier
PhD and ablation caps do not apply. If the current session already explicitly
approves this fellowship panel and cap, do not ask again. Configure or confirm
the dedicated provider-side key limit and the documented local reservations.
Use only the current EVAL_API_KEY environment variable. If missing, ask the user
to set it in their terminal. Never retrieve old keys from chat, print a key,
write it to a file or commit it. Wait for required authorization before calls.

3. Run approved models sequentially, cheapest first.
Use the documented run command below with the approved cap and the verified
worst-case request cost. Use no extra sampling parameters. First send at most
20 requests with concurrency 1. Inspect every saved reply in that smoke test,
including score fields, decision vocabulary, rationales and errors.
Stop if transport, billing or prompt semantics are wrong. If replies are sound,
complete clean-record cells using --conditions clean in this same plan. This
is 1,200 clean cells per model, and is part of the 13,200 total. Report score
ranges, clean means by original tier, floor/ceiling rates and near-constant
scoring. A nonmonotone provisional tier ordering is a finding; do not retune
applicants to force it. Pause if the evaluator cannot distinguish applicants.
Then remove --conditions and --limit, use concurrency 4, and complete the
approved full design. Resumption allows at most two total attempts per request.
Do not loop indefinitely. Report exhausted requests as incomplete. Stop on any
budget/billing warning; do not bypass it. Report spend and progress after each
model and at useful intervals during long runs. Do not start TA or RA work.

4. Collect and analyse separately from PhD.
Run python3 -m fellowship_eval collect --plan runs/fellowship/main.
Keep raw replies and attempt_starts.jsonl. Report attempts, distinct requests,
valid, unparseable, errors, missing, exhausted, and reported/unresolved cost by
model. Report first-attempt validity and retries by condition. Analyse both
results.csv and first_attempt_results.csv; do not replace one with the other.
Use matched applicant/wording/format/repeat cells for contrasts when replies
are missing, and report denominators. Never code a parse failure as score zero.
Use paired applicant-level differences and applicant-clustered 95% intervals
against clean and neutral_control. Fit score ~ condition + wording + format
with an applicant random intercept as sensitivity. Preserve PhD contrast
families and multiplicity correction; name the correction used for intervals.
Use award/decline for fellowship binary decisions. Report original-tier results
as descriptive and use cross-fitted own-clean scores for strength moderation.
Flag clean means below 15 and ceiling compression. Inspect wording/format and
rationales linking allegations to listed work. Mark Llama's format comparison
cautiously because its PhD replies included prose in both formats.
Do not run equivalence tests. Do not claim a small difference is established
unless its corrected interval excludes zero. Separate verified observations
from interpretation. The three-example sanity check is not bank validation.
Do not treat PhD and fellowship applicants as matched people or attribute
cross-opportunity differences solely to the opportunity name.
Write fellowship-specific analysis code, a tidy estimate CSV, figures and a
short summary under runs/fellowship/main/analysis/. Reuse PhD analysis helpers
where appropriate without changing published PhD results or overwriting files.

5. Preserve and report.
Copy the whole runs/fellowship/main folder, including raw replies, to a dated
folder under /Users/baileyhirota/Desktop/test/llm-exoneration-backups/. Verify
copied hashes and report the exact backup path. Report branch, source commit,
resolved model/provider IDs, cost, completeness, errors, limitations and paths.
Commit only reviewed code/configs, compact exports and analysis outputs to the
working fellowship branch. Exclude secrets and large raw dumps. Ask before
pushing or merging. Do not overwrite earlier results or delete old datasets.
```

After panel and cap approval, the run command is:

```sh
python3 -m fellowship_eval run --plan runs/fellowship/main \
  --label "$MODEL_LABEL" --api-model "$MODEL_ID" \
  --budget-cap-usd "$FELLOWSHIP_CAP_USD" \
  --request-cost-ceiling-usd "$VERIFIED_REQUEST_CEILING_USD" \
  --limit 20 --concurrency 1 --max-attempts 2
```

Set the four named shell variables to approved, non-secret values. The credential
stays in `EVAL_API_KEY`. For clean calibration replace `--limit 20` with
`--conditions clean` and use `--concurrency 4`. For completion remove that filter.
Do not change the retry limit or request ceiling under an existing label.

## Verified limits of this setup

All applicants are fictional. The bank supports a controlled comparison within
fixed packets. Template reuse, synthetic supervisor evidence, limited proposal
topics and unvalidated scientific novelty constrain external validity. The
December 2025 evidence snapshot and graduate enrollment accommodate the 2026
record conditions; no later achievement or actual damage to the CV is invented.
Minor doubled punctuation is preserved from the published release.

A provider/model may have changed since the PhD experiment. Record model and
provider identifiers and dates. Historical prices and IDs do not guarantee a
comparable current service. The original PhD code and results remain unchanged.
