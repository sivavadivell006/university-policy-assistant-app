"""Central configuration: paths, thresholds, facets, offices."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "data" / "policies"

# --- retrieval / grading thresholds -------------------------------------
TOP_K = 6              # chunks retrieved per query
MIN_SCORE = 1.0        # BM25 score below which nothing is considered evidence
MIN_COVERAGE = 0.55    # share (IDF-weighted) of question terms found in evidence
REL_RATIO = 0.55       # a chunk is "relevant" if score >= REL_RATIO * best score
ANSWER_RATIO = 0.7     # extra sections are quoted only if close to the best match
MAX_EVIDENCE = 2       # sections quoted in a single answer
MAX_EVIDENCE_PROCESS = 3  # 'how do I...' answers also show conditions, deadline and fee
CATEGORY_BOOST = 1.3   # multiplier for chunks in the detected topic category

# --- topic detection (used for boosting and for choosing the right office)
CATEGORY_PATTERNS = {
    "attendance": r"attendance|condon|shortage|on[\s-]?duty|detain",
    "project": r"project|dissertation|thesis|capstone",
    "examination": r"exam|hall ticket|invigilat|malpractice|supplementary|make[\s-]?up|question paper|mobile|phone|grace|marks?\b|arrear|\bfail",
    "lab": r"\blabs?\b|laborator|safety|practical|experiment|record notebook|viva",
    "reevaluation": r"reevaluation|photocopy|answer script|recheck",
}

OFFICES = {
    "attendance": "your class advisor or the Department Academic Office",
    "project": "your Project Coordinator or the Department Office",
    "examination": "the Office of the Controller of Examinations",
    "lab": "your Lab In-charge or the Department Office",
    "reevaluation": "the Office of the Controller of Examinations",
    None: "the Department Office",
}

# --- facets: details the right answer can depend on ----------------------
# A policy section declares e.g. [project_type=final]. If the retrieved
# sections disagree on a facet and the student has not said which one applies,
# the assistant asks ONE clarification question.
FACETS = {
    "project_type": {
        "mini": r"\bmini\b",
        "final": r"final|capstone|major\b",
    },
    "assessment": {
        "internal": r"internal|continuous|\bcia\b|record|observation",
        "end_semester": r"end[\s-]?sem|external|practical exam|viva|university exam",
    },
}

FACET_PROMPTS = {
    "project_type": "Is this about a mini project (semesters 5-6) or a final-year (capstone) project?",
    "assessment": "Do you mean the internal (continuous) assessment or the end-semester practical exam?",
}

# --- query normalisation ---------------------------------------------------
PHRASE_MAP = [
    (r"last date|due date|cut[\s-]?off( date)?|by when|till when", "deadline"),
    (r"re[\s-]?evaluation|re[\s-]?valuation|revaluation|re[\s-]?check(ing)?", "reevaluation"),
    (r"xerox|photo[\s-]?copy|copy of (my )?(answer )?(script|paper)", "photocopy"),
    (r"laboratory|practicals?", "lab"),
    (r"cell ?phone|smart ?phone|mobile phone", "mobile"),
    (r"charges?|cost|amount|payment", "fee"),
    (r"attendence|attendace", "attendance"),
    (r"split( up)?|distribut\w*|break[\s-]?up|breakdown|scheme", "marks"),
]

# Words that describe the student's intent, not policy content. They are ignored
# when checking whether the retrieved evidence covers the question.
COVERAGE_IGNORE = {"eligible", "eligibility", "qualify", "allow", "policy", "rule", "procedure", "process", "possible"}
STEP_BOOST = 1.5       # process questions ("how do I...") favour sections with numbered steps
STEP_PENALTY = 0.85    # other questions slightly de-prioritise them
