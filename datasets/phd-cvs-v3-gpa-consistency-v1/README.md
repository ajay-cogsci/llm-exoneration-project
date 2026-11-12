# PhD applicant CVs — version 3 (GPA consistency)

The same 100 applicants as [version 2](../phd-cvs-v2-rubric-v1/), with one correction:
19 CVs printed a cumulative GPA that contradicted the course grades on
the same page (for example a 3.94 GPA beside B, B, B+, B). Those GPA values were
redrawn. Nothing else changed: applicants, coursework, dates, research,
publications, work, projects and all accepted CV prose are identical, and the
other 81 CV files are byte-identical to version 2. No model calls were made.

## Rule and correction

A CV is consistent when its GPA lies within 0.6 grade points of the unweighted
grade-point mean of its four listed courses. A violating CV receives a new GPA
drawn from the sampler's own GPA distribution for that applicant's academic
level, restricted to consistent values. The draw is also restricted to values
that keep the rubric's academic rating, when such a value exists. The seed and
settings are in [gpa_consistency_policy.json](gpa_consistency_policy.json); the
tolerance is a plausibility bound chosen for this study, not an empirical
relationship between course grades and GPA.

| Applicant | Course mean | GPA v2 | GPA v3 | Tier v2 | Tier v3 |
| --- | ---: | ---: | ---: | --- | --- |
| PHDv3-123-01124 | 2.675 | 3.76 | 3.26 | weak | weak |
| PHDv3-123-01383 | 3.075 | 3.89 | 3.31 | borderline | borderline |
| PHDv3-123-01483 | 2.675 | 3.42 | 3.02 | borderline | borderline |
| PHDv3-123-01745 | 2.675 | 3.57 | 3.08 | weak | weak |
| PHDv3-123-01830 | 3.075 | 3.82 | 3.39 | borderline | borderline |
| PHDv3-123-01851 | 3.075 | 3.82 | 3.65 | weak | weak |
| PHDv3-456-00633 | 2.675 | 3.54 | 3.19 | weak | weak |
| PHDv3-456-00788 | 2.675 | 3.47 | 2.85 | weak | weak |
| PHDv3-456-00797 | 3.075 | 3.74 | 3.59 | borderline | borderline |
| PHDv3-456-00958 | 3.850 | 2.95 | 3.83 | weak | borderline |
| PHDv3-456-01157 | 3.075 | 3.82 | 3.37 | borderline | borderline |
| PHDv3-456-01325 | 2.675 | 3.33 | 3.00 | weak | weak |
| PHDv3-789-00271 | 3.075 | 3.92 | 3.50 | borderline | borderline |
| PHDv3-789-00504 | 3.075 | 3.94 | 3.41 | borderline | borderline |
| PHDv3-789-00730 | 2.675 | 3.51 | 3.17 | weak | weak |
| PHDv3-789-01053 | 2.675 | 3.63 | 2.91 | weak | weak |
| PHDv3-789-01189 | 2.675 | 3.48 | 3.06 | weak | weak |
| PHDv3-789-01418 | 3.075 | 3.83 | 3.09 | weak | weak |
| PHDv3-789-01730 | 2.675 | 3.75 | 2.82 | borderline | borderline |

## Consequences to know about

- The allocation is now 29 weak, 41 borderline and 30 strong. 1 applicant
  changed tier (PHDv3-456-00958), because no consistent GPA could keep its
  previous academic rating. The allocation no longer equals the 30/40/30 quota
  in `sampling_policy.json`, which describes how the version 2 sample was drawn.
- 2 applicants (PHDv3-123-01483, PHDv3-789-01730) keep their tier but now match the
  `lower_gpa_strong_research` descriptive pattern first.
- `legacy_diagnostic` in a changed record still describes the original draw.
- The model factual review recorded in `generation/*.status.json` was run on
  the version 2 record. It was not rerun; the changed line is rendered by code
  and the reviewed prose never mentions the GPA. Each changed status file says so.
- Human review of the CVs is still pending, as in version 2.

## Files

| Location | Contents |
| --- | --- |
| [resumes/](resumes/) | 100 final CV text files |
| [index.html](index.html) | Local HTML browser for all CVs |
| [profiles.jsonl](profiles.jsonl) | Structured records and internal rubric labels; changed records carry `gpa_consistency` |
| [evaluator_fields.jsonl](evaluator_fields.jsonl) | Applicant facts without analysis labels |
| [gpa_consistency_changes.json](gpa_consistency_changes.json) | Every changed value with before/after hashes and labels |
| [generation/](generation/) | Accepted CV descriptions and check statuses |
| [resume_manifest.json](resume_manifest.json) | CV/content paths and source hashes |
| [config.json](config.json), [rubric.json](rubric.json), [sampling_policy.json](sampling_policy.json) | Version 2 construction settings, copied unchanged |
| [checksums.json](checksums.json) | SHA-256 of every other file in this directory |

Use the packets in [version 4](../phd-applications-v4-recommendations-v2/) for evaluation. Do not send internal
labels or latent fields to an evaluator. From the repository root,
`python3 scripts/verify_datasets.py` rebuilds this dataset from version 2 and the
saved policy and compares every file.
