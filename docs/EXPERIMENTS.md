# Experiments and current status

This index separates completed evidence from the next opportunity. Earlier
results remain available and are not pooled with a new run by default.

| Stage | Status | Inputs and results |
|---|---|---|
| PhD pilot | Completed for the seven-model panel | `runs/pilot/results.csv`, `runs/pilot/summary.json` |
| Original PhD full design | Five of seven planned models completed; 66,000 valid replies | [Written analysis](../runs/main/analysis/SUMMARY.md), `runs/main/results.csv`, `runs/main/summary.json` |
| No-inference-sentence ablation | Completed for three models and two arms | [Written analysis](../runs/ablation/analysis/SUMMARY.md); results in `runs/ablation/plan_A/` and `plan_B/` |
| Introductory-CS teaching assistant | Applicant generation completed; evaluation run not configured or approved | [100 graduate applicants, version 2](../datasets/ta-applicants-v2/), [method](../TA_METHOD.md), [verification](../VALIDATION.md). Retain the original 11 conditions, three tasks and two formats for the eventual evaluation. |
| Graduate research fellowship | Applicant generation completed; final v2 release approved on 18 November 2026; evaluation run not approved | [100 early-stage CS graduate applicants](../datasets/fellowship-applicants-v2/), [method](../FELLOWSHIP_METHOD.md), [audit](../datasets/fellowship-applicants-v2/audit_report.json). Allocation: 30 weak, 40 borderline, 30 strong and ten designated mixed cases. Earlier fellowship drafts and raw generation logs are not published. |
| Research assistant | Applicant generation completed; final v2 release approved on 18 November 2026; evaluation run not approved | [100 current CS graduate applicants](../datasets/ra-applicants-v2/), [method](../RA_METHOD.md), [audit](../datasets/ra-applicants-v2/audit_report.json). Allocation: 30 weak, 40 borderline, 30 strong and ten designated mixed cases. Earlier RA drafts and raw generation logs are not published. |

The full-design run used GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT,
Llama 4 Maverick, and Qwen3-32B. GPT-5.5 and Claude Sonnet 5.5 were included
in the pilot but have not completed the full design.

## Repository branches (consolidated 16 November 2026)

`main` is the canonical branch for completed work and current study documentation.
The former `codex/ta-prep` branch is synchronized with the approved files on
`main`. Its unapproved example packets, generation handoff and superseded
preparation notes have been removed. It does not contain an alternative TA
pipeline. No TA evaluation experiment is approved. Only explicitly approved
final changes should be published.

Before consolidation, the GitHub default branch was behind the experiments.
All six remote branch tips formed one ancestry chain ending at `70ae71a`; there
were no divergent tips or pull requests. The working tree was clean, all 72 tests
passed, and dataset verification succeeded without model calls. The user approved
fast-forwarding `main` and retiring the five superseded branch names.

| Branch | Tip at audit | What it contains | Disposition |
|---|---|---|---|
| `main` | `a449ac9` | Earlier PhD CVs and recommendation datasets; lacked the corrected evaluation inputs, harness and results | Updated to include the cleaned completed history; canonical branch. |
| `consistency-fixes-and-phd-eval` | `fc50788` | GPA/letter corrections, harness and completed seven-model pilot | Integrated into `main`; branch name retired. |
| `pilot-results` | `fc50788` | Exactly the same commit as the preceding branch | Duplicate name retired; pilot results retained on `main`. |
| `main-results` | `12214fb` | Adds the five-model full PhD run and analysis | Integrated into `main`; branch name retired. These are completed results, not disposable trial output. |
| `ablation-no-infer` | `811803d` | Adds the completed three-model, two-arm sentence ablation | Integrated into `main`; branch name retired. |
| `codex/phd-followup-prep` | `70ae71a` | All preceding work plus removal of the abandoned PhD follow-up and updated study/TA preparation notes | Cleaned state integrated into `main`; misleading temporary name retired. |

The abandoned 20-condition follow-up files have been deleted from the current
tree. Their creation and deletion remain in Git history; they are not an active
dataset, experiment or archive folder. The TA notes at consolidation commit
`ac2c596` were planning
requirements, not a prepared applicant bank or executable TA run.

Only branch names were retired. Results, local raw responses, and Git history
were retained. No experiment inputs or analysis outputs changed in consolidation.
Use experiment folders and this index to distinguish runs, rather than keeping
a permanent branch for each run. A future cleanup must recheck remote tips and
retain any branch that gained collaborator work.

At consolidation on 16 November, no TA-specific applicant bank or collaborator TA submission was found in the
six branch trees, pull requests, or current shared notebook and its comments.
This does not establish whether work exists in another clone, fork or document,
or whether a collaborator has read the existing results.

## File organization

- `configs/`: original study configurations; do not rewrite completed-run inputs.
- `analysis/`: analysis code for the completed PhD study and ablation.
- `TA_METHOD.md`: the single approved TA method and current generation scope.
- `FELLOWSHIP_METHOD.md`: the single approved fellowship method; the final applicant bank is `datasets/fellowship-applicants-v2/`.
- `RA_METHOD.md`: the single approved RA method; the final applicant bank is `datasets/ra-applicants-v2/`.
- `runs/`: historical outputs and local raw replies. Existing committed exports
  remain tracked; new raw logs and private human-pilot files remain ignored.
- `datasets/`: versioned applicant inputs. Keep the published versions intact.

The pilot, main study, and ablation answer different questions. Preserve their
outputs, raw responses, and provenance. A follow-up should use a separate run
directory after approval. Do not overwrite an old plan, delete completed results,
or treat repeated bridge conditions as additional independent applicants.

The Google Doc is the shared research notebook:
[LLM exoneration](https://docs.google.com/document/d/1dgZkwce8f8iXa1Nt0kmj7WIPqrdzxcMJCaYEYm7VQ2s/edit).
Exact executable PhD stimuli are in the versioned configs. The TA notes describe
preparation only and are not a runnable evaluation config.
