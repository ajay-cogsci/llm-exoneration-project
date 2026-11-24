# Validation

This page lists what has been checked for each applicant bank and what those
checks do and do not establish. Run every check offline, without API keys:

```sh
python3 -m unittest discover -s tests
python3 scripts/verify_datasets.py                                    # PhD
python3 -m ta_applicants verify --out datasets/ta-applicants-v2 && python3 scripts/audit_ta.py
python3 -m fellowship_applicants verify --out datasets/fellowship-applicants-v2
python3 scripts/audit_fellowship.py --out datasets/fellowship-applicants-v2
python3 -m ra_applicants verify --out datasets/ra-applicants-v2
python3 scripts/audit_ra.py --out datasets/ra-applicants-v2
```

## What every bank has

- **Reproducibility:** the structured pool (6,000 records across seeds 123, 456 and 789) and the selected 100 applicants rebuild exactly from the saved config.
- **Integrity:** every published file has a SHA-256 checksum. Verification checks the full file list, the tier labels, the rendered text and the evaluator messages.
- **Model-written wording:** GPT-6 Astra (medium reasoning) wrote short descriptions only. Dates, grades, tools, observations and credentials are rendered from the structured facts. A separate model call checked each application against its facts.
- **No labels in prompts:** tier labels, mixed-case designations and identifiers never appear in evaluator prompts.
- **Simulated tests:** the tests use simulated API responses.

## PhD

- **Sample:** 100 CVs, 29 weak, 41 borderline and 30 strong, with ten designated mixed profiles.
  - Tiers follow fixed academic/research rules ([RUBRIC.md](RUBRIC.md)).
  - 91 CVs passed the factual check first time; nine passed after one wording repair.
- **Recommendations:** three per applicant, from fixed templates, with no model calls ([RECOMMENDATIONS.md](RECOMMENDATIONS.md)).
  - Strength: 68 limited, 147 moderate and 85 strong.
  - 148 compare the applicant with other students; 97 give a specific example.
- **Consistency corrections** (the current inputs):
  - 19 GPAs that contradicted the listed course grades were redrawn, and one applicant changed tier.
  - 11 letters whose endorsement contradicted the cited grade were changed to moderate.
  - `scripts/verify_datasets.py` rebuilds both corrections from the earlier versions and requires a byte-for-byte match.
- **Evaluation harness:** tests confirm that:
  - conditions differ only in the record block;
  - no identifier or label reaches a prompt;
  - replies parse correctly;
  - runs resume correctly.
- **Open:** human review of the CVs and letters has not been done.

## Teaching assistant

- **Sample:** 100 graduate applicants, 55 MS and 45 PhD; 30 weak, 40 borderline and 30 strong, including ten designated mixed cases.
- **Design checks:**
  - communication and teaching history are drawn independently;
  - strong first-time TAs are possible;
  - every applicant is available for the required duties;
  - university appointments fall within enrolled periods.
- **Wording:** all 100 passed the factual check without a repair. A keyword scan of the 578 generated bullets found no screened numeric or superlative claims.
- **Audit:** `scripts/audit_ta.py` checks the exported records independently of the generator.
- **Limits:**
  - mean length is 340.5 words for weak applicants, 347.4 for borderline and 372.0 for strong;
  - availability effects cannot be tested, because everyone is available.

## Graduate research fellowship

- **Sample:** 100 applicants, 64 MS and 36 PhD; 30 weak, 40 borderline and 30 strong, including ten designated mixed cases.
- **Uniqueness:** there are 100 distinct proposal bundles and 100 distinct broader-impact bundles.
- **Length:** mean length is 710.2 words for weak applicants, 711.0 for borderline and 726.6 for strong (2.3% spread).
- **Wording:** all 100 passed the factual check without a repair.
- **Audit:** the audit checks chronology, workload, GPA compatibility, source links, criterion coverage, metadata leakage and duplication.
- **Rubric sensitivity:** removing one type of evidence at a time changes tiers as expected. For example, setting both graduate grades to C changes 58 tiers. This tests the rules, not their external validity.

## Research assistant

- **Sample:** 100 applicants, 53 MS and 47 PhD; 30 weak, 40 borderline and 30 strong, including ten designated mixed cases.
- **Audit:** the audit checks:
  - chronology and workload;
  - GPA consistency;
  - source attribution;
  - distinct portfolios;
  - that SQL and pandas routes are interchangeable;
  - absence of researcher metadata.

## What validation does not establish

- **Plausibility, not realism:** passing checks shows the banks are internally consistent and reproducible. It does not show they resemble real applicant pools or match real committee judgments.
- **Not independent review:** the same model generated the wording and reviewed it.
- **Provisional thresholds:** the rubric thresholds and sampling probabilities are study choices.
- **Human review:** the only human check so far is one researcher's informal review of a few examples.
