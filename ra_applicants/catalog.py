"""Fictional, source-linked work examples for the plan's RA criteria."""

CONTEXTS = (
    "public news summaries with topic labels and publication metadata",
    "public research abstracts with subject labels and bibliographic metadata",
    "public product reviews with rating-derived sentiment labels and product metadata",
    "public programming questions with category labels and post metadata",
    "public policy excerpts with hand-coded topic labels and document metadata",
    "public company report excerpts with section labels and reporting-period metadata",
)
FAMILIES = {
    "text_classification":{"topic":"classification of public text records","nlp":True,"materials":"provided labeled document examples"},
    "text_retrieval":{"topic":"retrieval from a public text collection","nlp":True,"materials":"provided query examples and document-relevance judgments"},
    "entity_extraction":{"topic":"organization and date extraction from public text","nlp":True,"materials":"provided examples with manually checked organization and date spans"},
    "corpus_exploration":{"topic":"exploration of themes in public text","nlp":True,"materials":"provided document samples and a topic-coding guide"},
    "data_integration":{"topic":"integration of document metadata tables","nlp":False,"materials":"provided metadata tables and a data dictionary"},
    "visual_reporting":{"topic":"visual analysis of document metadata","nlp":False,"materials":"provided metadata tables and a data dictionary"},
}
PROJECT_TYPES = {
    "Undergraduate course project":("undergraduate",(2,3,4)),
    "Undergraduate capstone":("undergraduate",(5,6,8)),
    "Undergraduate independent study":("undergraduate",(3,4,6)),
    "Graduate course project":("graduate",(2,3)),
}
PROGRAMMING = (
    {"tasks":["ran a supplied Python notebook to load the provided records","edited simple filters and loops with step-by-step guidance"],"tools":["Python"],"artifact":"Annotated notebook and a record of the changes made with guidance"},
    {"tasks":["wrote Python functions for parsing the provided records","tested transformations on hand-checked input examples"],"tools":["Python","unittest"],"artifact":"Processing functions with checked examples and usage instructions"},
    {"tasks":["implemented reusable Python modules for the recorded workflow","wrote regression tests for malformed and edge-case inputs"],"tools":["Python","pytest","Git"],"artifact":"Processing modules, regression tests and documented expected behavior"},
)
DATA_ANALYSIS = (
    {"tasks":["cleaned supplied metadata tables using provided steps","plotted record counts and inspected missing-value summaries with guidance"],"tools":["pandas","Matplotlib"],"artifact":"Cleaning notebook with record-count plots and missing-value summaries"},
    {"tasks":["joined document identifiers to metadata using SQL and checked unmatched records","visualized group comparisons and documented missing-data handling"],"tools":["SQL","SQLite","pandas","Matplotlib"],"artifact":"Join queries, checked analysis tables and annotated comparison figures"},
    {"tasks":["validated SQL joins with duplicate-key and unmatched-record checks","visualized how group comparisons changed under alternative cleaning rules"],"tools":["SQL","SQLite","pandas","Matplotlib"],"artifact":"Validated join queries, sensitivity comparisons and figures explaining the cleaning assumptions"},
)
DATAFRAME_ANALYSIS = (
    DATA_ANALYSIS[0],
    {"tasks":["joined document identifiers to metadata using pandas merges and checked unmatched records","visualized group comparisons and documented missing-data handling"],"tools":["pandas","Matplotlib"],"artifact":"Dataframe merge code, checked analysis tables and annotated comparison figures"},
    {"tasks":["validated pandas merges with duplicate-key and unmatched-record checks","visualized how group comparisons changed under alternative cleaning rules"],"tools":["pandas","Matplotlib"],"artifact":"Validated dataframe merges, sensitivity comparisons and figures explaining the cleaning assumptions"},
)
NLP = {
    "text_classification":(
        {"tasks":["ran supplied tokenization and word-count steps on document samples","inspected vocabulary examples with guidance before attempting classification"],"tools":["NLTK"],"artifact":"Tokenization notebook and vocabulary inspection notes"},
        {"tasks":["used TF-IDF features and a logistic-regression text classifier","evaluated a fixed held-out split using macro F-score and example errors"],"tools":["scikit-learn"],"artifact":"Baseline classifier notebook, held-out evaluation and error examples"},
        {"tasks":["compared a TF-IDF classifier with a majority-label reference on held-out document groups","checked near-duplicate overlap and examined label-specific errors across repeated splits"],"tools":["scikit-learn"],"artifact":"Classifier comparison, split-overlap checks and label-specific error analysis"},
    ),
    "text_retrieval":(
        {"tasks":["ran supplied tokenization steps on the document collection","inspected query terms and example matches with guidance"],"tools":["NLTK"],"artifact":"Tokenization notebook and inspected query-match examples"},
        {"tasks":["ranked documents for provided queries using TF-IDF similarity","checked retrieved documents against a small judged query set"],"tools":["scikit-learn"],"artifact":"Retrieval notebook with ranked examples and relevance-check notes"},
        {"tasks":["compared TF-IDF and pretrained sentence-embedding retrieval on held-out judged queries","examined recall at fixed cutoffs and grouped retrieval errors by query type"],"tools":["scikit-learn","sentence-transformers"],"artifact":"Held-out retrieval comparison, cutoff-based recall summaries and query error analysis"},
    ),
    "entity_extraction":(
        {"tasks":["ran supplied tokenization steps on document excerpts","inspected organization-name and date examples with guidance"],"tools":["NLTK"],"artifact":"Tokenized excerpts and inspected organization/date examples"},
        {"tasks":["used regular-expression and dictionary rules to extract organization and date spans","compared extracted spans with provided manually checked examples"],"tools":["Python re"],"artifact":"Extraction rules and a table of checked span matches and errors"},
        {"tasks":["compared rule-based and pretrained spaCy extraction on held-out annotated excerpts","checked span precision and recall and analyzed errors by entity type"],"tools":["Python re","spaCy"],"artifact":"Held-out extraction comparison, span metrics and entity-type error analysis"},
    ),
    "corpus_exploration":(
        {"tasks":["ran supplied tokenization and frequency-count steps on document samples","inspected frequent terms with guidance using the topic-coding guide"],"tools":["NLTK"],"artifact":"Frequency-count notebook and inspected term examples"},
        {"tasks":["applied a documented topic dictionary to document samples","checked dictionary matches against manually reviewed examples"],"tools":["NLTK"],"artifact":"Dictionary coding notebook and manually reviewed match examples"},
        {"tasks":["compared dictionary coding with nonnegative-matrix-factorization topic exploration","examined topic stability across repeated fits and inspected documents supporting each interpretation"],"tools":["scikit-learn"],"artifact":"Theme comparison, repeated-fit stability checks and supporting document examples"},
    ),
}
WORK_EVIDENCE = {
    "independence":(
        "Needed frequent prompts to choose the next task and bring stalled work to review.",
        "Completed agreed routine tasks between check-ins and brought unresolved questions to review.",
        "Planned a sequence of checks, investigated unexpected inputs and brought remaining design questions to review.",
    ),
    "teamwork":(
        "Shared assigned files, but needed prompts to communicate changes that affected the group's review.",
        "Shared progress and files with the review group and incorporated the agreed revisions.",
        "Coordinated review of shared inputs and explained changes so the group could integrate the contribution.",
    ),
    "organization":(
        "Folder names and handoff notes needed clarification before the review group could follow the workflow.",
        "Maintained dated task notes and tracked pending checks alongside the working files.",
        "Kept input versions, the task queue and decision notes aligned so reviewers could locate each change.",
    ),
    "written_communication":(
        "The methods summary listed steps, but the reviewer needed clarification of their purpose and limitations.",
        "The methods summary explained the recorded steps and separated observations from interpretations.",
        "The methods summary connected choices to the task, explained limitations and incorporated substantive reviewer comments.",
    ),
    "oral_communication":(
        "The briefing covered the activity, but follow-up questions were needed to clarify the main result and next step.",
        "The briefing clearly summarized the activity and answered routine questions about the recorded work.",
        "The briefing explained methodological choices and limitations, and addressed questions without overstating the findings.",
    ),
}
INTEREST = (
    "I am mainly looking to develop general coding experience; academic research is one of several directions I am considering.",
    "I am interested in supporting academic research through text analysis, data preparation and discussion of findings with a research group.",
    "I am interested in translating academic research questions into text-analysis choices, examining assumptions and helping explain findings to a research team.",
)


def technical_bundle(domain, family, level, variant='sql'):
    if domain == "programming": return PROGRAMMING[level]
    if domain == "data_analysis":
        if variant not in ('sql','dataframe'):raise ValueError('Unknown data-analysis pathway')
        return (DATA_ANALYSIS if variant=='sql' else DATAFRAME_ANALYSIS)[level]
    if domain == "nlp": return NLP[family][level]
    raise ValueError("Unknown technical domain")


def technical_level(domain, family, evidence):
    for level in range(3):
        for variant in ('sql','dataframe'):
            if evidence == technical_bundle(domain,family,level,variant): return level
    raise ValueError("Unsupported or contradictory technical evidence")


def implementation_support(evidence):
    if evidence['programming'] != PROGRAMMING[0]:
        return None
    methods = 'NLP and analysis' if 'nlp' in evidence else 'analysis'
    return (f'Supplied Python notebooks implemented the recorded {methods} procedures. '
            'The applicant executed and inspected them and made the recorded guided code edits. '
            + ('SQL tasks describe separate work.' if 'SQL' in evidence['data_analysis']['tools'] else '')).strip()
