# Verification record

## Live validation — 2026-11-01

The user authorized 100 PhD resumes using the environment API key. GPT-6 Astra
was verified as available and used with medium reasoning and strict structured
outputs for generation and a separate-context factual review. The existing
configuration was reduced to three cohorts of 33, 33, and 34 retained applicants
from pools of 50, 49, and 51. The provisional numerical distributions, scoring
rules, and original generation/review prompts were retained.

The run exposed a sampling defect missed by the earlier tests: creating a new
`Random(seed)` for selection repeated the random draws used for latent
preparation. Higher-preparation applicants consequently had more favorable
selection keys. Selection now uses a separate reproducible stream initialized
with `phd-selection:<seed>`. A regression case with equally populated selection
cells reduced the selected-minus-pool mean preparation difference from 0.811 to
0.023. All **26 automated tests passed** after the fix.

The initial live generation was interrupted and preserved under
`sample-100-resume-generated/audit/superseded-correlated-selection/`.
The corrected selection was completed before reusing 22 identical saved API
responses whose source facts and request hashes matched. No applicants were
selected based on whether their earlier wording passed.

Final results:

- **100 final CVs**, with 100 distinct IDs and no identical prose objects.
- **91 first-pass successes** and **nine wording rejections**: six contained
  digits, two used a restricted word, and one violated the bullet-length rule.
- Each rejected draft passed after one logged wording revision through the
  run-specific `finish_validation.py` helper. Fixed credentials were unchanged,
  original failures were retained, and existing validators and the reviewer
  prompt were reapplied. The core generator still has no automatic repair loop.
- All final raw generation/review responses matched the saved content and fixed
  facts. Rendered CV hashes, request hashes, index links, and exact reproduction
  of all sampled cohorts were checked. The API key was absent from saved files.
- Provisional labels: 41 weak, 19 borderline, 40 strong. Areas: 37 NLP,
  37 computer vision, 26 statistical ML. Pathways: 33 bachelor's, 34 master's,
  19 recent graduates, 14 industry returners.
- 213 unique saved API responses used 231,298 input and 62,727 output tokens
  (294,025 total), including the interrupted run and repairs, with cache copies
  deduplicated. Up to three interrupted initial calls may have been billed
  without a saved response; these figures are not a complete billing statement.

Browse `sample-100-resume-generated/index.html`. Individual CVs are in its
`resumes/` directory. The `VALIDATION_REPORT.txt`,
`validation_summary.json`, `artifact_verification.json`, source manifests, and
raw logs retain the detailed evidence. `human_review.csv` is blank for review.
The original implementation snapshot and sampling-fix diff are retained too.
The repair helper was additionally checked with simulated acceptance, bounded
rejection, cache reuse, and preservation of original failures.

This validates live execution and automated constraints. It does **not**
establish empirical PhD calibration, independence of the same-model review, or
human approval. The limitations below still apply except for the previously
untested live API compatibility. No full-size 30,000-profile run was performed.

## Initial verification — 2026-10-31

### Result

The codebase passes **25 automated tests** on Python 3.14.6. The existing suite
first passed 16 tests. Additional boundary tests exposed configuration-validation
and malformed-response errors; these were corrected before the final passing run.

Verification command:

```sh
python3 -m unittest discover -s tests -v
```

All generated fixtures use temporary directories. API clients are simulated;
HTTP-boundary tests replace the network transport. No live model calls or API
charges were incurred during this verification. Earlier prototype outputs are
not evidence for this version and are excluded from Git.

## Verified behavior

- Repeatable sampling for a given seed; different seeds produce different cohorts.
- Pool/selection sizes and selection without duplicate profile IDs.
- Count, date, publication-link and fixed-fact consistency across three seeds,
  including a test with 750 pool records per seed.
- Quantile boundary behavior, ties and duplicate-edge rejection.
- Configuration/source provenance and removal of analysis labels from CV facts.
- Inspection with no API key or client creation.
- CLI sampling, model selection, simulated generation, rendering and cached resume.
- A three-profile simulated batch requires six client calls; repeating it makes
  no additional calls.
- Invalid output, refusals and incomplete/malformed responses cannot produce an
  accepted CV; cached malformed envelopes are logged and not resubmitted.
- Changed run configuration, provenance or generation contract is rejected.
- Strict JSON-schema request construction, bounded transient HTTP retries and
  no automatic retry of timeouts or authentication failures.

## Corrections made during verification

1. Reject non-finite configuration values, fractional/boolean publication caps,
   invalid or noncanonical dates, and overlapping/unordered GPA bins.
2. Convert malformed HTTP JSON and response envelopes into controlled API errors
   instead of uncaught exceptions.
3. Preserve batch error reporting when malformed responses lack valid token-usage
   information, without treating unknown usage as a measured zero.

## Remaining limitations

Passing tests establish the implemented software behavior, not study validity.
The code remains a paper-inspired prototype rather than an exact reproduction
or a validated PhD applicant population model.

- PhD distributions, dependencies and index weights are provisional assumptions.
- Strong/borderline/weak labels are cohort-relative score groups, not implemented
  admissions rubric judgments or guarantees of the user's proposed examples.
- Rubric dimensions are partly represented; thesis/poster outputs, course
  difficulty and faculty fit are not fully modeled.
- A shared preparation level couples many attributes and limits mixed profiles.
- CV writing still permits substantive technical inventions; factual review does
  not establish preservation of applicant-strength categories.
- There are no fitted PhD population targets or completed human rubric reviews.
- No live API compatibility, model output quality or full-size performance test
  was performed in this verification.

The initial repository snapshot records this status without treating earlier
prototype outputs as approved study data.
