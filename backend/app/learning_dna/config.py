"""
Phase 3B scoring constants. Every weight and threshold below is an MVP
placeholder, not a scientifically validated value — the PRD is explicit
that these formulas must be simple, deterministic, and easy to change,
not treated as validated pedagogy. Keeping them in one module (rather
than inline in learning_dna/service.py) is what makes them easy to find
and tune later.
"""

# --- Concept mastery ----------------------------------------------------
# Weighted more toward conceptual understanding and standard application,
# per the PRD's scoring guidance. Multi-step/transfer count less here —
# failing those reflects problem-solving ability more than a raw
# understanding gap, which is why PROBLEM_SOLVING_WEIGHTS below applies
# the inverse emphasis.
CONCEPT_MASTERY_WEIGHTS: dict[str, float] = {
    "conceptual": 1.0,
    "formula_recall": 0.9,
    "numerical": 0.9,
    "application": 1.0,
    "multi_step": 0.6,
    "transfer": 0.5,
    "pyq_style": 0.8,
}
CONCEPT_MASTERY_DEFAULT_WEIGHT = 0.7  # used only if a question_type isn't in the map above

# --- Problem-solving score -----------------------------------------------
# Weighted toward application, multi-step, and transfer/unfamiliar
# questions; pure recall (formula_recall) gets a low weight since
# recalling a formula isn't evidence of being able to apply it to a new
# problem, per the PRD's explicit instruction.
PROBLEM_SOLVING_WEIGHTS: dict[str, float] = {
    "conceptual": 0.2,
    "formula_recall": 0.1,
    "numerical": 0.3,
    "application": 0.8,
    "multi_step": 1.0,
    "transfer": 1.2,
    "pyq_style": 0.6,
}
PROBLEM_SOLVING_DEFAULT_WEIGHT = 0.3

# --- Hint dependence -------------------------------------------------------
# The hint ladder (PRD Section 25) has 3 hints before a full explanation,
# so that's used as the normalization ceiling:
# hint_dependence = min(100, avg_hints_used_per_attempt / MAX_HINTS * 100).
HINT_DEPENDENCE_MAX_HINTS = 3

# --- Evidence confidence -----------------------------------------------------
# Step thresholds matching the PRD's example buckets:
# 1-2 evidence -> low, 3-5 -> medium-low, 6-10 -> medium. Beyond that,
# confidence keeps climbing slowly per additional evidence point but is
# hard-capped below 1.0 — confidence here means "how much evidence backs
# this number," never statistical certainty (PRD Principle 8).
CONFIDENCE_BUCKETS: list[tuple[int, float]] = [
    (2, 0.30),   # 1-2 evidence points -> low
    (5, 0.50),   # 3-5 -> medium-low
    (10, 0.70),  # 6-10 -> medium
]
CONFIDENCE_INCREMENT_PER_EXTRA_EVIDENCE = 0.01  # applied beyond the last bucket
CONFIDENCE_MAX = 0.90  # hard ceiling — confidence must never reach 1.0
