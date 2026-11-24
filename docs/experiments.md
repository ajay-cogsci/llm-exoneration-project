# Experiments

Each finished experiment has a folder in `results/` with its exports and a
written `SUMMARY.md`. Raw model replies are not committed; they are backed up
outside the repository by whoever ran the experiment.

| Experiment | Results | Design | Models | Cost |
|---|---|---|---|---|
| PhD full design | [`results/phd-main`](../results/phd-main/analysis/SUMMARY.md) | 100 applicants × 11 conditions × 2 wordings × 3 tasks × 2 formats = 13,200 requests per model | GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT, Llama 4 Maverick, Qwen3-32B | $62.58 |
| PhD "do not infer" ablation | [`results/phd-ablation`](../results/phd-ablation/SUMMARY.md) | Clean, cleared, pending, responsible × answer-only; with and without "Do not assume or infer details that are not stated." | Gemma 4 31B IT, Qwen3-32B, GPT-5.4 mini | $6.06 |
| Fellowship full design | [`results/fellowship-main`](../results/fellowship-main/analysis/SUMMARY.md) | Same as the PhD full design | Same five models | $72.82 |
| PhD pilot | `old/results/phd-pilot` | 15 applicants × 3 conditions × 3 repeats | The five above plus GPT-5.5 and Claude Sonnet 5.5 | $31.46 |

- **Inputs:** each harness and its inputs are described in [evaluation.md](evaluation.md). The applicant banks are described in [methods/](methods/).
- **Teaching assistant and research assistant:** their applicant banks exist (`data/ta`, `data/ra`), but there is no evaluation harness for them yet. A new one should copy `src/evaluate/fellowship_eval/` and keep the same 11 conditions, 2 wordings, 3 tasks and 2 formats.
- **Frontier models:** GPT-5.5 and Claude Sonnet 5.5 ran only in the pilot. Running them on the full design is the main open extension.

## Conventions

- **New folder per experiment:** use a new folder in `runs/` for every new experiment, and never write into a finished one.
- **Committing results:** when an experiment finishes, copy its compact exports (`results.csv`, `summary.json`, analysis) into `results/<name>/` and commit them. Back up the full run folder, raw replies included, outside the repository.
- **Comparing conditions:** compare conditions within an applicant (paired differences against `clean`). Results from different experiments or opportunities describe different applicants, so compare them descriptively only.
