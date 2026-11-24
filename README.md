# LLM exoneration study

Do large language models judge an applicant more harshly when the application
mentions an academic-integrity allegation that was later **cleared**, compared
with the identical application with a clean record?

We build fictional applicant packets and ask LLMs to evaluate them. Each packet
is sent in 11 versions that differ only in a short **institutional record**
paragraph at the end:
- a clean record;
- a neutral administrative control;
- nine allegation outcomes, from "pending" and "found responsible" to "cleared", "dismissed" and "exonerated on appeal".

Everything else is identical, so a score difference between versions of the same
applicant is caused by that paragraph.

The study plan is the "LLM exoneration" Google Doc:
[docs.google.com/document/d/1dgZkwce8f8iXa1Nt0kmj7WIPqrdzxcMJCaYEYm7VQ2s](https://docs.google.com/document/d/1dgZkwce8f8iXa1Nt0kmj7WIPqrdzxcMJCaYEYm7VQ2s/edit).

## Results so far

| Opportunity | Evaluation | Write-up |
|---|---|---|
| Computer Science PhD | 5 models × 13,200 requests | [results/phd-main](results/phd-main/analysis/SUMMARY.md) |
| Graduate research fellowship | 5 models × 13,200 requests | [results/fellowship-main](results/fellowship-main/analysis/SUMMARY.md) |
| Teaching assistant, research assistant | Applicants built, not yet evaluated | — |

The models were GPT-5.4 mini, Gemini 3.8 Flash, Gemma 4 31B IT, Llama 4
Maverick and Qwen3-32B. Scores are on a 0–100 scale. In both opportunities:

- **Cleared** allegations were barely penalised, and explicit exonerations often scored slightly *above* a clean record (+2 to +7 points). The one penalty that survived the strictest correction was GPT-5.4 mini's −2.3 on the fellowship award decision.
- **Pending** allegations cost 3–19 points, and **found responsible** cost 13–34 points.
- **Procedural reversals** (overturned without deciding the facts) were penalised by every model.
- **Withdrawn** and **dismissed** allegations were penalised by some models: Llama and Qwen on the PhD, and four of five models on the fellowship.
- **Robustness:** removing the instruction "Do not assume or infer details that are not stated." made no meaningful difference ([ablation](results/phd-ablation/SUMMARY.md)).

[docs/experiments.md](docs/experiments.md) lists every experiment with its cost.

## Quick start

Python 3.10 or newer.

```sh
git clone https://github.com/ajay-cogsci/llm-exoneration-project.git
cd llm-exoneration-project
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[analysis]"      # the code itself needs only the standard library

python3 -m unittest discover -s tests     # offline tests; no API keys
python3 scripts/verify_datasets.py        # checks the PhD inputs

# See exactly what a model is sent
python3 -m phd_eval preview --condition cleared --task advance --format rationale

# Rebuild the analyses from the committed results
python3 analysis/analyze_main.py
python3 analysis/fellowship.py
```

## Repository layout

```
data/            applicant banks used as inputs (read-only)
  phd/           cvs/ and applications/ (CV + 3 recommendation letters)
  fellowship/  ta/  ra/
src/
  generate/      code that built the applicants (one package per opportunity)
  evaluate/      phd_eval, fellowship_eval: build prompts, run models, export
configs/         prompts, condition wordings and generation settings
analysis/        statistics and figures for each finished experiment
results/         committed results of finished experiments, with SUMMARY.md
scripts/         dataset verification and audits
docs/            evaluation.md, experiments.md, methods/ (how each bank was built)
tests/           offline tests (simulated model clients)
old/             earlier data versions and one-off tooling, kept for the record
runs/            local working folder for runs and raw replies (not in git)
```

## Where to read next

- **[docs/evaluation.md](docs/evaluation.md):** how prompts are built and how to run, export and analyse an evaluation, with practical notes on paid runs.
- **[docs/methods/](docs/methods/):** how each applicant bank was built and checked ([PhD](docs/methods/phd.md), [fellowship](docs/methods/fellowship.md), [TA](docs/methods/ta.md), [RA](docs/methods/ra.md)).
- **[old/README.md](old/README.md):** what the archived material is, and how old paths map to new ones.

## Ground rules

- **API keys:** never commit or print them. Code reads keys from environment variables.
- **Spending:** paid model runs need an agreed model list and dollar cap.
- **Published inputs:** don't edit `data/`, the prompts in `configs/`, or a frozen run plan. Make a new version or a new run folder instead.
- **Finished results:** never overwrite them. Each new experiment gets its own folder.
- **Branches:** `main` is the shared branch.

## Limits

- **Fictional applicants:** every applicant is fictional. Tier labels (weak, borderline, strong) come from provisional rule-based rubrics, not human ratings.
- **Sampling settings:** models ran at their providers' default sampling settings, with one reply per request. Estimates average over 100 applicants, 2 wordings and 2 formats. An exact re-run of 2,400 PhD requests per model reproduced the condition-vs-clean gaps within about 0.2–0.9 points at the median. No formal test–retest study was run.
- **Model panel:** all five models are cheaper or open-weight models. No frontier model has run the full design.
- **Scope:** the results describe how these models respond to these packets. They do not describe how real committees behave.
