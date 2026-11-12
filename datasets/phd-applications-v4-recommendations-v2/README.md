# PhD application packets — version 4

100 corrected CVs from [CV version 3](../phd-cvs-v3-gpa-consistency-v1/), each with three recommendation
summaries written from fixed templates. This version replaces
[packet version 3](../phd-applications-v3-recommendations-v1/) for evaluation. It made no model calls.

## What changed from version 3

1. **CVs.** The GPA line changed in the CVs listed in the CV dataset's README.
2. **Letters.** A grade-only course letter can no longer contradict the grade it
   cites. A grade of A- or better has no limited endorsement, and a grade of B
   or B+ has no strong endorsement; the removed probability moved to moderate.
   The seed and random streams are unchanged, so only letters whose original
   draw fell in a removed cell changed. That is 11 of 300 letters:

| Applicant | Letter | Course and grade | Strength v3 | Strength v4 |
| --- | --- | --- | --- | --- |
| PHDv3-123-00099 | L2 | Probability and Statistics: B+ | strong | moderate |
| PHDv3-123-01253 | L2 | Machine Learning: B | strong | moderate |
| PHDv3-123-01851 | L2 | Machine Learning: B | strong | moderate |
| PHDv3-456-00005 | L2 | Algorithms: A | limited | moderate |
| PHDv3-456-00797 | L2 | Probability and Statistics: B | strong | moderate |
| PHDv3-456-01157 | L2 | Machine Learning: B | strong | moderate |
| PHDv3-456-01571 | L2 | Machine Learning: A- | limited | moderate |
| PHDv3-456-01677 | L2 | Linear Algebra: B | strong | moderate |
| PHDv3-456-01731 | L1 | Probability and Statistics: B+ | strong | moderate |
| PHDv3-789-01110 | L2 | Algorithms: B+ | strong | moderate |
| PHDv3-789-01977 | L2 | Machine Learning: B | strong | moderate |

Every other letter is word-for-word identical to version 3. The full list is in
[letter_changes.json](letter_changes.json) and the settings are in
[policy.json](policy.json).

## Contents

| Location | Contents |
| --- | --- |
| [applications/](applications/) | 100 complete CV-plus-recommendation text packets |
| [recommendations/](recommendations/) | Three summaries per applicant |
| [resumes/](resumes/) | Byte-identical copies of the version 3 CVs |
| [index.html](index.html) | Local browser showing CVs and summaries |
| [recommendations.jsonl](recommendations.jsonl) | All 300 letters, fields and evidence links |
| [inputs/applicants.jsonl](inputs/applicants.jsonl) | Facts, accepted CV descriptions and CV text |
| [manifest.json](manifest.json) | Source and complete-packet hashes |
| [checksums.json](checksums.json) | SHA-256 of every other file in this directory |

The output contains 66 limited, 158 moderate and 76 strong
recommendations. Letter strength is separate from the applicant's CV tier.
Sampling probabilities remain provisional study settings; see
[RECOMMENDATIONS.md](../../RECOMMENDATIONS.md).

## Using the packets

Keep each applicant's packet identical across integrity conditions. The packet
files still begin with the internal applicant identifier, which encodes the
sampling seed. `phd_eval` removes that line and adds the integrity record when it
assembles a prompt; see [EVALUATION.md](../../EVALUATION.md). Do not paste these
files into a prompt by hand.
