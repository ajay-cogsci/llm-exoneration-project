# Verification record — 2026-10-31

## Result

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
