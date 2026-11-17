"""Coherent study designs with topic-specific rationales and substantive tradeoffs.

Levels encode provisional methodological anchors. They are not novelty verdicts
and are never rendered as applicant ratings.
"""

from .catalog import TOPICS, IMPACT_AREAS

CONTEXTS = {
    "text_classification": ["public product-review text", "public news-topic text", "public question-category text", "public discussion-topic text"],
    "software_testing": ["public parsing utilities", "public numerical utility libraries", "public data-cleaning libraries", "public file-format utilities"],
    "database_queries": ["public transit timetable tables", "public environmental measurement tables", "public bibliographic tables", "public municipal service tables"],
    "graph_algorithms": ["public urban bus networks", "public regional rail networks", "public multimodal transit networks", "public walking-route networks"],
    "time_series": ["public air-quality sensor series", "public rainfall measurement series", "public river-level measurement series", "public temperature sensor series"],
    "program_analysis": ["public list-processing example programs", "public file-processing example programs", "public numeric-computation example programs", "public string-processing example programs"],
    "image_robustness": ["public small-object image collections", "public handwritten-symbol image collections", "public natural-scene image collections", "public texture image collections"],
    "reproducible_workflows": ["public environmental analysis workflows", "public transport analysis workflows", "public bibliographic analysis workflows", "public municipal-data analysis workflows"],
}

STUDIES = {
    "text_classification": {
        "foci": ["training-set size", "rare-label frequency", "document-length variation"],
        "rationale": "Overall accuracy can conceal failures on short documents and rare labels, making it difficult to decide when additional training data help those groups.",
        "question": "How does {focus} change the relative performance of linear and compact encoder classifiers on {context}?",
        "contribution": "Identify conditions where the encoder's additional training cost improves minority-label performance, and where the simpler classifier retains comparable performance.",
        "methods": ["Fit a linear classifier and a compact encoder to one training split, vary {focus}, and compare the resulting aggregate accuracy values.", "Compare the classifiers across several settings of {focus}, using a fixed held-out split and inspecting errors within each label group.", "Compare the classifiers under matched training budgets across {focus}, separate near-duplicates before splitting, and repeat training on multiple held-out partitions."],
        "evaluation": ["Use overall accuracy from the selected split to rank the settings and summarize several illustrative classification errors.", "Report macro F-score, label-specific errors and training time on the held-out split; compare patterns across the chosen settings.", "Report macro F-score, label-specific errors and training cost with repeated-split uncertainty estimates; test whether the pattern transfers to a separately held-out collection."],
        "limits": ["A result from one split may depend on its label mix and may not describe performance on a different collection.", "The fixed test split permits controlled comparisons, while uncertainty across new training samples and collections remains a limitation.", "Label definitions and duplicate detection can change the apparent effect; retain per-collection results and test the result under alternative deduplication rules."],
    },
    "software_testing": {
        "foci": ["test execution budget", "defect type", "library version change"],
        "rationale": "Coverage can increase without detecting additional faults, so a useful selection strategy must preserve defect detection while reducing execution cost.",
        "question": "How does {focus} affect fault detection by coverage-guided test selection on {context}?",
        "contribution": "Characterize when coverage is a useful proxy for fault detection and identify failure categories where inexpensive test selection loses important evidence.",
        "methods": ["Select a small pair of library versions, vary {focus}, and compare coverage-guided test subsets with the full suite using the recorded defect cases.", "Compare coverage-guided and random test subsets under matched budgets, varying {focus} across several library versions with reproducible defects.", "Compare budget-matched coverage-guided and random subsets across {focus}, define defect categories before selection, and reserve library versions for a transfer check."],
        "evaluation": ["Report the number of detected recorded defects and the test-suite execution time for each chosen setting.", "Report defect detection and runtime by version and defect type, repeating the random selection to estimate its variability.", "Report detection loss and runtime with repeated-selection intervals on held-out versions; separate real-defect results from any mutation-based supplementary check."],
        "limits": ["The selected library and its recorded defects provide a narrow basis for claims about the usefulness of coverage-guided selection.", "Repeated random selection helps compare methods, while results can still depend on which library versions are included.", "Defect availability can favor well-documented libraries; report inclusion rules and examine whether conclusions change when libraries are held out."],
    },
    "database_queries": {
        "foci": ["read-to-update ratio", "query selectivity", "table-size variation"],
        "rationale": "An index can accelerate reads while imposing storage and update costs; a recommendation based only on query latency can therefore be misleading.",
        "question": "How does {focus} change the balance of query latency, update overhead and storage for indexes on {context}?",
        "contribution": "Identify workload conditions where an indexing choice changes from a useful speed improvement to an avoidable maintenance cost.",
        "methods": ["Run one ordered workload on a database with and without indexes, vary {focus}, and record the resulting elapsed times.", "Replay matched workloads across {focus} with fixed index configurations, consistent warm-up and repeated runs on the same machine.", "Vary {focus} under matched database states, randomize workload order, standardize warm-up, and reserve workload mixes for checking the indexing tradeoff."],
        "evaluation": ["Compare average query time and index size for the chosen workload, then describe the observed changes across settings.", "Report median query time, update cost and storage by setting, separating read-heavy and update-heavy workload results.", "Report median and tail latency, update overhead and storage with run-to-run intervals; test whether the inferred tradeoff persists on held-out workload mixes."],
        "limits": ["Workload order and a single database state can affect timings, limiting the interpretation of a small latency difference.", "Standardized runs improve comparability, while the fixed machine and workload family limit transfer to other installations.", "Cache effects and skewed inputs may change the preferred index; repeat key comparisons with cold starts and altered data skew."],
    },
    "graph_algorithms": {
        "foci": ["query repetition", "network sparsity", "localized route changes"],
        "rationale": "Graph preprocessing can reduce query time but becomes expensive when routes change, so query speed alone does not describe the useful operating range.",
        "question": "How does {focus} affect the total cost of preprocessed shortest-path queries on {context}?",
        "contribution": "Map the conditions under which preprocessing repays its construction cost while retaining correct route costs after the tested changes.",
        "methods": ["Implement a preprocessing strategy on one network, vary {focus}, and compare query execution time with unmodified Dijkstra search.", "Compare preprocessing and Dijkstra search across {focus}, checking path costs on fixed query sets and recording preprocessing time.", "Vary {focus} across held-out network regions, compare total preprocessing and query cost, and test path-cost agreement after each controlled route change."],
        "evaluation": ["Report average query latency and several checked path costs from the selected network and query set.", "Report path-cost agreement, preprocessing time, memory and query latency for the selected network sizes and settings.", "Report correctness failures and total cost with repeated-query intervals; locate break-even query counts and verify them on held-out network regions."],
        "limits": ["A single query set can favor the selected preprocessing strategy and gives limited evidence about update-heavy uses.", "The comparison covers static and controlled changes, but may not reflect the frequency of changes in operational routing systems.", "Controlled changes do not reproduce live transport disruptions; report sensitivity to changed edges and separate correctness from timing conclusions."],
    },
    "time_series": {
        "foci": ["missing-observation frequency", "outage duration", "seasonal variation"],
        "rationale": "A low average forecast error may hide failure during extended outages; comparing missingness patterns can clarify when imputation ceases to be useful.",
        "question": "How does {focus} affect imputation and short-horizon forecasting on {context}?",
        "contribution": "Characterize conditions where simple imputation preserves forecast usefulness and where uncertainty or long outages undermine that conclusion.",
        "methods": ["Apply simple imputation to one chronological split, vary {focus}, and compare forecast errors with a seasonal-naive reference.", "Compare several imputation methods across {focus}, retain chronological splits, and evaluate separately by sensor and missingness pattern.", "Vary {focus} across chronological evaluation windows, preserve a final holdout period, and compare imputation with seasonal-naive and unaltered-input reference forecasts."],
        "evaluation": ["Summarize mean absolute error over the selected test period and inspect example forecasts near missing observations.", "Report forecast errors by sensor and outage pattern over several windows, including the error of the seasonal-naive reference.", "Report sensor-level error distributions and uncertainty across windows; test whether conclusions hold for long contiguous outages in the final holdout period."],
        "limits": ["The chosen period may underrepresent extended outages and seasonal changes that would alter the preferred method.", "Chronological evaluation avoids future-data leakage, while simulated missingness may differ from the process causing actual sensor failures.", "Observed sensor failures can have different causes from injected missingness; compare several patterns and avoid interpreting associations as causal outage effects."],
    },
    "program_analysis": {
        "foci": ["nesting depth", "helper-function boundaries", "identifier reuse"],
        "rationale": "A warning rule that matches a useful surface pattern can still generate false positives when surrounding program context changes its meaning.",
        "question": "How does {focus} affect false warnings from syntax-pattern checks on {context}?",
        "contribution": "Identify contexts where additional syntax information reduces false warnings and document cases where that extra complexity still misses the intended distinction.",
        "methods": ["Implement context-aware checks for one set of examples, vary {focus}, and compare their warning counts with simple pattern matching.", "Compare context-aware and pattern-only checks across {focus}, manually check example labels, and retain a separate evaluation subset.", "Vary {focus} in examples reserved by program family, define labeling rules before tuning, and have a collaborator independently recheck a subset of warning labels."],
        "evaluation": ["Count warnings and inspect examples judged useful or unhelpful in the selected program collection.", "Report precision and recall on the evaluation subset, separating warning categories and documenting ambiguous labels.", "Report precision and recall by context with uncertainty intervals, adjudicate labeling disagreements, and evaluate on program families excluded from rule tuning."],
        "limits": ["Warning counts alone do not establish accuracy, and hand-picked examples can favor the implemented rule.", "A separate evaluation subset limits direct tuning effects, while related program templates may still occur on both sides of the split.", "Manual labels and template overlap can distort apparent gains; publish the labeling rules and repeat analysis after excluding near-duplicate program families."],
    },
    "image_robustness": {
        "foci": ["blur intensity", "brightness variation", "training-set size"],
        "rationale": "An augmentation can improve transformed-image accuracy while harming unchanged images, making aggregate accuracy an incomplete guide to robustness.",
        "question": "How does {focus} affect the benefit and cost of training augmentation on {context}?",
        "contribution": "Map where an augmentation improves transformed-image performance without unacceptable loss on unchanged inputs, including settings where the tradeoff reverses.",
        "methods": ["Train compact classifiers with and without an augmentation on one split, vary {focus}, and compare accuracy on transformed images.", "Compare augmentations across {focus} under matched training budgets, retaining held-out unchanged images alongside transformed test inputs.", "Vary {focus} under matched budgets and repeated training seeds, reserve transformation intensities for evaluation, and separate tuning images from the final test set."],
        "evaluation": ["Report transformed-image accuracy from the chosen split and show representative misclassified images for each setting.", "Report unchanged and transformed accuracy together with training time, separating results by transformation intensity.", "Report paired accuracy differences and repeated-seed intervals for unchanged and held-out transformations; examine whether improvements persist beyond the tuning intensities."],
        "limits": ["A single split and transformed-only evaluation can obscure losses on ordinary images and variation between training runs.", "Testing both input types reveals tradeoffs, while transformation settings chosen during development may still favor the selected augmentation.", "Artificial transformations approximate only some imaging changes; distinguish tested perturbation tolerance from claims about deployment conditions or general visual robustness."],
    },
    "reproducible_workflows": {
        "foci": ["schema changes", "unit inconsistencies", "missing-value conventions"],
        "rationale": "A workflow can run successfully while producing a misleading table; examining silent processing faults can distinguish successful execution from reliable reuse.",
        "question": "How does {focus} affect fault detection by lightweight checks in {context}?",
        "contribution": "Characterize which silent processing failures inexpensive checks detect and which require contextual knowledge beyond schema validation.",
        "methods": ["Add checks to one workflow, vary {focus}, and inspect whether the selected processing faults cause a warning.", "Compare unchecked, schema-only and combined checks across {focus}, using a fixed list of processing faults and expected table outputs.", "Define fault categories before writing checks, vary {focus}, and reserve workflows and fault instances for evaluating schema-only and combined checks."],
        "evaluation": ["Count detected injected faults and describe the runtime of the selected workflow with the checks enabled.", "Report detected faults, false alarms and overhead by failure category, comparing the same fault cases across check sets.", "Report detection and false-alarm rates on held-out workflows with category-specific intervals; test whether conclusions change when fault prevalence differs."],
        "limits": ["Checks written around a small fault list can appear successful without covering the errors encountered in other workflows.", "Using shared fault cases permits comparisons, while a developer-selected fault list can still favor the implemented checks.", "Injected faults need not match real processing failures; disclose the fault taxonomy and distinguish detection coverage from claims about complete analytical correctness."],
    },
}

LOW_CONTRIBUTIONS = {
    "text_classification":"Describe how aggregate accuracy differs between the linear classifier and compact encoder across the selected settings, with illustrative classification errors.",
    "software_testing":"Describe how test selection changes recorded-defect detection and execution time in the selected library versions, using those cases to illustrate the tradeoff.",
    "database_queries":"Describe the observed query-latency and storage tradeoff for indexed and unindexed configurations across the selected settings.",
    "graph_algorithms":"Describe query latency and illustrative path-cost agreement under the selected settings on the chosen network.",
    "time_series":"Describe how imputation and the seasonal reference differ in average forecast error over the selected period, with examples near missing observations.",
    "program_analysis":"Describe how contextual checks change warning counts and illustrate warnings judged useful or unhelpful in the selected program collection.",
    "image_robustness":"Describe where augmentation improves or worsens transformed-image accuracy on the selected split, using representative errors to illustrate the differences.",
    "reproducible_workflows":"Describe which selected faults trigger the added checks in the chosen workflow and the observed runtime with those checks enabled.",
}


def proposal_bundle(family, context, focus, level):
    s = STUDIES[family]
    subst = {"context":context,"focus":focus}
    question = s["question"].format(**subst).replace("How does ", "How does variation in ")
    contribution = s["contribution"] if level else LOW_CONTRIBUTIONS[family]
    comparison = TOPICS[family]["comparison"] if level else "Use the stated reference approach on the same selected inputs, with the available implementation settings held fixed during the comparison."
    limitations = s["limits"][level]
    if family == "software_testing" and level:
        comparison = "Use the full test suite as an unrestricted reference, and compare random selection with coverage-guided selection under matched execution budgets."
    if family == "database_queries" and not level:
        question = question.replace("query latency, update overhead and storage", "query latency and storage")
    if family == "graph_algorithms":
        if not level:
            question = question.replace("total cost", "query latency")
        elif level == 1 and focus != "localized route changes":
            contribution = contribution.replace("after the tested changes", "on the tested graphs")
            limitations = "The comparison covers the selected static graphs, but may not reflect the frequency of changes in operational routing systems."
    if family == "reproducible_workflows" and not level:
        comparison = "Compare the workflow with and without the added checks on the same selected fault cases, holding other implementation settings fixed."
    method = s["methods"][level].format(**subst)
    if family == "time_series":
        method += " Fill missing historical inputs using past observations only, then forecast one step ahead with lagged-input ridge regression fitted only on earlier observations."
        comparison = "Compare the resulting ridge forecasts with seasonal-naive forecasts on the same test dates."
        if level:
            comparison += " Also apply the same ridge model to unaltered historical inputs as a reference."
    return {
        "question":question,
        "rationale":s["rationale"],
        "contribution":contribution,
        "method":method,
        "comparison":comparison,
        "evaluation":s["evaluation"][level],
        "feasibility":"Use small public inputs and university computing available through the department; schedule a pilot, comparisons and a written report within six months.",
        "limitations":limitations,
    }

DELIVERY_CONTEXTS = ["a campus learning centre", "a community education programme", "an open online learning group", "a student-led computing club"]
IMPACT_FOCI = ["interpreting an example", "reproducing an example", "adapting an example"]

def impact_bundle(family, setting, focus, level):
    area = IMPACT_AREAS[family]
    activity = area["activity"]
    return {
        "beneficiaries":area["beneficiaries"],
        "goal":area["goal"] + " The learning task is " + focus + ".",
        "activity":activity,
        "delivery":[f"Share the materials through {setting} and invite interested learners to use them during their own study time.", f"Seek a host at {setting}, offer a guided pilot activity and collect participant questions for a revised version.", f"Seek a host at {setting}, pilot the activity with volunteer learners, revise the difficult steps and offer a follow-up session."][level],
        "access":["Provide the materials online with brief instructions so interested learners can choose when and how to work through them.", "Offer the materials without a participation fee and provide worked examples suitable for learners using ordinary laptops or printed instructions.", area["access"]][level],
        "assessment":[f"Track views and downloads and collect optional comments about {focus} to decide which materials to share more widely.", f"Record activity completion and questions about {focus}; use participant comments to revise the examples and instructions after the pilot.", f"Use a short task on {focus} before and after the activity, inspect common mistakes and use optional feedback to revise the materials."][level],
    }

def proposal_level(proposal):
    for level in range(3):
        if proposal["components"] == proposal_bundle(proposal["catalog_family"],proposal["study_context"],proposal["focus"],level):
            return level
    raise ValueError("Unsupported or inconsistent study design")

def impact_level(impact):
    for level in range(3):
        if impact["components"] == impact_bundle(impact["catalog_family"],impact["delivery_context"],impact["focus"],level):
            return level
    raise ValueError("Unsupported or inconsistent impact design")
