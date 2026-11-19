# Fellowship evaluation: readiness and Claude Code handoff

Status: offline preparation only. No evaluation calls or spending are approved.
Reviewed on 19 November 2026 against `main` at
`c1e30a216a79da85e34ddc6bb5015ccafc57e57f`.

## Readiness decision

The approved fellowship v2 bank supports an extension of the original
11-condition experiment. No substantive regeneration need was found. Keep the
existing PhD inputs and results. The fellowship applications describe a different
population and different evidence, so a difference between opportunities cannot
be attributed solely to the opportunity label.

| Study-plan criterion | Evidence checked in the fellowship bank |
| --- | --- |
| Intellectual Merit | Academic preparation, completed contributions and a proposed study |
| Broader Impacts | Beneficiaries, activities, delivery, access and assessment; prior activities where available |
| Preparation, initiative, independence and collaboration | Dated work, individual responsibilities, deliverables and source-linked supervisor observations |
| Intellectual ability | Undergraduate GPA, relevant undergraduate and graduate grades, supported awards where present |
| Proposed research and prior achievements | Question, rationale, contribution, method, comparison, evaluation, feasibility and limitations; separately identified completed outputs |

The full-bank verification and audit passed on the reviewed source. There are
100 applicants: 30 weak, 40 borderline and 30 strong, including ten designated
mixed cases. All are enrolled in February 2026 and at the November 2026 review.
Completed academic and work evidence is dated no later than December 2025.
The six-month proposed studies fit within enrollment. These dates permit the
original course-assignment conditions without inventing a new allegation.

The system template matches the PhD template. The opportunity criteria match
the local research plan. The overall-quality wording matches apart from
paragraph spacing. The latest source check ran 180 tests: 177 passed and three
PDF-extraction tests skipped because `pdftotext` was unavailable. A separate
`pypdf` extraction checked all 12 TA/fellowship/RA source passages and the PDF
hash; they matched. PhD, TA, fellowship and RA dataset verification also passed.

Four complete fellowship packets were read for this review: the middle
identifier among non-designated applicants in each tier, plus the first
identifier in the lower-GPA/substantive-research mixed group:

- Weak: `FEL-v2-456-01320`.
- Borderline: `FEL-v2-456-00451`.
- Strong: `FEL-v2-456-00656`.
- Mixed strong: `FEL-v2-123-00106`.

The packets distinguish proposed work from completed achievements. They contain
plausible differences in the adequacy of research methods and impact assessment.
A weak researcher's label can coexist with strong evidence on other dimensions;
these are provisional multi-criterion labels, not GPA ranks. Strong profiles need
not have publications. The labels still require empirical calibration from clean
scores, and the bank has not received independent human validation.

Minor doubled punctuation occurs in 71 packets, mostly at the end of prior
activity descriptions. It is a cosmetic renderer issue, not a reason to regenerate
the bank. Preserve the published bytes for this proposed extension. A later
punctuation correction would require a documented new release or explicit,
uniformly applied transformation, never an undisclosed edit to frozen inputs.
Finite templates, synthetic supervisor evidence and the dated record snapshot
also limit realism. Automated verification does not resolve those limits.

## Why an adapter is required

`fellowship_applicants` creates applicants, not treatment runs. Its exported
`evaluator_inputs.jsonl` contains only the quality question. `condition: null`
means no assigned record condition; it is not the clean treatment. All 100 base
previews also include an internal applicant identifier. The optional record
helper uses `ACADEMIC INTEGRITY RECORD`, whereas the actual PhD experiment used
the neutral heading `INSTITUTIONAL RECORD`.

The existing `phd_eval` loader expects a different manifest, PhD metadata, two
identifier lines and a recommendation section. Merely changing its dataset path
will not produce a valid fellowship experiment. None of these facts invalidates
the applicant bank; they define the remaining offline implementation work.

## Prompt to give Claude Code

You are preparing the fellowship extension in `ajay-cogsci/llm-exoneration-project`.
Do the offline work below. Stop with reviewable outputs. Do not make generation
or evaluation API calls. Do not start a smoke test. Do not infer a budget from
earlier PhD or ablation approvals.

### 1. Inspect and protect the existing study

1. Fetch `origin`. Start from current `origin/main` in an isolated branch named
   `codex/fellowship-eval-prep`. Preserve any unrelated worktree changes.
2. Read `README.md`, `EVALUATION.md`, `FELLOWSHIP_METHOD.md`, this handoff, the
   fellowship dataset README, and the completed PhD analysis summary.
3. Record the starting commit and hashes of protected files. Keep published
   datasets, original PhD configs, original harness and old results unchanged.
   Do not run applicant generation. Do not rename or remove the four PhD packages.
4. Use only `datasets/fellowship-applicants-v2/` for applicant evidence. Validate
   its manifest, checksums and source facts before assembling prompts.

### 2. Implement a separate fellowship evaluation entry point

Create a small adapter with a documented CLI and
`configs/fellowship_eval_v1.json`. Reuse existing pure functions where appropriate.
Keep the original `phd_eval` behavior unchanged. Do not invent missing PhD fields
or add fake recommendation sections to satisfy its loader. If the existing
interfaces force a change to frozen code, explain that limitation and stop with
the proposed diff before making that change.

The current config validator accepts `version: phd-eval-v1` only. Distinguish the
schema identifier from the opportunity identifier. Either reuse that schema
explicitly with fellowship metadata or define and validate a separate adapter
schema. Do not silently bypass validation or label fellowship outputs as PhD.

Use `application_manifest.json`, `profiles.jsonl` and `applications/*.txt` from
the fellowship bank. Keep each applicant's substantive packet identical across
all requests. Strip only its exact `Applicant FEL-v2-...` header. Assert that the
identifier, tier, sampling metadata and rubric labels never enter a prompt.
Keep the original packet hash and the transformed evaluator-text hash.

Copy these elements exactly from `configs/phd_eval_v1.json`:

- All 11 condition objects, including both wordings and the corrected pending
  wording. Do not copy the superseded pending sentence from the PDF.
- The system-message template, including the no-inference sentence.
- All three task templates, both format instructions and their JSON fields.
- The neutral `INSTITUTIONAL RECORD` heading, placed after the complete
  application and before the task.
- Empty request parameters and the saved order seed.

The condition IDs are:

```text
clean
pending
responsible
cleared
dismissed
withdrawn
exonerated_on_appeal
neutral_control
exonerated_acknowledged
responsible_rehabilitated
procedural_reversal
```

Use the exact fellowship description and criteria from
`fellowship_applicants/plan.py`. Use these proposed role substitutions, and show
them for review before calls:

```json
{
  "committee_name": "the Graduate Research Fellowship Selection Committee",
  "next_stage": "final fellowship selection review",
  "offer_verb": "award this applicant the fellowship",
  "yes_word": "award",
  "no_word": "decline"
}
```

The committee name already appears in the approved base inputs. The remaining
values are explicit proposal choices, not requirements from the source plan.
Do not invent an interview requirement. Keep `advance_score`/`advance` and
`decision_score`/`decision`; validate `yes`/`no` and `award`/`decline` correctly.
The collected score must always refer to the task's stated 0–100 score field.

### 3. Plan and verify offline

Prepare a new plan in `runs/fellowship/main/`. Never overwrite an existing plan.
Use 100 applicants × 11 conditions × 2 wordings × 3 tasks × 2 formats × 1 repeat:
**13,200 requests per model**. This count is not approval to send those requests.
Keep a seeded random request order, frozen inputs and resumable response records.

Run the existing offline suite and applicant checks:

```sh
python3 -m unittest discover -s tests
python3 scripts/verify_datasets.py
python3 -m fellowship_applicants verify --out datasets/fellowship-applicants-v2
python3 scripts/audit_fellowship.py --out datasets/fellowship-applicants-v2
```

Report skips. If PDF extraction is unavailable, check the source hash and compare
the source passages through an available extractor; do not call skipped tests
passes. Add focused adapter tests that establish:

- Exactly 13,200 unique requests, balanced across every design dimension.
- Complete agreement of condition strings with the original PhD config.
- For a fixed applicant, wording, task and format, only the institutional-record
  block differs across conditions. Validate this for all 100 applicants.
- No identifier or researcher-label leakage; no unresolved placeholders.
- Enrollment fits the incident and review dates. The fixed record remains the
  same under all conditions, including those mentioning sanctions.
- Correct score and decision parsing for every task and format.
- Resumption skips valid replies, preserves all attempts, rejects changed
  settings under a reused label, and accounts for missing/failed requests.
- Original PhD behavior and all protected hashes remain unchanged.

Do not send `evaluator_inputs.jsonl` directly to a provider. Do not treat its
`condition: null` as a clean baseline.

### 4. Deliver review material and stop

Provide complete assembled clean and cleared prompts for the three tier examples
listed above. Show both wordings, all three task suffixes and both format
instructions. Also provide an exact diff against the PhD prompt components,
separating the necessary application/opportunity changes from shared wording.

Write a run proposal with model labels, API IDs, parameters, concurrency,
retry limits, request counts and estimated cost. A comparable candidate panel is
the five completed PhD models: GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT,
Llama 4 Maverick and Qwen3-32B. This is a proposal, not an approved panel.
Read IDs and request settings from saved `runs/main` records. Do not guess missing
settings or replace an unavailable model silently. Verify availability and current
pricing against provider documentation before proposing paid work. Record model
and provider versions where available; later provider changes complicate
cross-opportunity comparisons.

Propose a bounded parse smoke test and a stratified clean-score calibration check
before the full run. A 20-request smoke test tests transport/parsing; it does not
validate the provisional tiers. Inspect clean-score ordering and floor/ceiling
behavior in calibration. Flag clean means below 15. Never tune or select the
applicant bank to obtain a desired exoneration result. Any revised protocol needs
its own frozen plan and approval before expansion.

Show separate cost estimates for smoke/calibration and completion. Use measured
prompt sizes and explicit assumptions about output length and retries. Require an
explicit dollar cap before calls; previous $10/$100 caps do not carry over.
The proposed cap enforcement must reserve for requests in flight and retries,
not merely notice that spending already exceeded the cap. Keep all attempts;
propose a finite retry policy rather than retrying until a desired response parses.

Use only the current `EVAL_API_KEY` environment variable and the OpenRouter base
URL `https://openrouter.ai/api/v1` after execution is approved. If the key is
missing then, ask the user to set it in their terminal. Never print, save, commit
or retrieve a key from chat history. Offline work requires no key.

Commit only the adapter, new config, tests and preparation documentation locally.
Check that protected files did not change. Report the branch, commit, checks,
preview paths and unresolved choices. Ask before pushing or merging this new
implementation. **Stop here for review and an explicit execution decision.**

### 5. Requirements for a later, separately approved run

After approval, retain raw replies and every retry. Report sent, valid,
unparseable and error counts plus cost per model. Report retries by condition,
and first-attempt validity separately from eventual validity. Track costs from
saved usage and provider accounting; stop within the approved cap.

Collect fellowship results separately from PhD results. Preserve the original
analysis questions: paired score differences against clean and neutral_control;
applicant-clustered 95% intervals; mixed-model sensitivity; prespecified cleared
and adverse contrasts; binary advance/award differences; tier, wording and format
checks. State multiplicity families and report corrected inference. Treat Llama's
format comparison cautiously given its prior prose in both formats. Do not run
an equivalence test without a chosen meaningful-difference threshold.

Use applicant IDs unique to the fellowship bank. Do not treat applicants across
opportunities as matched people, or wordings/formats as independent applicants.
Small differences require corrected intervals before being described as evidence
of an effect. Keep the absence of independent human validation explicit.

Save exports and analysis under `runs/fellowship/main/`. Copy the entire run,
including raw replies, to a dated backup under
`/Users/baileyhirota/Desktop/test/llm-exoneration-backups/`. Report that exact path.
Commit only approved code/configs, compact result exports and analysis artifacts.
Do not commit raw response dumps or secrets. Do not overwrite earlier results.
