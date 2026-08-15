"""
Properties the FSRS scheduler must hold.

These assert on behaviour a student would notice - intervals that grow when
you keep getting something right, shrink when you forget it, and never send
an item away for a decade - rather than on the exact float the weights
happen to produce. Reweighting FSRS later should not break this file.
"""
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/lenin/Apps Developed/Socratic-ai/backend")

from services.review.scheduler import (  # noqa: E402
    new_state, review, interval_days, retrievability, mastery_strength,
    GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY,
    MAX_INTERVAL_DAYS, MIN_DIFFICULTY, MAX_DIFFICULTY,
)

T0 = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"pass  {label}")
    else:
        failures.append(label)
        print(f"FAIL  {label} {detail}")


# --- a brand new item -------------------------------------------------
fresh = new_state()
check("new item has no stability", fresh["stability"] == 0.0)

first_good = review(fresh, GRADE_GOOD, now=T0)
check("first good review schedules ahead", first_good["due_at"] > T0)
check("first good review sets stability", first_good["stability"] > 0)
check("first review counts as a rep", first_good["reps"] == 1)
check("first review is not a lapse", first_good["lapses"] == 0)

# Easy should always buy more time than good, which buys more than hard.
f_hard = review(fresh, GRADE_HARD, now=T0)["interval_days"]
f_good = review(fresh, GRADE_GOOD, now=T0)["interval_days"]
f_easy = review(fresh, GRADE_EASY, now=T0)["interval_days"]
check("hard < good < easy on first review", f_hard < f_good < f_easy,
      f"({f_hard:.2f}, {f_good:.2f}, {f_easy:.2f})")

# --- failing --------------------------------------------------------
failed = review(fresh, GRADE_AGAIN, now=T0)
check("a failed item returns within the session",
      failed["interval_days"] <= 10.0 / 1440.0)
check("a failed item records a lapse", failed["lapses"] == 1)

# --- repeated success grows the interval -----------------------------
state, when, intervals = new_state(), T0, []
last = None
for _ in range(6):
    state = review(state, GRADE_GOOD, now=when, last_reviewed_at=last)
    intervals.append(state["interval_days"])
    last = when
    when = state["due_at"]

check("intervals grow monotonically with repeated success",
      all(b > a for a, b in zip(intervals, intervals[1:])),
      f"{[round(i, 1) for i in intervals]}")
check("six good reviews reach a multi-week interval", intervals[-1] > 14,
      f"{intervals[-1]:.1f}d")
check("interval never exceeds the cap", all(i <= MAX_INTERVAL_DAYS for i in intervals))

# --- forgetting shrinks it -------------------------------------------
mature = state
lapsed = review(mature, GRADE_AGAIN, now=mature["due_at"],
                last_reviewed_at=mature["last_reviewed_at"])
check("a lapse never increases stability", lapsed["stability"] <= mature["stability"],
      f"{lapsed['stability']:.2f} vs {mature['stability']:.2f}")
check("a lapse increments the lapse count", lapsed["lapses"] == mature["lapses"] + 1)

# --- difficulty ------------------------------------------------------
hard_state = new_state()
when, last = T0, None
for _ in range(4):
    hard_state = review(hard_state, GRADE_HARD, now=when, last_reviewed_at=last)
    last, when = when, hard_state["due_at"]

easy_state = new_state()
when, last = T0, None
for _ in range(4):
    easy_state = review(easy_state, GRADE_EASY, now=when, last_reviewed_at=last)
    last, when = when, easy_state["due_at"]

check("consistently hard items stay harder than easy ones",
      hard_state["difficulty"] > easy_state["difficulty"],
      f"{hard_state['difficulty']:.2f} vs {easy_state['difficulty']:.2f}")
check("difficulty stays in range",
      all(MIN_DIFFICULTY <= s["difficulty"] <= MAX_DIFFICULTY
          for s in (hard_state, easy_state, lapsed)))

# --- a long absence ---------------------------------------------------
# The student vanishes for two years and then answers correctly. The
# interval must stay sane rather than exploding.
stale = review(mature, GRADE_GOOD, now=mature["last_reviewed_at"] + timedelta(days=730),
               last_reviewed_at=mature["last_reviewed_at"])
check("a two-year gap does not produce an absurd interval",
      stale["interval_days"] <= MAX_INTERVAL_DAYS, f"{stale['interval_days']:.0f}d")
check("a two-year gap still schedules forward", stale["interval_days"] > 0)

# --- retrievability ---------------------------------------------------
check("retrievability is 1.0 at zero elapsed", abs(retrievability(10, 0) - 1.0) < 1e-9)
check("retrievability decays with time", retrievability(10, 30) < retrievability(10, 1))
check("retrievability of an unseen item is 0", retrievability(0, 5) == 0.0)
check("interval is ~stability at target retention",
      abs(interval_days(10.0) - 10.0) < 1.0, f"{interval_days(10.0):.2f}")

# --- mastery roll-up --------------------------------------------------
check("unseen concept has no mastery", mastery_strength(0, 0, 0) == 0.0)
check("mastery rises with stability",
      mastery_strength(60, 0, 5) > mastery_strength(5, 0, 5))
check("lapses discount mastery",
      mastery_strength(30, 4, 8) < mastery_strength(30, 0, 8))
check("mastery stays within 0-1",
      0.0 <= mastery_strength(10_000, 0, 50) <= 1.0)

# --- input validation -------------------------------------------------
try:
    review(new_state(), 7, now=T0)
    check("out-of-range grade is rejected", False)
except ValueError:
    check("out-of-range grade is rejected", True)

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED: {failures}")
sys.exit(0 if not failures else 1)
