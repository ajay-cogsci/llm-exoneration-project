# Graduate introductory CS TA applicants, version 2

100 fictional graduate applicants, with study allocation
{'weak': 30, 'borderline': 40, 'strong': 30} and ten designated mixed cases in the full sample.
All selected applicants are available for the advertised duties. Applicants with
no teaching history can be strong. Communication is sampled separately from
teaching history. Courses, grades, projects, skills and education histories vary.

## Files

- `applications/`: the complete application profiles, including supporting
  communication and teaching-performance evidence. These are not CVs alone.
- `index.html`: local research viewer; its tier and mixed-case annotations are
  excluded from the application files and evaluator messages.
- `profiles.jsonl`: source facts plus private study metadata and provisional tiers.
- `evaluator_fields.jsonl`: source facts only.
- `evaluator_inputs.jsonl`: the plan's exact shared system message (committee
  placeholder resolved), TA opportunity and overall-quality prompt. No integrity
  treatment is attached: `condition: null` does not mean a clean record.
  No evaluations have been run. Reuse the same application across treatments.
- `prompts/`: the shared system template, resolved system message and TA opportunity.
- `generation/`: accepted wording and separate-context factual-check results.
- `config.json`, `generation_contract.json`, `source_map.json`: reproducible choices.
- `sampling_report.json`, `validation.json`, `dataset.json`,
  `application_manifest.json`, `checksums.json`: diagnostics and file hashes.

All people, institutions, activities, instructor observations and supervisor
feedback are fictional. Supporting evidence uses fixed templates grounded in the
same source record as the CV sections. No recommendation letters or essays have
been added. The research plan supplies criteria, not numerical thresholds or
empirical applicant distributions. See [the version 2 method](../../TA_V2_METHOD.md)
for the mapping, rubric rules, mixed-case definition and limitations.

## Generation and verification

GPT-6 Astra at medium reasoning effort writes only titles and two short factual
bullets per project or teaching entry. It receives no tier or mixed-case label.
A separate context checks each output against the fixed record. Grades, dates,
roles, feedback, teaching interest and availability render deterministically.
Repairs, if needed, change wording only. Raw API records stay in the local run.

Saved API responses: 200.
Reported total tokens: 311247.
Accepted profiles by number of wording repairs: {"0": 100}.
Usage totals are not a billing estimate.

```sh
python3 -m ta_applicants_v2 verify --out datasets/ta-applicants-v2
```

This command makes no API calls. It reproduces the pool and selection, recomputes
labels, checks hashes and rerenders every application and assessment message.
Fresh model prose is not guaranteed to repeat. Automated checks and same-model
factual review do not establish real hiring accuracy, empirical realism or
independent human agreement. The earlier TA and PhD datasets are preserved.

## Revision audit

`audit.json` compares this sample with version 1 and checks source evidence against
the exported text without using the generator's sampler. `revision_history.json`
records the superseded three-applicant pilot, its timeline correction and total
reported API usage, including responses not used in the final dataset.
