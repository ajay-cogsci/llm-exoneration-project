# 100 PhD applicant resumes

The **100 final resumes** are in [resumes/](resumes/). Download this directory
and open [index.html](index.html) locally to browse and search them. GitHub
displays HTML source rather than running this index.

GPT-6 Astra generated the wording and performed separate-context factual
reviews. Of the 100 applicants, 91 passed initially and nine passed after one
wording revision each. Fixed applicant facts were preserved. All final CVs
passed the automated checks; human review and empirical calibration remain
pending.

- [Validation report](VALIDATION_REPORT.txt): findings, sampling correction,
  limitations, and API usage.
- [Detailed validation](validation_summary.json) and
  [artifact checks](artifact_verification.json): machine-readable results.
- [Resume manifest](resume_manifest.json): final files, source records, and hashes.
- [Human review sheet](human_review.csv): blank rubric-aligned review fields.
- [Run plan](run_plan.json) and [sampling fix verification](sampling_fix_verification.json):
  configuration and regression evidence.

`cohorts/` retains source facts, first-pass drafts, requests, responses, and
checks. `repairs/` retains the nine wording corrections. `audit/` preserves the
interrupted run with the original sampling defect, the implementation snapshot,
and the correction. These intermediate drafts are not additional final resumes.

The validation report records the state at generation time, before Git upload.
This directory was subsequently added to the repository at the user's request;
the original run records and scripts remain preserved.
