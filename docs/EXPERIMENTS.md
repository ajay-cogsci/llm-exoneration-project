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
