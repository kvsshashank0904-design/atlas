"""
Diagnostic Engine constants (PRD Section 13). Kept in one module, same
pattern as learning_dna/config.py, so the selection mix and the
question-type/skill criteria behind each category are easy to find and
change — and so the engine can be pointed at a different chapter/subject
later without touching selection logic itself.

Nothing here hardcodes question text or content — only metadata
categories (question_type, problem_solving_skill), per the PRD
instruction that the diagnostic engine must generalize to future
subjects (SAT, university courses, etc.) without a rebuild.
"""
from app.questions.models import QuestionType, ProblemSolvingSkill

# Which chapter a diagnostic targets by default when the caller doesn't
# specify one explicitly. A string lookup (exam_pack + chapter name)
# rather than a hardcoded id, so re-seeding the DB doesn't break it and
# a future subject just needs its own chapter row + these two strings
# changed (or overridden per-call) — not a schema or code change.
DIAGNOSTIC_DEFAULT_SUBJECT_EXAM_PACK = "jee"
DIAGNOSTIC_DEFAULT_CHAPTER_NAME = "Mechanics"

# PRD Section 13 target mix. Values are MVP placeholders, not validated
# psychometrics — easy to retune here without touching selection code.
DIAGNOSTIC_TARGET_DISTRIBUTION: dict[str, int] = {
    "concept_understanding": 4,
    "standard_application": 5,
    "strategy_selection": 4,
    "multi_step": 4,
    "transfer": 3,
}

# Maps each distribution category to the existing Question metadata that
# qualifies for it. A question can only fill ONE category slot (the
# selector below tracks already-used question ids), so overlapping
# categories don't double-count a question.
DIAGNOSTIC_CATEGORY_CRITERIA: dict[str, dict] = {
    "concept_understanding": {
        "question_type": [QuestionType.CONCEPTUAL],
    },
    "standard_application": {
        "question_type": [
            QuestionType.APPLICATION,
            QuestionType.NUMERICAL,
            QuestionType.FORMULA_RECALL,
            QuestionType.PYQ_STYLE,
        ],
    },
    "strategy_selection": {
        "problem_solving_skill": [
            ProblemSolvingSkill.STRATEGY_SETUP,
            ProblemSolvingSkill.CONCEPT_SELECTION,
        ],
    },
    "multi_step": {
        "question_type": [QuestionType.MULTI_STEP],
    },
    "transfer": {
        "question_type": [QuestionType.TRANSFER],
    },
}
