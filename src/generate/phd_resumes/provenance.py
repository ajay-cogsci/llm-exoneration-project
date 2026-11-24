"""Source-to-implementation map. Importing or inspecting this module generates no data."""

SOURCES = {
    "paper": {
        "url": "https://arxiv.org/html/2509.16400v1",
        "location": "Section 3 and Appendix D",
        "supports": "Conditional structured sampling, empirical marginals/dependencies, normalized composite indices, cohort quintiles, oversampling and distribution checks.",
        "limit": "Undergraduate admissions. It does not provide PhD distributions or use an LLM to generate the underlying applicant records.",
    },
    "paper_code": {
        "url": "https://github.com/hnghiem-nlp/ses_emnlp/blob/5817943ef9509c49494e15408463a51cc82a034e/src/ses_admissions/profiles.py",
        "supports": "Seeds, quantile construction and inverse-frequency sampling without replacement.",
        "limit": "The original sampling cells are SES by performance. Pathway by performance is a PhD implementation assumption.",
    },
    "uw": {
        "url": "https://grad.uw.edu/wp-content/uploads/Holistic-Admissions-2020.pdf",
        "location": "Sample evaluation rubric",
        "supports": "Academic preparation, research duration, responsibility, outputs, methods and program fit. Two years of research is one high-category anchor.",
        "limit": "A 2020 illustrative, broad graduate rubric, not a current ML admissions threshold or frequency estimate. GRE thresholds are not imported.",
    },
    "brandeis": {
        "url": "https://www.brandeis.edu/psychology/doctoral/how-to-apply.html",
        "original_url": "https://www.brandeis.edu/psychology/doctoral/phd-applicant-evaluation-rubric-111023.pdf",
        "location": "What We Look For (the original PDF link was unavailable; the official page contains the rubric)",
        "supports": "Relevant coursework, quantitative preparation, substantive research contributions, relevant methods, outputs and faculty fit. Thesis-equivalent research can support the high research category; a publication is not mandatory.",
        "limit": "Psychology rubric: transfer dimensions, not psychology-specific courses or claims about ML competitiveness. Essays and letters provide evidence a CV alone cannot supply.",
    },
    "penn": {
        "url": "https://www.cis.upenn.edu/admission-statistics/",
        "supports": "Reported mean GPA among admitted CIS applicants: 3.70 in 2023, 3.78 in 2022 and 3.80 in 2021.",
        "limit": "Admitted students only, not the applicant-pool distribution, an ML-only population, a minimum GPA or a standard deviation. Not a calibration target for the full synthetic pool.",
    },
    "cmu_2015": {
        "url": "https://instant.1point3acres.com/thread/121768",
        "supports": "No parameter is derived from this link.",
        "limit": "Older secondary repost; not used for numerical calibration or current admissions thresholds.",
    },
    "project": {
        "path": "LLM exoneration research plan.pdf",
        "supports": "CS PhD opportunity, academic preparation, research potential, fit, recommendation strength and fixed credentials across integrity conditions.",
        "limit": "This component makes CVs only. It does not fabricate recommendation letters or change treatment conditions.",
    },
    "user": {
        "supports": "Proposed strong/borderline/weak examples, PhD-only scope, OpenAI with a configurable model, and provisional numerical values for review.",
        "limit": "Providing provisional values does not establish empirical calibration or authorize execution.",
    },
}

FIELD_MAP = {
    "academic_preparation": {"fields": ["education", "gpa", "gpa_scale", "gpa_as_of", "coursework"], "sources": ["project", "uw", "brandeis", "penn"]},
    "research_potential": {"fields": ["research_experience.months", "research_experience.contribution", "publications", "projects"], "sources": ["project", "uw", "brandeis", "user"]},
    "quantitative_preparation": {"fields": ["coursework", "skills", "projects.scope"], "sources": ["brandeis", "project"]},
    "fit": {"fields": ["research_area"], "sources": ["project", "uw", "brandeis"], "limit": "Research area is visible evidence only; no specific faculty/lab is supplied, so actual faculty fit is not scored."},
    "work_and_internships": {"fields": ["work_experience", "research_experience.role"], "sources": ["user"], "limit": "Nontechnical work does not by itself imply weak research potential."},
    "letters_and_essays": {"fields": [], "sources": ["project", "brandeis"], "limit": "Outside the CV-only scope; no letter strength, writing quality, personal character or essay score is invented."},
}

# Every numerical family is traceable. Source support for a dimension must not
# be mistaken for support for its simulation probabilities or score weights.
PARAMETERS = [
    {"keys": ["seeds", "n_per_cohort", "oversample"], "basis": "paper", "sources": ["paper", "paper_code"], "note": "Original cohort defaults; not a requirement to execute that many records."},
    {"keys": ["review_month", "gpa_as_of"], "basis": "provisional", "sources": ["project"], "note": "Implementation dates chosen to accommodate the plan's 2026 coursework incidents; these exact dates are assumptions."},
    {"keys": ["pathways", "preparation_probabilities", "research_areas"], "basis": "provisional", "sources": ["user", "project"], "note": "A synthetic preparation variable and pathway mix, not measured PhD frequencies or the paper's income variable."},
    {"keys": ["gpa_bins", "gpa_bin_probabilities", "gpa_latent_rank_coefficient"], "basis": "provisional", "sources": ["penn", "paper"], "note": "Binning/rank alignment comes from the method; all PhD bin boundaries, masses and correlation settings are assumptions. Penn means cannot determine them."},
    {"keys": ["research_month_ranges_by_preparation", "contribution_by_preparation"], "basis": "provisional", "sources": ["uw", "brandeis", "user"], "note": "Qualitative rubric anchors inform duration and responsibility; five levels and their full intervals are implementation assumptions."},
    {"keys": ["publication_probability_per_six_months", "max_publications", "main_conference_probability_by_preparation", "first_author_probability"], "basis": "provisional", "sources": ["user", "brandeis", "uw"], "note": "Output fields are rubric-supported. Binomial probabilities, six-month opportunities, caps and venue/author mixtures are not reported PhD statistics."},
    {"keys": ["internship_count_ranges_by_preparation", "technical_project_count_ranges_by_preparation", "technical_work_probability_by_preparation"], "basis": "provisional", "sources": ["user"], "note": "User-proposed dimensions; all numerical relationships require review."},
    {"keys": ["coursework_by_preparation"], "basis": "provisional", "sources": ["brandeis", "project"], "note": "Explicit CS course/grade patterns operationalize relevant and quantitative preparation; they are not sampled transcripts or inferred from GPA."},
    {"keys": ["performance_weights", "performance_normalization", "strength_by_quintile", "subsample_cells"], "basis": "provisional", "sources": ["paper", "user"], "note": "Index construction is transferred; coefficients on PhD features, normalization choices, quintile-to-strength mapping and pathway strata are unvalidated adaptations. The paper's coefficients are not PhD importance weights."},
    {"keys": ["generation"], "basis": "engineering", "sources": ["user"], "note": "Optional CV wording and factual checks, additional to the paper's structured profiles. No model is selected automatically."},
]


def source_map(config):
    return {
        "sources": SOURCES,
        "field_map": FIELD_MAP,
        "parameters": [{**entry, "values": {key: config[key] for key in entry["keys"]}} for entry in PARAMETERS],
        "remaining_assumptions": [
            "Generic institutions, venues and employers; program-specific prestige is not modeled.",
            "Template degree dates; three-month internships; research and work hours and work-duration mixtures are template assumptions in sampling.py.",
            "Research periods are consecutive, do not overlap, and end at the review month; publications cannot precede their linked research.",
            "Strength is a provisional cohort-relative label, not an admit/reject truth or a guaranteed publication-count pattern.",
            "No empirical PhD joint distribution is supplied; distribution summaries are descriptive validation, not a fitted population claim.",
        ],
    }
