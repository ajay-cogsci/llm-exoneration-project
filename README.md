# PhD semi-synthetic applicant pipeline

Structured PhD applicant generation, provisional admissions-rubric labels,
constrained CV wording, and fixed-template recommendation summaries. The project
studies evaluations of otherwise identical applications across integrity conditions.

## Published datasets

| Dataset | Contents |
| --- | --- |
| [CVs, version 2](datasets/phd-cvs-v2-rubric-v1/) | 100 revised CVs: 30 weak, 40 borderline and 30 strong, including ten mixed profiles |
| [Applications, version 3](datasets/phd-applications-v3-recommendations-v1/) | The same 100 CVs with 300 recommendation summaries and 100 complete packets |
| [Original sample](sample-100-resume-generated/) | Historical sample retained unchanged |

Each dataset has its own README, data dictionary, local HTML viewer and file
checksums. GitHub displays HTML source; clone or download the repository to
open a viewer. The version 3 `applications/` directory contains the complete
evaluation inputs. Preserve each packet across integrity conditions.

## Construction

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

## Documentation

- [RUBRIC.md](RUBRIC.md): tier definitions, mixed profiles and sampler design.
- [RECOMMENDATIONS.md](RECOMMENDATIONS.md): template fields and assignment settings.
- [VALIDATION.md](VALIDATION.md): validation results and limitations.
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
```

Dataset verification checks every exported file, reproduces the structured pool
and selected sample, recomputes CV tiers, verifies CV rendering and reproduces
all three recommendations for each applicant. No keys are needed.

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

Generate another recommendation package from the published CVs:

```sh
python3 -m phd_recommendations generate \
  --source datasets/phd-cvs-v2-rubric-v1 \
  --out runs/phd-recommendations-new \
  --policy configs/phd_recommendations_v1.json
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
