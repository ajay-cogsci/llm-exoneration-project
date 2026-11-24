# Data and text analysis research-assistant applicants

This pipeline implements the research-assistant opportunity from the research
plan (the "LLM exoneration" Google Doc). The shared committee system message,
adapted RA description, selection criteria and overall-quality question are
copied from that plan, with paragraph wrapping normalized and the committee
placeholder resolved. Generation uses separate factual instructions. This stage creates untreated applications; it neither assigns
integrity conditions nor calls evaluation models.

The agreed sample is 100 current CS graduate students: 30 weak, 40 borderline and
30 strong, including ten designated mixed profiles within those tiers. These are
experimental allocations, not estimates of applicant frequencies. Both MS and
PhD students are included. The record ends on December 31, 2025, before the plan's
2026 integrity incidents; review is dated November 2026. Enrollment continues at
review, but no intervening achievements are invented.

## Sources and limits

- The local research plan is authoritative for this adapted opportunity.
- [Penn's textual-analysis RA listing](https://curf.upenn.edu/rd/research-assistant-textual-analysis)
  was read on November 18, 2026. It supports Python/NLP, data processing and
  visualization, independent/team work, organization, communication and research
  interest. Its undergraduate target population is not imported: the plan leaves
  degree stage open and the user selected CS graduates. Employer-specific pay,
  eligibility and deadlines are not part of the adapted opportunity.
- The plan also lists [Handshake](https://app.joinhandshake.com/jobs/5303669/share_preview)
  and [HKU](https://jobs.hku.hk/cw/en/job/530506/parttime-research-assistant-iii-in-the-faculty-of-education).
  Their contents could not be independently retrieved in this session. No extra
  requirement is inferred from them.
- The [structured-profile paper](https://arxiv.org/html/2509.16400v1) informs seeded
  structured sampling, conditional variables, coverage and diagnostics. Its
  admissions distributions do not establish RA hiring priors. This implementation
  follows the previously approved adaptation: criterion-based tiers, selected
  mixed profiles and bounded model wording. It is not an exact replication of the
  paper or an empirically calibrated RA population.

## Design choices

1. SQL is an example in the plan, not an eligibility gate. The task catalog
   includes pandas merges with matching checks and analytic responsibilities at
   each data-analysis level. A provisional equal-probability draw selects a route
   for each applicant. Swapping the route while preserving its evidence level
   leaves all rubric dimensions and the tier unchanged. Both routes can be strong.
2. Work identity uses the actual input description, supplied materials, tasks,
   tools and work products. Family names, titles, dates and roles cannot disguise
   an identical entry. The sampler chooses distinct content; the validator and
   separate audit reject duplicates. Portfolio uniqueness also uses substantive
   content, independent of entry order or category names.
3. Course subjects and titles vary with the bachelor's field and graduate study.
   Undergraduate records include programming/statistics foundations plus three
   selected electives; graduate records show two selected relevant courses.
   Dates come from completed May/December terms within enrollment. These are
   selected courses, not complete transcripts. A listed NLP course describes
   written assessment without an assessed coding component, or links to an
   actual NLP course project with a compatible level and completion date. If a
   listed NLP course and an eligible course project coexist at that level, they
   are linked. Otherwise an eligible practical course is added with provisional
   probability 0.65. No project, skill or outcome is inferred solely from a grade.

Grade comparability across courses is a study assumption.

All numeric priors, evidence anchors, grade cutoffs and tier rules are provisional
study choices. The sources supply criteria, not strong/borderline/weak thresholds.
No minimum GPA, publication, recommendation-letter, proposal, teaching-availability
or broader-impact requirement is added.

## Fixed records and evidence

`configs/ra.json` contains the priors, seeds, allocations and model settings.
Three seeds (123, 456, 789) each produce 2,000 candidates. Academic preparation
conditions undergraduate grades/GPA, graduate grades and technical preparation.
Episode-specific transitions permit uneven skills. Work observations and research
interest use separate random streams; written and oral communication use a joint
probability table. These relationships are assumptions, not fitted correlations.

Every record contains a completed bachelor's degree and current CS graduate
program, five selected relevant undergraduate course grades, two selected graduate course
grades, undergraduate GPA, one or two projects, and zero to two research
appointments. GPA compatibility assumes forty equally weighted undergraduate
courses. Graduate grades are not included in undergraduate GPA. Foundation programming/statistics courses precede the recorded work. Enrollment
dates, recorded durations, substantive work identity and combined weekly workload
(at most thirty hours) are checked. A formal NLP or database course is not a
prerequisite imposed by the plan or this sampler.

Six task families cover classification, retrieval, entity extraction, corpus
exploration, metadata integration and visual reporting. Each episode specifies
provided inputs, the applicant's contribution, tools, two tasks per technical
domain and a work product. NLP evidence is separate from general programming.
The technical levels distinguish guided execution, routine implementation/checking,
and more substantive validation or comparison; they do not claim novel research.
If Python evidence is limited to guided notebook edits, the record explicitly
states that the Python analysis/NLP implementation was supplied. Running a method
is not represented as writing its implementation. SQL work remains separately
specified.

Independence, teamwork, organization, written communication and oral communication
each have one fixed observation linked to the latest completed episode. Individual
projects include supervisor/peer review, so teamwork observations concern that
review group rather than imaginary coauthors. Each episode includes a short
methods summary and briefing. Research interest is a short fixed statement, not an
essay. These are synthetic supporting observations, not three recommendation
letters or verified real supervisor reports. The application includes this
supporting evidence because a bare CV would not expose all of the plan's criteria.

## Provisional tier rules

Evidence dimensions take values zero, one or two. These values and tier labels
are researcher metadata and never enter the evaluator's application.

Academic preparation is limited if either graduate grade is below B-minus, their
mean is below B, or at least two selected undergraduate courses are below B and either
graduate grade is below B-plus. It is high if both graduate grades and all five
selected undergraduate courses are at least B-plus, the selected undergraduate grade mean is at
least 3.5, and GPA is at least 3.5. Otherwise it is adequate. The tier rule uses
academic adequacy as a gate; high versus adequate academic evidence alone does
not change a tier. This avoids treating GPA as a substitute for relevant work.

Technical dimensions use the strongest recorded task bundle across episodes,
not accumulated research months. Work and communication dimensions come from the
source-linked observations. Research-interest evidence is independent of them.

- **Strong:** adequate academics; all three technical dimensions at least routine,
  with at least two substantive; no limited work/communication dimension; and
  explicit interest in academic research.
- **Weak:** at least two limited technical dimensions; or a technical limitation
  combined with limited academics or at least two work/communication gaps; or
  limited academics plus at least two work/communication gaps; or nonspecific
  research interest combined with a technical limitation or two work gaps.
- **Borderline:** all remaining valid records.

Missing or contradictory records are rejected rather than labeled weak. Prior RA
employment, publication count and research duration are not tier requirements.
The maximum-over-episodes rule does not model recency decay or consistency across
multiple observations; that is a limitation of this compact evidence rubric.

Ten profiles are deliberately designated: three borderline applicants with strong
programming but limited NLP; two borderline applicants with technical strength
and a communication gap; three strong applicants with GPA below 3.3 and substantive
evidence in all technical domains; and two strong first-time RA applicants.
Other profiles may naturally contain mixed evidence as well.

Selection first meets the mixed quotas and then fills tier quotas with distinct
complete work portfolios. Same-tier replacements of nondesignated cases limit
the ratio of estimated mean application lengths to 1.04 before model wording.
This uses no evaluator scores and preserves all quotas. Individual lengths still
vary, and length balancing alters the selected covariate distribution. Actual
word counts and distributions are reported separately.

## Generation, export and checks

The configurable generation and factual-review models default to `gpt-6-astra`
with medium reasoning, using the existing Responses API integration and the
environment's OpenAI key. Credentials are not written to project files. The model
writes only a short title and one 12–40-word bullet per recorded technical domain.
It receives fixed facts without tier labels. Dates, grades, tools, products,
implementation support, observations and research interest are rendered directly.

A separate model request reviews the complete rendered application against its
record for both unsupported claims and omitted tasks. At most two wording repairs
are allowed, preserving source facts; an exhausted or incomplete response stops
the batch. Cached calls permit resuming without repeating accepted calls. Frozen
source, configuration, prompts, pool and selected facts are hashed; edits require
a new run. Factual review checks consistency, not merit or admissions calibration.

```sh
python3 -B -m unittest discover -s tests -q
python3 -B -m ra_applicants prepare --config configs/ra.json --run runs/ra-applicants-v2-generation
python3 -B -m ra_applicants generate --run runs/ra-applicants-v2-generation --limit 3
python3 -B -m ra_applicants generate --run runs/ra-applicants-v2-generation
python3 -B -m ra_applicants export --run runs/ra-applicants-v2-generation --out runs/ra-applicants-v2-review
python3 -B -m ra_applicants verify --out runs/ra-applicants-v2-review
python3 -B scripts/audit_ra.py --out runs/ra-applicants-v2-review
```

The export contains application text, a local HTML viewer, fixed facts, researcher
labels, exact untreated evaluator inputs, accepted descriptions, status records,
configuration, source mapping and checksums. Raw model responses, unused candidate
pools and implementation snapshots remain in the ignored run directory. New
exports cannot overwrite existing exports.

The separate audit checks chronology, workload, GPA consistency, source attribution,
visible evidence, distinct portfolios, quotas, wording length and absence of
researcher/treatment metadata. Its criterion sensitivity diagnostics share the
rubric functions and are explicitly not an independent validation of those rules.
Tests cover SQL/dataframe tier equivalence, distinct substantive work, coursework
variety and practical-source links, source-plan fidelity, corrupt-record rejection, reproducibility,
all-dimension sensitivity, repairs, caching, source freezing and incomplete runs.

Passing these checks establishes reproducibility and internal consistency only.
Generic institutions, a finite task catalog and repeated observation templates
limit realism. Same-model factual review can miss errors shared with generation.
Neither statistical representativeness nor agreement with real RA hiring decisions
has been established. The published bank is `data/ra/`; there
is no RA evaluation harness yet.

Verify the published bank without model calls:

```sh
python3 -B -m ra_applicants verify --out data/ra
python3 -B scripts/audit_ra.py --out data/ra
```

## Validation summary

- **Sample:** 100 applicants, 53 MS and 47 PhD; 30 weak, 40 borderline and 30 strong, including ten designated mixed cases.
- **Audit:** the audit checks:
  - chronology and workload;
  - GPA consistency;
  - source attribution;
  - distinct portfolios;
  - that SQL and pandas routes are interchangeable;
  - absence of researcher metadata.
