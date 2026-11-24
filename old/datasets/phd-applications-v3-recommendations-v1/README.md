# PhD application packets — version 3

100 unchanged version 2 CVs, each accompanied by three short recommendation
summaries. All summaries use fixed fill-in templates. This stage made no model
calls. Every letter includes writer type, strength level, comparison with other
students (Yes/No), and a specific work example (Yes/No).

| Location | Contents |
| --- | --- |
| [applications/](applications/) | 100 complete CV-plus-recommendation text packets |
| [recommendations/](recommendations/) | Three summaries per applicant, in 100 files |
| [resumes/](resumes/) | Byte-identical copies of the version 2 CVs |
| [index.html](index.html) | Local browser showing CVs and summaries |
| [recommendations.jsonl](recommendations.jsonl) | All 300 letters, fields and evidence links |
| [inputs/applicants.jsonl](inputs/applicants.jsonl) | Facts, accepted CV descriptions and CV text |
| [policy.json](policy.json) | Templates, seed, assignment probabilities and assumptions |
| [manifest.json](manifest.json) | Source and complete-packet hashes |
| [dataset.json](dataset.json) | Counts, distribution and validation metadata |
| [checksums.json](checksums.json) | SHA-256 of every other file in this directory |

Letter strength means limited, moderate or strong endorsement; it is separate
from the applicant's CV tier. Writer relationships and comparative judgments
are synthetic additions. Examples quote an existing activity from the linked
research, work or course-project entry. A grade-only letter has no concrete work
example. Observation periods match the linked role; no additional supervision
history, achievements or course-to-project links are invented.

The output contains 68 limited, 147 moderate and 85 strong recommendations.
There are 148 explicit comparisons and 97 specific examples. Writer types are
95 research supervisors, 200 course instructors and five work supervisors.
Summary bodies contain 30–100 words.

Sampling probabilities and the short-research restriction are provisional study
settings. Consistency checks do not establish realistic endorsement frequencies
or calibration against real admissions. See [RECOMMENDATIONS.md](../../RECOMMENDATIONS.md)
for the complete assignment table and template design.

Use `applications/` for evaluation, keeping each applicant's complete packet
identical across integrity conditions. Recommendation summaries do not change
the existing CV-only labels. Internal assignment metadata should not be included
as additional evaluator input.

From the repository root, run `python3 scripts/verify_datasets.py` to verify
checksums, original CV equality, exact templates, flags, source links and seeded
assignments. GitHub displays HTML source; download or clone to open the viewer.
