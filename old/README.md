# old/

Nothing here is needed to use the current data, run an evaluation or reproduce
the analyses. It is kept so that the project's history can be checked.

| Path | What it is |
|---|---|
| `datasets/phd-cvs-v2-rubric-v1/` | First release of the 100 PhD CVs. The current CVs (`data/phd/cvs`) correct 19 GPAs in it. |
| `datasets/phd-applications-v3-recommendations-v1/` | First release of the PhD packets with letters. The current packets (`data/phd/applications`) change 11 letters in it. |
| `datasets/sample-100-resume-generated/` | The original 150-record PhD sample, built with an earlier quintile-based sampler. |
| `phd_revisions/` | Code that produced the GPA and letter corrections. |
| `configs/` | Settings for the above (`phd.json`, `phd_gpa_consistency_v1.json`, `phd_recommendations_v1.json`) and the ablation's config without the "do not infer" sentence (`phd_eval_v1_no_infer.json`). |
| `scripts/verify_phd_history.py` | Rebuilds the current PhD data from the first releases and requires a byte-for-byte match (README and checksum files excepted). |
| `scripts/run_rubric_validation.py` | Runner used to validate the rubric on the original sample. |
| `scripts/fellowship-run/` | Tooling written for the fellowship run: unattended driver, gap fill, parallel per-model plans, cost re-settlement. Reusable for future paid runs. |
| `results/phd-pilot/` | PhD pilot exports (7 models, 15 applicants). |
| `results/phd-ablation/` | Ablation plans and secondary tables; the summary is in `results/phd-ablation/`. |
| `analysis/ablation.py` | Analysis script for the ablation. |
| `docs/fellowship-run-spec.md` | The specification the fellowship run followed. |
| `tests/` | Tests for the code above: `python3 -m unittest discover -s old/tests`. |

```sh
python3 old/scripts/verify_phd_history.py   # re-derive the current PhD data from its first release
python3 -m unittest discover -s old/tests     # tests for the archived code
```

## Path changes on 24 November 2026

The repository was reorganised on 24 November 2026. Frozen run plans
(`runs/*/config.json`) and older commits use these earlier paths. The files
themselves are byte-identical, except for README, METHOD and checksum files,
whose paths and links were updated.

| Old path | New path |
|---|---|
| `datasets/phd-applications-v4-recommendations-v2/` | `data/phd/applications/` |
| `datasets/phd-cvs-v3-gpa-consistency-v1/` | `data/phd/cvs/` |
| `datasets/fellowship-applicants-v2/` | `data/fellowship/` |
| `datasets/ta-applicants-v2/` | `data/ta/` |
| `datasets/ra-applicants-v2/` | `data/ra/` |
| `phd_resumes/`, `phd_recommendations/`, `ta_applicants/`, `fellowship_applicants/`, `ra_applicants/` | `src/generate/…` |
| `phd_eval/`, `fellowship_eval/` | `src/evaluate/…` |
| `runs/main/` exports, `runs/fellowship/main/` exports, `runs/ablation/analysis/SUMMARY.md` | `results/phd-main/`, `results/fellowship-main/`, `results/phd-ablation/` |
| `EVALUATION.md`, `docs/EXPERIMENTS.md` | `docs/evaluation.md`, `docs/experiments.md` |
| `RUBRIC.md` + `RECOMMENDATIONS.md` | `docs/methods/phd.md` |
| `TA_METHOD.md`, `FELLOWSHIP_METHOD.md`, `RA_METHOD.md` | `docs/methods/ta.md`, `fellowship.md`, `ra.md` |
| `VALIDATION.md` | Folded into each `docs/methods/*.md` |
| `LLM exoneration research plan.pdf` | Removed; the living plan is the "LLM exoneration" Google Doc |

A completed run's frozen plan also records the code it ran with. To re-verify
the fellowship plan exactly, check out commit `d9bc934`, the last commit before
the reorganisation.
