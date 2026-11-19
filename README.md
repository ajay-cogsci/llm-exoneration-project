# Semi-synthetic applicant pipelines

Structured PhD, graduate CS teaching-assistant, graduate research fellowship and research-assistant
applicant generation, provisional
criterion-based labels, and constrained application wording. PhD applications also
include fixed-template recommendation summaries. The project studies evaluations
of otherwise identical applications across integrity conditions.

## Experiment status

The PhD pilot, five-model full-design run, and three-model no-infer ablation
are complete. The original 11-condition methodology remains the study design.
The introductory-CS TA applicant bank has been generated and verified following
approval: 100 graduate applicants in [version 2](datasets/ta-applicants-v2/).
TA evaluation runs, model-panel choices and evaluation spending remain pending.

The graduate research fellowship applicant bank is approved for publication:
100 early-stage CS graduate applicants in [version 2](datasets/fellowship-applicants-v2/).
Fellowship evaluation runs remain unapproved. See the
[fellowship method](FELLOWSHIP_METHOD.md) for scope, assumptions and verification.

The Data and Text Analysis Research Assistant applicant bank is approved for
publication: 100 current CS graduate applicants in [version 2](datasets/ra-applicants-v2/),
with 30 weak, 40 borderline, 30 strong and ten designated mixed cases.
RA evaluation runs remain unapproved. See the [RA method](RA_METHOD.md) for the
plan mapping, provisional rubric and verification.

Use the [experiment index](docs/EXPERIMENTS.md) to find each dataset and analysis,
and [the approved TA method](TA_METHOD.md) for the applicant-generation scope.
Earlier results and published datasets are retained.

**Start from `main` for approved work.** It is the only current remote branch.
The former `codex/ta-prep` branch has been retired; its unapproved draft examples
and handoff prompt were removed. Applicant-generation approval does not authorize
an evaluation run.
The [branch history](docs/EXPERIMENTS.md#repository-branches-consolidated-16-november-2026)
explains the retired names. The five-model full run is complete for those five
models; the originally proposed seven-model panel remains incomplete.

## Which code should I use?

The four `phd_*` folders are different steps, not competing versions of the study.

| Folder | Purpose | Why it remains |
| --- | --- | --- |
| `phd_resumes/` | Sample structured PhD facts, assign provisional tiers and write CVs | Reproduces the PhD inputs. TA, fellowship and RA generators also import its shared API, file and validation helpers. |
| `phd_recommendations/` | Add three source-linked recommendation summaries to each PhD CV | Reproduces the recommendation evidence in the evaluated PhD packets; no model calls. |
| `phd_revisions/` | Apply the published GPA and recommendation corrections | Rebuilds corrected CV v3 and application v4 from their published predecessors; required by `scripts/verify_datasets.py`. This is not a second applicant generator. |
| `phd_eval/` | Assemble PhD treatments, send evaluation requests and collect replies | Reproduces the completed PhD pilot, full run and sentence ablation. Its packet loader is PhD-specific. |

The current applicant generators for the other opportunities are `ta_applicants/`,
`fellowship_applicants/` and `ra_applicants/`. Their JSON configs control applicant
generation. They are **not evaluation configs**. Their `evaluator_inputs.jsonl`
files contain an untreated quality-question preview, not the full experiment.

For PhD work, use application v4 and `configs/phd_eval_v1.json`. Older published
CVs, packets and policies remain because the correction checks reproduce their
successors from them. `configs/phd_eval_v1_no_infer.json` belongs only to the
completed sentence ablation. The saved config and plan in each run directory
record what that particular experiment used. Do not regenerate existing banks
or delete these dependencies as housekeeping.

The [fellowship evaluation handoff](docs/FELLOWSHIP_EVALUATION_HANDOFF.md) records
the readiness review and instructions for offline adapter preparation. It does
not authorize evaluation calls. No TA, fellowship or RA evaluation adapter is
implemented yet.

## Datasets

| Dataset | Contents |
| --- | --- |
| [Applications, version 4](datasets/phd-applications-v4-recommendations-v2/) | **Use this for PhD evaluation.** The 100 packets with contradictory GPAs and letters corrected |
| [CVs, version 3](datasets/phd-cvs-v3-gpa-consistency-v1/) | The 100 CVs with 19 GPA values corrected; all prose unchanged |
| [CVs, version 2](datasets/phd-cvs-v2-rubric-v1/) | 100 revised CVs: 30 weak, 40 borderline and 30 strong, including ten mixed profiles |
| [Applications, version 3](datasets/phd-applications-v3-recommendations-v1/) | The same 100 CVs with 300 recommendation summaries and 100 complete packets |
| [Original sample](sample-100-resume-generated/) | Historical sample retained unchanged |
| [Graduate TA applications, version 2](datasets/ta-applicants-v2/) | Revised 100-applicant TA sample: 30 weak, 40 borderline, 30 strong and ten designated mixed cases; capable first-time TAs and varied source records |
| [Graduate research fellowship applications, version 2](datasets/fellowship-applicants-v2/) | Approved 100-applicant sample: 64 MS and 36 PhD students, 30 weak, 40 borderline, 30 strong and ten designated mixed cases; complete research and broader-impact plans |
| [Research assistant applications, version 2](datasets/ra-applicants-v2/) | Approved 100-applicant sample: 53 MS and 47 PhD students, 30 weak, 40 borderline, 30 strong and ten designated mixed cases; source-linked technical and work evidence, equivalent SQL/dataframe routes and varied selected coursework |

Only final datasets explicitly approved for publication are committed. TA version
2 is the approved TA dataset. Drafts, pilots and intermediate outputs belong in
ignored local run directories. Other TA dataset directories are ignored by
default; a future approved dataset requires an explicit publication update.
The only TA generator is `ta_applicants/`, configured by `configs/ta.json` and
documented in [TA_METHOD.md](TA_METHOD.md). Its approved dataset keeps the v2
release identifier; it is not a second pipeline.

Fellowship version 2 is the only approved fellowship release. Its canonical
pipeline is `fellowship_applicants/`, with `configs/fellowship.json` and
[FELLOWSHIP_METHOD.md](FELLOWSHIP_METHOD.md). Earlier fellowship data, pilots and
raw generation logs remain excluded from version control.

RA version 2 is the only approved RA release. Its canonical pipeline is
`ra_applicants/`, with `configs/ra.json` and [RA_METHOD.md](RA_METHOD.md).
Earlier RA data, pilots and raw generation logs remain excluded from version control.

Dataset directories include documentation, a local HTML viewer and file
checksums. GitHub displays HTML source; clone or download the repository to
open a viewer. The version 4 `applications/` directory contains the complete
evaluation inputs. Preserve each packet across integrity conditions.

## Corrections and evaluation

Version 2 CVs and version 3 packets are kept unchanged for the record. Two
problems were corrected in new versions, without any model calls:

- **GPA against coursework.** Nineteen CVs printed a GPA that contradicted the
  grades beside it. Only those GPA values were redrawn; see the
  [CV version 3 README](datasets/phd-cvs-v3-gpa-consistency-v1/README.md). One
  applicant changed tier, so the sample is now 29 weak, 41 borderline, 30 strong.
- **Letters against grades.** Eleven course letters gave an endorsement that
  contradicted the grade they cited. Recommendation policy v2 removes those
  cells; see the [packet version 4 README](datasets/phd-applications-v4-recommendations-v2/README.md).

Rebuild both from the published datasets with `python3 -m phd_revisions`
(it refuses to overwrite existing folders).

[EVALUATION.md](EVALUATION.md) explains how to run the PhD experiment with
`phd_eval`: prompt assembly, the integrity-record slot, the design, the runner
and the export.

## PhD construction

1. Sample academic and research preparation using separate conditional draws.
2. Assign CV tiers from explicit academic/research rubric rules.
3. Select the configured tier and mixed-profile allocation from three seeded pools.
4. Generate constrained CV descriptions, check factual consistency and render
   fixed credentials deterministically.
5. Attach three recommendation summaries using fixed templates and seeded settings.

The revised sample was selected from 6,000 records across seeds 123, 456 and 789.
CV descriptions were generated with GPT-6 Astra at medium reasoning effort.
Ninety-one passed initially; nine passed after one wording repair. All accepted
CVs passed structural checks and a separate-context model factual review.

Recommendations use no additional model calls. Each has a writer type, strength
level, comparison-to-other-students flag and specific-work-example flag. Dates
and examples are linked to the source CV. Recommendation strength is distinct
from the applicant's CV tier.

## TA construction

The TA pipeline follows the opportunity and shared assessment system message in
`LLM exoneration research plan.pdf`. It models relevant coursework, programming,
teaching/tutoring experience and performance, written/oral communication,
teaching interest, and availability. All applicants are current graduate students.

Applicant wording uses separate generation instructions. Evaluator inputs preserve
the plan's system message and overall-quality assessment prompt; no integrity
conditions are attached and no assessments are run. Tier labels remain separate
research metadata. The numerical sampler and TA rubric are provisional study
choices, not thresholds supplied by the plan. The current implementation permits
strong first-time TAs, samples communication separately from teaching history,
and holds required-duty availability fixed across the selected sample. See
[TA_METHOD.md](TA_METHOD.md) for the current mapping, assumptions, limits and
commands. The audit runs directly on the approved dataset and does not require
an earlier applicant draft.

```sh
python3 -m ta_applicants verify --out datasets/ta-applicants-v2
python3 scripts/audit_ta.py
```

## Documentation

- [RUBRIC.md](RUBRIC.md): tier definitions, mixed profiles and sampler design.
- [RECOMMENDATIONS.md](RECOMMENDATIONS.md): template fields and assignment settings.
- [TA_METHOD.md](TA_METHOD.md): revised TA sampling, rubric and verification.
- [FELLOWSHIP_METHOD.md](FELLOWSHIP_METHOD.md): fellowship evidence rubric, sampling, model wording and verification.
- [RA_METHOD.md](RA_METHOD.md): RA evidence rubric, sampling, source-linked work and coursework, model wording and verification.
- [VALIDATION.md](VALIDATION.md): validation results and limitations.
- [EVALUATION.md](EVALUATION.md): running the PhD evaluation and its open choices.
- [configs/](configs/): reusable parameter files; numerical PhD settings are provisional.

The structured construction follows [Nghiem et al., Section 3 and Appendix D](https://arxiv.org/html/2509.16400v1).
The paper studies undergraduate admissions and does not provide PhD distributions
or recommendation-letter generation rules. The PhD criteria draw on the
[Brandeis rubric](https://www.brandeis.edu/psychology/doctoral/how-to-apply.html),
[UW holistic admissions rubric](https://grad.uw.edu/wp-content/uploads/Holistic-Admissions-2020.pdf),
and [Penn CIS statistics](https://www.cis.upenn.edu/admission-statistics/).
These sources motivate dimensions; they do not empirically calibrate this sampler.

## Verification

Python 3.10+ and the standard library are sufficient. These checks make no model calls:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_datasets.py
python3 -m fellowship_applicants verify --out datasets/fellowship-applicants-v2
python3 scripts/audit_fellowship.py --out datasets/fellowship-applicants-v2
python3 -m ra_applicants verify --out datasets/ra-applicants-v2
python3 scripts/audit_ra.py --out datasets/ra-applicants-v2
```

Dataset verification checks every exported file, reproduces the structured pool
and selected sample, recomputes CV tiers, verifies CV rendering and reproduces
all three recommendations for each applicant. No keys are needed.
It also rebuilds the corrected datasets from the published ones and requires
every file to match.

## Generating another sample

Inspect the revised settings:

```sh
python3 -m phd_resumes inspect-rubric
```

Set an explicit allocation in a copy of `configs/phd_sampling_v3.json`, then
create a new structured run with `sample-rubric`. CV wording is a separate
`generate` command requiring a configured OpenAI model and `OPENAI_API_KEY`.
The key is read from the environment and is not stored in the repository.
The reusable allocation defaults to null; published allocation settings are
in the version 2 dataset. Historical `sample` and `inspect` commands retain the
original composite-quintile behavior.

For a separately approved new recommendation package, use the corrected CVs
and current recommendation policy explicitly. The CLI's historical default is
policy v1, which is retained for reproduction:

```sh
python3 -m phd_recommendations generate \
  --source datasets/phd-cvs-v3-gpa-consistency-v1 \
  --out runs/phd-recommendations-new \
  --policy configs/phd_recommendations_v2.json
```

Generation refuses to overwrite an existing output. The published datasets are
portable exports; full intermediate working runs and conversational audit notes
are excluded from this update. Existing historical files remain unchanged.

## Interpretation

All applicants are fictional. Numeric rubric thresholds, dependencies and letter
probabilities are study choices, not validated admission probabilities. Fixed
templates control wording variation but do not establish realistic recommendation
frequencies or eliminate evaluator bias. CV tiers remain CV-only after letters
are added. Source consistency and model checks do not substitute for independent
validation against real admissions judgments.
