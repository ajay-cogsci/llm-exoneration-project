# Claude Code handoff: TA extension

Paste the prompt below into Claude Code. It permits offline preparation now.
It does not authorize model calls. Review `TA_REVIEW.md` with the study owner
before turning its examples into a full applicant bank.

---

Work in `ajay-cogsci/llm-exoneration-project`, branch `codex/ta-prep`.
The local checkout is `/Users/baileyhirota/Desktop/test/llm-exoneration-project`.
Check the working tree before edits. Preserve work that you did not create.

The repository has two branches. `main` contains the completed PhD work and
current study documentation. `codex/ta-prep` contains TA materials awaiting
review. Earlier branches were integrated and retired. Do not recreate them.

Read these files first:

1. `README.md`, `docs/EXPERIMENTS.md` and `EVALUATION.md`.
2. `docs/TA_PREPARATION.md` and `docs/TA_REVIEW.md`.
3. `configs/phd_eval_v1.json`, `phd_eval/design.py` and `phd_eval/run.py`.
4. `runs/main/analysis/SUMMARY.md` and `runs/ablation/analysis/SUMMARY.md`.

The three TA examples are new fictional review drafts. They are not a validated
dataset or a collaborator's submission. First check for newer collaborator
material in the remote branches and pull requests. Report what you find.
Do not claim a collaborator read the results based only on commit ancestry.

## Current authorized stage: offline preparation

Do not call any model API. Do not generate a full applicant bank yet.
Do not start an evaluator run, smoke test or human recruitment.
Earlier PhD and ablation budgets do not apply to TA work.

Confirm that the study owner approved the wording and eligibility in
`docs/TA_REVIEW.md` before using them as fixed inputs. Without that approval,
inspect the interfaces, prepare a minimal implementation proposal, and stop
with an explicit list of remaining decisions. Do not silently approve drafts.

Keep the original 11 condition IDs and both wordings byte-for-byte:
clean, pending, responsible, cleared, dismissed, withdrawn,
exonerated_on_appeal, neutral_control, exonerated_acknowledged,
responsible_rehabilitated, procedural_reversal.

Keep all three tasks and both formats. Keep the original system template,
including “Do not assume or infer details that are not stated.” Change only the
approved opportunity text and role placeholders. Do not restore the abandoned
20-condition PhD follow-up or add an allegation/control in this TA extension.

Preserve the original PhD configs, harness, datasets and results. Do not repoint
the PhD default config to TA inputs. Put TA code, inputs and outputs in clearly
named separate locations. Reuse existing pure prompt and parser functions where
possible. Present any required change to shared harness code before making it.

The current loader expects PhD-specific fields and packet manifests. Do not
invent research facts just to satisfy that loader. Propose an explicit TA adapter
or schema mapping. If a legacy export column such as `cv_tier` is reused, document
that it represents TA preparation and is not the original PhD rubric.

Before constructing a bank, propose a TA fact schema and reproducible quality
rubric. Cover coursework, teaching/tutoring or explicit no experience, observed
communication, recommendations, teaching interest, availability and eligibility.
Keep the same packet fixed across all record conditions. Keep tier labels out
of prompts. All applicants must be eligible; vary relevant preparation instead.
Include plausible mixed profiles, not just copies of the three examples.
Do not tune inputs until models produce a desired allegation penalty.

Keep education dates compatible with the unchanged early-2026 incident.
Keep reported grades and GPA snapshots before that incident. Do not connect the
allegation to a named course, project or writer when the record does not do so.
Use anonymous fictional institutions. State that the disclosure is an experimental
manipulation, not a claim about routine institutional record-sharing.

Use a new versioned TA dataset with facts, packet hashes and a manifest.
Define the applicant count and tier allocation before generating the full bank.
One hundred applicants is a proposal, not an approval. It would imply
100 × 11 × 2 × 3 × 2 = 13,200 evaluator requests per model for one repeat.

Run only offline checks during this stage:

```sh
python3 -m unittest discover -s tests
python3 scripts/verify_datasets.py
```

The original baseline is 72 passing tests. Add targeted tests for any new adapter
or schema. Check these properties before proposing a run:

- Frozen PhD prompts and datasets remain unchanged.
- Every applicant supports every condition's dates.
- Each intended design cell occurs exactly once per repeat.
- Only the record block changes across conditions for a fixed applicant/task/format.
- IDs, tiers and other analysis metadata stay out of prompts.
- All role placeholders resolve. Both hire decisions parse in both formats.
- Rendered packets match their facts, grades, dates and recommendation evidence.
- Generated wording, if later approved, changes no fixed facts.

Return a diff, validation results, full sample prompts and the proposed next step.
Commit offline work on `codex/ta-prep`. Do not merge into `main` or push without
the study owner's instruction for that handoff session.

## Later stage: requires separate explicit authorization

Before any API call, obtain approval for the final inputs, dataset size, model
panel and exact IDs, request settings, concurrency, retry policy and hard cap.
Check current provider documentation and price estimates then. Historical labels
and costs do not establish current availability or a TA budget.

Read keys only from the environment. Never print, persist or commit a key.
If a required key is missing, ask the owner to set it in the terminal.
Do not reuse a key pasted into an old conversation or search history for one.

Before launching, verify that the budget mechanism accounts for retries and
requests in flight. A watchdog that stops after recorded usage reaches the cap
does not guarantee a hard cap. Report any limitation and reserve sufficient
headroom before dispatch. Keep raw attempts, first-attempt parse outcomes,
provider usage and checkpoints. Do not discard failed or unparseable attempts.
Some transport retries occur inside the original client; surface their accounting
limitations rather than treating saved JSONL rows as every HTTP attempt.

Use a separate TA run directory. Start with the specifically approved smoke-test
size. Report parse failures, errors, actual spend and clean-score separation by
TA tier before expansion. A successful smoke test does not authorize expansion
beyond the agreed scope. Pause at the agreed cap or material validity problem.

Use paired applicant-level comparisons for condition differences and cluster
intervals by applicant. Wordings and formats are repeated measurements, not new
applicants. Preserve the original contrasts versus clean and neutral_control,
and the original mixed/paired, binary-decision and heterogeneity analyses where
applicable. State multiplicity families and interval corrections in advance.
Flag floor/ceiling cells and report retry selection checks. Do not call a small
difference an effect unless its corrected interval excludes zero.

Do not claim an equivalence result without a chosen meaningful-difference margin.
Do not pool PhD and TA applicants or infer human cognitive differences from model
outputs alone. Compare opportunities descriptively unless a joint analysis was
specified in advance. Preserve all raw replies and create an external backup.

For Codex validation afterwards, return the exact commit, configuration hashes,
dataset manifest, plan counts, model/settings records, all-attempt counts, costs,
result paths, backup path, and failures or deviations. Separate file-verified
facts from interpretation. Wait for the study owner's instruction before pushing
or merging the experiment results.
