"""
What counts as "the learner already knows this".

The asymmetry here is the whole point: skipping something a student has not
actually mastered leaves a hole they cannot see, while re-teaching something
they do know costs a few minutes. So the bar for "known" is high and the bar
for "shaky" is low, and these assertions pin that down.
"""
import sys

sys.path.insert(0, "/home/lenin/Apps Developed/Socratic-ai/backend")

from services.review.mastery import (  # noqa: E402
    classify, build_context, _filter_relevant,
    KNOWN_THRESHOLD, SHAKY_THRESHOLD, MAX_LISTED,
)

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"pass  {label}")
    else:
        failures.append(label)
        print(f"FAIL  {label} {detail}")


def row(name, strength, reviews=3, lapses=0):
    return {"name": name, "strength": strength,
            "review_count": reviews, "lapse_count": lapses}


# --- the basic split ---------------------------------------------------
known, shaky = classify([
    row("calvin cycle", 0.85),
    row("chlorophyll", 0.10),
    row("thylakoids", 0.42),          # between the thresholds: neither
])
check("a solid concept is known", known == ["calvin cycle"])
check("a weak concept is shaky", shaky == ["chlorophyll"])
check("a middling concept is neither", "thylakoids" not in known + shaky)

# --- never seen -------------------------------------------------------
never, _ = classify([row("photosynthesis", 0.0, reviews=0)])
check("a concept taught but never tested is not claimed as known", never == [])
_, never_shaky = classify([row("photosynthesis", 0.0, reviews=0)])
check("a concept never tested is not flagged as weak either", never_shaky == [])

# --- repeated forgetting overrides a high score -----------------------
known, shaky = classify([row("rubisco", 0.95, reviews=9, lapses=4)])
check("repeated lapses stop a concept counting as known", known == [])
check("repeated lapses mark it shaky instead", shaky == ["rubisco"])

known2, _ = classify([row("stomata", 0.95, reviews=9, lapses=1)])
check("a single lapse does not disqualify a strong concept", known2 == ["stomata"])

# --- ordering and caps -------------------------------------------------
many_known, _ = classify([row(f"c{i}", 0.9) for i in range(MAX_LISTED + 8)])
check("the known list is capped", len(many_known) <= MAX_LISTED)

ordered, _ = classify([row("weaker", 0.65), row("stronger", 0.99)])
check("known is ordered strongest first", ordered == ["stronger", "weaker"])

_, shaky_order = classify([row("bad", 0.02), row("less bad", 0.20)])
check("shaky is ordered weakest first", shaky_order == ["bad", "less bad"])

# --- threshold boundaries ---------------------------------------------
at_known, _ = classify([row("edge", KNOWN_THRESHOLD)])
check("the known threshold is inclusive", at_known == ["edge"])
_, at_shaky = classify([row("edge", SHAKY_THRESHOLD)])
check("the shaky threshold is exclusive", at_shaky == [])

# --- the prompt block --------------------------------------------------
check("no mastery produces no context", build_context([], []) == "")
ctx = build_context(["calvin cycle"], ["rubisco"])
check("known concepts are named", "calvin cycle" in ctx)
check("shaky concepts are named", "rubisco" in ctx)
check("known concepts are told not to be retaught", "from scratch" in ctx)
check("shaky concepts are told to be re-explained differently",
      "second angle" in ctx or "another" in ctx or "more time" in ctx)

only_known = build_context(["a"], [])
check("a known-only block omits the struggled section", "struggled" not in only_known)

# --- relevance filtering ----------------------------------------------
rows = [row("calvin cycle", 0.9), row("binary search", 0.9), row("chlorophyll", 0.9)]
filtered = _filter_relevant(rows, "Teach me the calvin cycle in more depth")
check("filters to concepts related to the request",
      [r["name"] for r in filtered] == ["calvin cycle"])

unrelated = _filter_relevant(rows, "Teach me about medieval history")
check("returns everything when nothing matches", len(unrelated) == len(rows))

short = _filter_relevant(rows, "hi")
check("returns everything for a request with no usable words", len(short) == len(rows))

# --- rows missing fields must not explode ------------------------------
messy, _ = classify([{"name": "", "strength": 0.9},
                     {"strength": 0.9},
                     {"name": "ok", "strength": None, "review_count": 2}])
check("rows with no name are skipped", messy == [])

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED: {failures}")
sys.exit(0 if not failures else 1)
