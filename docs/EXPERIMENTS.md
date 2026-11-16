# Experiments and current status

This index separates completed evidence from the next opportunity. Earlier
results remain available and are not pooled with a new run by default.

| Stage | Status | Inputs and results |
|---|---|---|
| PhD pilot | Completed for the seven-model panel | `runs/pilot/results.csv`, `runs/pilot/summary.json` |
| Original PhD full design | Five of seven planned models completed; 66,000 valid replies | [Written analysis](../runs/main/analysis/SUMMARY.md), `runs/main/results.csv`, `runs/main/summary.json` |
| No-inference-sentence ablation | Completed for three models and two arms | [Written analysis](../runs/ablation/analysis/SUMMARY.md); results in `runs/ablation/plan_A/` and `plan_B/` |
| Introductory-CS teaching assistant | Offline preparation; no run configured or approved | [Preparation notes](TA_PREPARATION.md). Retain the original 11 conditions, three tasks and two formats; prepare suitable applicant evidence first. |
| Fellowship, research assistant | Not run | Opportunity drafts exist in the shared notes. Current PhD packets do not supply all needed opportunity-specific evidence. |

The full-design run used GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT,
Llama 4 Maverick, and Qwen3-32B. GPT-5.5 and Claude Sonnet 5.5 were included
in the pilot but have not completed the full design.

## Repository branches (consolidated 16 November 2026)

`main` is the canonical branch for completed work and current study documentation.
`codex/ta-prep` is the only preparation branch, for TA materials awaiting review.
No TA experiment is approved. Merge reviewed work back into `main` and retire its
preparation branch when finished.

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
dataset, experiment or archive folder. The TA notes at this commit are planning
requirements, not a prepared applicant bank or executable TA run.

Only branch names were retired. Results, local raw responses, and Git history
were retained. No experiment inputs or analysis outputs changed in consolidation.
Use experiment folders and this index to distinguish runs, rather than keeping
a permanent branch for each run. A future cleanup must recheck remote tips and
retain any branch that gained collaborator work.

No TA-specific applicant bank or collaborator TA submission was found in the
six branch trees, pull requests, or current shared notebook and its comments.
This does not establish whether work exists in another clone, fork or document,
or whether a collaborator has read the existing results.

## File organization

- `configs/`: original study configurations; do not rewrite completed-run inputs.
- `analysis/`: analysis code for the completed PhD study and ablation.
- `docs/TA_PREPARATION.md`: the next opportunity and its preparation requirements.
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
