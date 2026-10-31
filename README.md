# PhD semi-synthetic resume pipeline

This is a PhD-only research prototype inspired by the **structured construction method** in
[Nghiem et al. (2025), Section 3 and Appendix D](https://arxiv.org/html/2509.16400v1).
Its inputs are the existing project plan and the admissions sources below. The
opportunity text and accusation/exoneration conditions are not redesigned.

**Current status: locally tested prototype with provisional research settings.**
On 2026-10-31, all 25 automated tests passed using temporary synthetic fixtures
and simulated API responses. No live API calls were made during verification.
This verifies software behavior, not empirical PhD calibration or rubric fidelity.
See [verification evidence and limitations](VALIDATION.md).

The earlier `runs/pilot/` remains an unapproved prototype, preserved locally for
audit and excluded from version control. It is not validated study data and
cannot be resumed by this configuration version.

The user requested provisional numerical values for review. They are in
`configs/phd.json`, with their basis recorded in `phd_resumes/provenance.py`.
They are not empirical PhD estimates.

## Construction sequence

1. Sample structured credentials with fixed seeds and explicit dependencies.
2. Compute a normalized performance index and cohort quintiles.
3. Subsample an oversampled pool using inverse cell-frequency weights without
   replacement.
4. Save facts, hashes, parameter provenance, count/date checks, marginals and
   correlation matrices for both the pool and retained sample.
5. Optionally ask a configurable OpenAI model to write CV entries around the
   fixed credentials; validate the entries and render a consistent CV. The
   current prompt still permits invented technical methods and activities, so
   this stage can affect perceived strength beyond the fixed numerical fields.

The paper supplies steps 1–4 as a methodological pattern. Its models **evaluate**
structured profiles; it does not use them to invent applicants. Step 5 is a
separate CV presentation layer for this project. Structured profiles can be used
without that layer. Neither essays nor recommendation letters are generated.

## Method correspondence

| Component | Implementation |
| --- | --- |
| Three independent seeded cohorts | Defaults 123, 456, 789 |
| Oversampled pool and retained sample | Defaults 15,000 and 10,000 per seed |
| Marginals and conditional relationships | Explicit PhD GPA bins, preparation/pathway mixture, research and output probabilities |
| Noisy rank alignment | GPA marginal preserved while its ordering depends on a noisy preparation variable |
| Composite normalization | Configurable percentile ranks or z-scores per feature |
| Performance quintiles | Linear empirical quantile cuts, matching `pandas.qcut` boundary semantics; duplicate edges raise an error |
| Weighted selection without replacement | Each record has weight 1 / its cell count; improves sparse-cell representation without guaranteeing equal cell sizes |
| Validation | Structural checks and before/after distribution reports; empirical PhD calibration remains unestablished |

The source study uses income and SES; this project audits integrity conditions.
The current PhD configuration uses a **provisional five-level preparation
variable** and **pathway × performance** sampling cells. These are explicit
adaptations, not variables supplied or validated by the paper. The sampler
follows the algorithmic pattern, not the authors' exact random-number stream or
their undergraduate population.

## How the PhD sources enter

| Source | Implemented evidence | Limit |
| --- | --- | --- |
| [UW holistic admissions rubric, 2020](https://grad.uw.edu/wp-content/uploads/Holistic-Admissions-2020.pdf) | Research duration, responsibility, methods, outputs, academics and fit | Broad illustrative rubric, not a current ML cutoff; old GRE rules are not imported |
| [Brandeis official admissions rubric](https://www.brandeis.edu/psychology/doctoral/how-to-apply.html) | Relevant/quantitative coursework, substantive research contribution, methods, outputs and fit | Psychology dimensions are adapted to CS; its publication expectations are not ML admission requirements |
| [Penn CIS statistics](https://www.cis.upenn.edu/admission-statistics/) | Admitted-GPA context | These means cannot identify a full applicant distribution, correlations or thresholds |
| [CMU chair repost, 2015](https://instant.1point3acres.com/thread/121768) | No numerical parameters | Older secondary material is excluded from calibration |
| Local research plan and user's proposed applicant examples | Existing CS PhD opportunity, work/internships, technical projects, intended three strength groups | No new treatment conditions, selection prompts or fellowship/RA pipeline |

The original Brandeis PDF URL was unavailable; its rubric is presented on the
official admissions page linked above. Source locations, limitations and field
names are also available in the inspection output and each future run's
`source_map.json`.

GPA and selected course grades are distinct fields. Course/grade patterns are
explicit in the configuration rather than all grades being inferred from the
overall GPA. These patterns are still illustrative, not reconstructed transcripts.
Research interests are visible, but no specific prospective faculty member is
supplied, so the pipeline does not invent a faculty-fit rating. Letter strength,
essay quality and personal character cannot be inferred from these CVs.

## Provisional settings to review

All PhD frequencies, correlations and score coefficients require review. In
particular:

- The pathway mixture is 35% bachelor's, 35% master's, 15% recent graduate and
  15% industry returner. All default timelines permit coursework in early 2026.
- Five preparation levels have equal probability. This is a simulation device.
- GPA bin probabilities are 10%, 20%, 25%, 25%, 20%; the noisy rank coefficient
  is 0.35. It is not a guaranteed observed Pearson correlation.
- Research duration, internships, publication opportunities, authorship, work
  domain and projects have conditional values in the configuration. The links
  support including these dimensions, not their exact numerical probabilities.
- Performance weights are 0.35 GPA, 0.35 research duration, 0.20 publication
  count, 0.10 internships and 0.10 projects. This reuses a numerical pattern on
  different fields; it is not evidence for their relative importance in a PhD
  decision. The sum is 1.10; the index is a ranking score, not a probability.
- Quintiles 1–2 are provisionally weak, 3 borderline and 4–5 strong. These are
  relative labels for review, not admission truth. They do not enforce the
  user's rough publication/work examples as exact rules. A reviewer should
  check that the resulting CVs express the intended groups.

Institution, employer and venue names are generic. Degree dates, work-duration
mixtures, three-month internships and weekly hours are template assumptions
documented in the source map. Publications are bounded by research opportunity;
internships are included in total research time. No strength or treatment label
is sent to the CV writer or included in evaluator-facing facts.

## Review without execution

Python 3.10+ and the standard library are sufficient. This command only reads
and checks settings and prints their provenance; it does not generate records,
write output files, require a key or contact a model:

```sh
python3 -m phd_resumes inspect --config configs/phd.json
```

Inspection establishes configuration consistency, not empirical calibration or
runtime correctness. Automated tests exercise inspection, small temporary sample
runs and simulated CV generation; they do not contact a live model.

## Commands for a later authorized run

The commands below describe how to create a study run; validation only created
temporary test fixtures. First review the provisional configuration. Choose a
new output folder; previous data is never silently replaced.

```sh
python3 -m phd_resumes sample --config configs/phd.json \
  --out runs/phd-reviewed --n-per-cohort 20 --oversample 10
```

That example would make 60 selected structured records from 90 pool records
without API calls. Omitting the size overrides uses the paper-sized defaults.
Sampling never automatically starts CV generation.

For optional wording, set `OPENAI_API_KEY` privately in the environment and
choose `OPENAI_MODEL`, or specify the model in the saved configuration/command.
No model ID is preselected. `.env.example` is documentation, not an automatically
loaded secrets file.

```sh
python3 -m phd_resumes generate --run runs/phd-reviewed --limit 3 \
  --model YOUR_MODEL_ID
```

Choose a model supporting Responses and Structured Outputs. Set
`generation.reasoning_effort` to null if that model does not support the field.
Model precedence is command line, environment, saved configuration. Optional
`--review-model` / `OPENAI_REVIEW_MODEL` selects a reviewer; otherwise it uses
the generator model in a separate context. Same-model checking is not
independent-model validation.

Each CV normally requires one wording call and one factual check. The mandatory
limit includes cached profiles. Existing responses are reused only for matching
requests; changed models, prompts or implementation require a new `--batch`.
Local fact-check failure skips the review call. API failures are retained, and
there is no automatic rewrite loop. Explicit transient HTTP errors have bounded
retries. Credentials are never written in request logs.

## Outputs and review

| Output | Purpose |
| --- | --- |
| `config.json`, `source_map.json`, `manifest.json` | Exact settings, sources, limitations and version/hash provenance |
| `pool.jsonl`, `profiles.jsonl` | Full pool and selected records, including internal provisional labels |
| `evaluator_fields.jsonl` | Fixed applicant facts with no analysis or treatment labels |
| `validation.json` | Structural checks, marginals, correlations and explicit calibration status |
| `human_review.csv` | Blank rubric-aligned academic/research/quantitative/fit review sheet, without intended labels |
| `structured_previews/` | Clearly marked previews without model wording |
| `generation/raw/` | Exact requests/responses and actual token usage |
| `generation/*.content.json`, `*.status.json` | Wording, factual checks and status |
| `generation/cvs/` | CVs passing automated checks, still requiring human review |

`ready_for_human_review` does not mean calibrated or approved. `needs_revision`
retains failures without exporting them as accepted CVs. Reuse the exact same
approved CV across all integrity conditions; stored hashes allow equality checks.
Treatment assembly and admissions evaluation are outside this component.

## Verification status

**25 tests passed on Python 3.14.6.** Tests cover source provenance, read-only
inspection, quantile ties, reproducibility, chronology, fixed facts, metadata
exclusion, malformed configuration, refusal, malformed responses, bounded HTTP
retries, CLI model selection, cache reuse and changed-run rejection. API tests
use mocked HTTP responses or a fake client. Run the same offline suite with:

```sh
python3 -m unittest discover -s tests -v
```

Live model access, output quality, full-size sampling performance and empirical
PhD/rubric calibration have not been established by these tests.
