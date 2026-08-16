"""
FSRS scheduling, as pure functions.

Given what a student knew and how they just answered, work out when to ask
again. This is FSRS (Free Spaced Repetition Scheduler) rather than SM-2:
SM-2 tracks one "ease" number and systematically over-schedules material the
learner keeps failing, while FSRS models memory as two quantities that move
independently -

  stability   how many days this memory would survive before recall decays
              to the target retention. Grows with every successful review.
  difficulty  how resistant this particular item is to gaining stability.
              A hard fact stays hard; it does not become easy by being seen.

Nothing here touches the database or the model. Every function takes a plain
dict of state and returns a new one, which is the same shape as
services/lesson/generator.py and for the same reason: the scheduling rules
are the part most likely to be wrong, and this way the whole of them can be
tested in milliseconds without a session, a worker, or an API key.

Grades follow the FSRS convention throughout:

    1 = again   (failed - could not recall)
    2 = hard    (recalled, but with real effort)
    3 = good    (recalled correctly)
    4 = easy    (immediate, no hesitation)
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# FSRS-5 default weights. These are population-level defaults from the
# algorithm's published parameter fitting; they are deliberately not tuned
# per user here. Retuning needs review history, which review_logs is
# accumulating for exactly that purpose - see docstring in models/review.py.
DEFAULT_WEIGHTS = (
    0.40255, 1.18385, 3.173, 15.69105,   # initial stability by grade
    7.1949, 0.5345, 1.4604,              # initial + update difficulty
    0.0046, 1.54575, 0.1192, 1.01925,    # stability on success
    1.9395, 0.11, 0.29605, 2.2698,       # stability on lapse
    0.2315, 2.9898, 0.51655, 0.6621,     # short-term and easy bonus
)

# Recall probability we aim for at the moment an item comes due. 0.9 is the
# FSRS default and a reasonable trade: higher means more reviews for the
# same knowledge, lower means more forgetting between them.
TARGET_RETENTION = 0.90

# FSRS decay constants. Kept named rather than inline so the retrievability
# curve is legible.
DECAY = -0.5
FACTOR = 19.0 / 81.0

MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0
MIN_STABILITY = 0.01
# A cap on how far ahead anything can be scheduled. Without it a long-lived
# item drifts to intervals measured in decades, which is not a schedule so
# much as a deletion.
MAX_INTERVAL_DAYS = 365.0 * 5

GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY = 1, 2, 3, 4


def new_state() -> Dict[str, Any]:
    """State for an item that has never been reviewed."""
    return {
        "stability": 0.0,
        "difficulty": 0.0,
        "reps": 0,
        "lapses": 0,
        "last_grade": None,
    }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _initial_stability(grade: int, w=DEFAULT_WEIGHTS) -> float:
    return max(w[grade - 1], MIN_STABILITY)


def _initial_difficulty(grade: int, w=DEFAULT_WEIGHTS) -> float:
    return _clamp(w[4] - math.exp(w[5] * (grade - 1)) + 1, MIN_DIFFICULTY, MAX_DIFFICULTY)


def _next_difficulty(difficulty: float, grade: int, w=DEFAULT_WEIGHTS) -> float:
    """Difficulty drifts toward its easy-grade anchor but never resets.

    The mean reversion is what stops a single lucky "easy" from erasing a
    long history of struggling with an item.
    """
    delta = -w[6] * (grade - 3)
    damped = difficulty + delta * ((10 - difficulty) / 9)
    reverted = w[7] * _initial_difficulty(GRADE_EASY, w) + (1 - w[7]) * damped
    return _clamp(reverted, MIN_DIFFICULTY, MAX_DIFFICULTY)


def retrievability(stability: float, elapsed_days: float) -> float:
    """Probability of recall after `elapsed_days` at this stability."""
    if stability <= 0:
        return 0.0
    return float((1 + FACTOR * max(0.0, elapsed_days) / stability) ** DECAY)


def _stability_after_success(
    difficulty: float, stability: float, retr: float, grade: int, w=DEFAULT_WEIGHTS
) -> float:
    hard_penalty = w[15] if grade == GRADE_HARD else 1.0
    easy_bonus = w[16] if grade == GRADE_EASY else 1.0
    growth = (
        math.exp(w[8])
        * (11 - difficulty)
        * (stability ** -w[9])
        * (math.exp(w[10] * (1 - retr)) - 1)
        * hard_penalty
        * easy_bonus
    )
    return max(stability * (1 + growth), MIN_STABILITY)


def _stability_after_lapse(
    difficulty: float, stability: float, retr: float, w=DEFAULT_WEIGHTS
) -> float:
    lapsed = (
        w[11]
        * (difficulty ** -w[12])
        * (((stability + 1) ** w[13]) - 1)
        * math.exp(w[14] * (1 - retr))
    )
    # A lapse must never make an item MORE stable than getting it right
    # would have. Without this clamp a very stable item that is suddenly
    # forgotten can come back with a larger interval than before, which is
    # exactly backwards.
    return max(min(lapsed, stability), MIN_STABILITY)


def interval_days(stability: float, retention: float = TARGET_RETENTION) -> float:
    """Days until recall probability decays to `retention`."""
    if stability <= 0:
        return 0.0
    days = (stability / FACTOR) * (retention ** (1 / DECAY) - 1)
    return _clamp(days, 0.0, MAX_INTERVAL_DAYS)


def review(
    state: Dict[str, Any],
    grade: int,
    *,
    now: Optional[datetime] = None,
    last_reviewed_at: Optional[datetime] = None,
    retention: float = TARGET_RETENTION,
) -> Dict[str, Any]:
    """Apply one answer and return the new state plus the next due date.

    `state` is not mutated. The returned dict carries the same keys plus
    `due_at`, `interval_days` and `elapsed_days`, which the caller persists
    to review_schedules and review_logs respectively.
    """
    if grade not in (GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY):
        raise ValueError(f"grade must be 1-4, got {grade!r}")

    now = now or datetime.now(timezone.utc)
    stability = float(state.get("stability") or 0.0)
    difficulty = float(state.get("difficulty") or 0.0)
    reps = int(state.get("reps") or 0)
    lapses = int(state.get("lapses") or 0)

    elapsed_days = 0.0
    if last_reviewed_at is not None:
        elapsed_days = max(0.0, (now - last_reviewed_at).total_seconds() / 86400.0)

    first_review = reps == 0 or stability <= 0
    if first_review:
        stability = _initial_stability(grade)
        difficulty = _initial_difficulty(grade)
    else:
        retr = retrievability(stability, elapsed_days)
        difficulty = _next_difficulty(difficulty, grade)
        if grade == GRADE_AGAIN:
            stability = _stability_after_lapse(difficulty, stability, retr)
        else:
            stability = _stability_after_success(difficulty, stability, retr, grade)

    if grade == GRADE_AGAIN:
        lapses += 1

    days = interval_days(stability, retention)
    if grade == GRADE_AGAIN:
        # Failed items come back inside the same session rather than
        # tomorrow - the point of failing is to try again while the correct
        # answer is still in front of you.
        days = min(days, 10.0 / 1440.0)

    return {
        "stability": stability,
        "difficulty": difficulty,
        "reps": reps + 1,
        "lapses": lapses,
        "last_grade": grade,
        "last_reviewed_at": now,
        "due_at": now + timedelta(days=days),
        "interval_days": days,
        "elapsed_days": elapsed_days,
    }


def mastery_strength(stability: float, lapses: int, reps: int) -> float:
    """Roll one item's state up into a 0-1 sense of "do they know this".

    Deliberately not a success rate. Answering an easy item right five times
    in one sitting is not mastery, so this leans on stability - knowledge
    that has survived time - and discounts for repeated forgetting.
    """
    if reps <= 0 or stability <= 0:
        return 0.0
    # 30 days of stability reads as solid; the curve is steep early and
    # flattens, so early progress feels visible without overstating it.
    base = 1 - math.exp(-stability / 30.0)
    penalty = 1.0 / (1.0 + 0.35 * lapses)
    return round(_clamp(base * penalty, 0.0, 1.0), 4)
