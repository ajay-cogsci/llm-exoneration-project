# PhD applicant CVs — version 2

100 semi-synthetic CS PhD applicant CVs, generated on 2026-11-11. The allocation
is 30 weak, 40 borderline and 30 strong under the provisional CV rubric, including
ten designated mixed profiles. These are study design categories, not admission
probabilities or estimates of applicant population frequencies.

| Location | Contents |
| --- | --- |
| [resumes/](resumes/) | 100 final CV text files |
| [index.html](index.html) | Local HTML browser for all CVs |
| [profiles.jsonl](profiles.jsonl) | Structured records and internal rubric labels |
| [evaluator_fields.jsonl](evaluator_fields.jsonl) | Applicant facts without analysis labels |
| [generation/](generation/) | Accepted CV descriptions and factual-check statuses |
| [resume_manifest.json](resume_manifest.json) | CV/content paths and source hashes |
| [config.json](config.json), [rubric.json](rubric.json), [sampling_policy.json](sampling_policy.json) | Exact construction and allocation settings |
| [dataset.json](dataset.json) | Generation and validation metadata |
| [checksums.json](checksums.json) | SHA-256 of every other file in this directory |

The structured pool contains 6,000 profiles across seeds 123, 456 and 789. Its
selected 100 records can be reproduced from the saved settings. Accepted prose
was generated with GPT-6 Astra at medium reasoning effort, followed by
separate-context factual checks. Ninety-one CVs passed initially; nine required
one wording repair. The exported CV files are byte-identical to the retained
version 2 run. Intermediate API responses and working notes are not included.

The construction method follows the conditional structured-data approach in
[Nghiem et al.](https://arxiv.org/abs/2509.16400), adapted for PhD CVs. Numerical
PhD parameters and tier rules are provisional. See [RUBRIC.md](../../RUBRIC.md)
for criteria, sources and limits. Papers, recommendation summaries and actual
admission outcomes are not interchangeable validation evidence.

The completed CV-plus-recommendation packets are in
[the version 3 dataset](../phd-applications-v3-recommendations-v1/). Existing CV
labels remain CV-only. Reuse each applicant's same credentials across integrity
conditions. Do not send internal labels or latent fields to an evaluator.

From the repository root, run `python3 scripts/verify_datasets.py` to verify
checksums, reproduce the pool and selection, and validate CV and letter contents.
GitHub displays HTML source; download or clone the repository to open the viewer.
