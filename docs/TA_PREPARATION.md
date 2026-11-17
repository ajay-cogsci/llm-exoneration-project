# Introductory-CS TA preparation

Status: offline preparation only. The original 11-condition PhD design is retained.
No TA applicant set, evaluation config, run plan, model panel, or spending cap is
approved. Nothing here authorizes model calls or human recruitment.

Three fictional examples and the exact adapted prompt are now available in
[TA review](TA_REVIEW.md) on `codex/ta-prep`. They are unapproved illustrations,
not a full applicant set. The [Claude Code handoff](TA_CLAUDE_CODE_PROMPT.md)
permits offline preparation and keeps all computational runs behind approval.

## What stays the same

- The original condition definitions and two wordings in
  [phd_eval_v1.json](../configs/phd_eval_v1.json): clean, pending, responsible,
  cleared, dismissed, withdrawn, exonerated_on_appeal, neutral_control,
  exonerated_acknowledged, responsible_rehabilitated, procedural_reversal.
- All three tasks: application quality, advancement, and final decision.
- Both formats: answer-only and rationale, with the same shared instructions.
- Hold each applicant packet fixed across all conditions. Use the same paired
  analysis logic, and validate that scores track applicant quality for the TA role.
- Keep PhD datasets and outputs unchanged. Any TA run will have its own dataset
  and run directory. Do not pool the two opportunities as one experiment.

The existing neutral administrative control is already included. No competence
case, new allegation type, or extra control is part of the initial TA extension.
Consider an additional control later only for a specific unresolved explanation;
if added, collect comparison cells at the same time and keep that extension separate.

## Existing opportunity draft

Copied from the shared research notes, not a new or live job advertisement:

**Introductory Computer Science Teaching Assistant**

**Description:** A university department seeks a teaching assistant for
introductory computer science. Responsibilities include leading lab or discussion
sections, holding office hours and answering student questions, grading student
work and providing feedback, and assisting the instructor with course administration.

**Selection criteria:** Knowledge of foundational computer science and programming,
shown by academic record in relevant courses; written and oral communication skills;
interest in teaching beginning programmers; previous teaching, tutoring, or TA
experience, including satisfactory past performance; availability for required
course duties.

Source notebook: [LLM exoneration](https://docs.google.com/document/d/1dgZkwce8f8iXa1Nt0kmj7WIPqrdzxcMJCaYEYm7VQ2s/edit).
Its attribution notes remain there; they have not been rechecked as current job
requirements in this preparation step.

## What needs preparation

The published 100 PhD packets contain academic and research evidence. Their fact
schema has no teaching/tutoring history, teaching-interest, or availability fields.
Their tiers reflect PhD preparation, not suitability for TA work. Merely changing
the opportunity title would leave several stated TA criteria unsupported.

Prepare a separate TA packet specification for review before generating a bank:

| Component | Required decision or evidence |
|---|---|
| Eligibility | Who can apply and when the appointment begins; do not assume all PhD applicants are enrolled TA candidates. |
| Subject preparation | Relevant introductory-CS/programming coursework and grades. |
| Teaching | Explicit experience or explicit no prior experience; duties, duration, and evidence of past performance where applicable. |
| Communication | Concrete support for explaining concepts and giving feedback, without inferring teaching skill from publication counts. |
| Interest and availability | A short stated interest and availability for the advertised duties. |
| Recommendations | If retaining three summaries for comparability, give each an appropriate source and evidence; do not recycle research endorsements as teaching evaluations. |
| Quality variation | Define weak, borderline, and strong TA profiles from TA criteria. Do not relabel the existing PhD tiers. |
| Timing | Ensure every applicant was enrolled when the original early-2026 coursework incident could have occurred. Any necessary date changes require review. |

These are proposed fields, not invented facts about the published applicants.
Review the three new example packets and adapted prompt before approving a full
dataset or making API requests. The examples use a common eligibility rule and
availability; the provisional tiers describe preparation for the TA role.

Only the opportunity, applicant evidence, and necessary role placeholders should
change for the initial extension: TA selection committee, interview, and hire/do
not hire instead of PhD admission. Show those changes explicitly at review.

If the eventual design keeps 100 applicants and one repeat, the original crossing
would again be 100 × 11 × 2 × 3 × 2 = 13,200 requests per model. That is a size
calculation, not an approved run. Estimate costs after the TA packet length and
model panel are chosen. Previous PhD/follow-up budgets do not authorize TA spending.

## Interpretation and approvals

This is a controlled disclosure study: the complete allegation/resolution history
is supplied in an institutional-record block. Do not claim that real admissions
or TA hiring normally receives all such records. A static packet measures response
to disclosed history, not sequential belief updating or an internal cognitive mechanism.

A human comparison remains a separate requirement for claims about human–LLM
differences. Additional model requests cannot substitute for human observations.

Review TA eligibility, packet examples, condition feasibility, prompt adaptation,
and the proposed model panel/budget before launch. The user must explicitly approve
any model run. The existing PhD harness and its defaults remain unchanged.
