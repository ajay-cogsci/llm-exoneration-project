# Graduate introductory CS TA applicants, version 1

100 fictional graduate-student applicants: 30 weak, 40 borderline and 30 strong
under a provisional study rubric, including ten designated mixed profiles.
The opportunity and shared assessment system message reproduce the local
research plan, with paragraph wrapping normalized and the committee placeholder
resolved. Source-plan SHA-256 is in `source_map.json`.

## Files and use

- `applications/`: 100 application texts containing education, coursework,
  programming project, teaching/tutoring history and supervisor feedback,
  communication evidence, teaching interest, and duty availability.
- `index.html`: local research viewer. Its tier/pattern annotations are not
  included in the application text files.
- `evaluator_fields.jsonl`: fixed factual records only.
- `evaluator_inputs.jsonl`: untreated overall-quality assessment inputs using
  the plan's system message and rating prompt. `condition: null` means no
  integrity treatment has been attached; it does not mean a clean record.
  No evaluations have been run. Reuse identical application text when attaching
  the plan's integrity conditions or using its other assessment prompts.
- `prompts/`: exact shared system template, resolved system message and TA
  opportunity text. Applicant generation uses separate instructions.
- `profiles.jsonl`: research metadata, source facts and provisional labels.
  Do not pass this file or the viewer's labels to an evaluator.
- `generation/`: accepted wording and factual-check status, without raw API logs.
- `config.json`, `generation_contract.json`, `source_map.json`: sampling,
  rubric, wording instructions and provenance.
- `sampling_report.json`, `validation.json`, `application_manifest.json`,
  `checksums.json`: coverage, automated checks, identities and file hashes.

The full method and assumptions are in `../../TA_METHOD.md`. All institutions,
projects, communication observations and supervisor feedback are synthetic.
These are short application profiles, including evidence a CV alone may omit.
No recommendation letters are generated for TA applications: the plan does not
include them among the TA criteria.

## Generation and verification

Fixed facts were sampled and labelled before wording. GPT-6 Astra, with medium
reasoning effort, paraphrased only the recorded project and teaching activities.
A separate model context checked each accepted output against those facts.
Dates, grades, role details, feedback, interest and availability were rendered
directly from the source records. Repairs changed wording only.

Saved API responses: 200.
Reported tokens in saved responses: 248664.
Accepted applicants by number of wording repairs: {"0": 100}.
These token counts are usage evidence, not a billing estimate.

From the repository root, without an API key:

```sh
python3 -m ta_applicants verify --out datasets/ta-applicants-v1
```

Verification reproduces the 6,000-record pool and selection, recomputes tiers,
checks all file hashes, renders each application again, and verifies exact
assessment messages. Fixed records are reproducible; fresh model wording is not
guaranteed to repeat. All numeric thresholds and distributions are study choices.
Automated consistency checks do not establish empirical realism, hiring accuracy,
independent human agreement or absence of evaluator bias.
