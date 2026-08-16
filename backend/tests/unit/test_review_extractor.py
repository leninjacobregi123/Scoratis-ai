"""
Parsing and normalising for concept extraction and question generation.

All of it runs without a model: the point of keeping these as pure functions
is that the handling of a malformed response is testable directly, and a
malformed response is the normal case, not the exception.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.review.extractor import (  # noqa: E402
    slug_for, strip_html, scene_text, scene_is_substantive,
    _normalise_concepts, _normalise_items, _normalise_grade, grade_mcq,
    _extract_json, ReviewGenerationError,
)

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"pass  {label}")
    else:
        failures.append(label)
        print(f"FAIL  {label} {detail}")


# --- slugging: the cheap duplicate catcher ---------------------------
check("slug ignores casing", slug_for("Photosynthesis") == slug_for("photosynthesis"))
check("slug ignores a leading article",
      slug_for("The Calvin Cycle") == slug_for("Calvin cycle"))
check("slug ignores punctuation", slug_for("F = ma!") == slug_for("F  ma"))
check("slug ignores accents", slug_for("Bézier curve") == slug_for("Bezier curve"))
check("distinct ideas keep distinct slugs",
      slug_for("photosynthesis") != slug_for("cellular respiration"))
check("empty name gives empty slug", slug_for("") == "")

# --- html stripping ---------------------------------------------------
check("strips tags", strip_html("<p>Hello <b>world</b></p>") == "Hello world")
check("decodes entities", strip_html("<p>a &amp; b</p>") == "a & b")
check("collapses whitespace", strip_html("<p>a</p>\n\n  <p>b</p>") == "a b")

# --- reading a real scene shape --------------------------------------
scene = {
    "id": "scene_1",
    "title": "What is Photosynthesis?",
    "slide": {"elements": [
        {"id": "title", "type": "text", "content": "<p>What is Photosynthesis?</p>"},
        {"id": "body", "type": "text", "content": "<p>Plants make food from light</p>"},
        {"id": "pic", "type": "shape"},
    ]},
    "actions": [
        {"type": "speech", "content": "Photosynthesis is how plants make their own food."},
        {"type": "spotlight", "elementId": "title"},
        {"type": "speech", "content": "It produces the oxygen we breathe."},
    ],
}
slide, narration = scene_text(scene)
check("slide text pulls only text elements",
      "Photosynthesis" in slide and "Plants make food" in slide)
check("narration pulls only speech actions",
      "own food" in narration and "spotlight" not in narration)
check("narration keeps both speech turns", narration.count("\n") == 1)
check("a substantive scene is kept", scene_is_substantive(scene))
check("a bare title card is skipped", not scene_is_substantive(
    {"id": "s", "slide": {"elements": [{"type": "text", "content": "<p>The End</p>"}]}}))

# --- concept normalising ---------------------------------------------
by_scene, edges = _normalise_concepts({
    "scenes": [
        {"scene_id": "scene_1", "concepts": [
            {"name": "Photosynthesis", "primary": True, "description": "d"},
            {"name": "photosynthesis"},                       # duplicate by slug
            {"name": "Chlorophyll", "primary": False},
            {"name": "Stroma"},
            {"name": "Thylakoid"},                            # over the cap
        ]},
        {"scene_id": "", "concepts": [{"name": "orphan"}]},   # no scene id
        "not a dict",
    ],
    "prerequisites": [
        {"before": "Light reactions", "after": "Calvin cycle"},
        {"before": "same", "after": "same"},                  # self-edge
        {"before": "", "after": "x"},                         # incomplete
    ],
})
check("duplicate concepts collapse by slug", len(by_scene["scene_1"]) == 3)
check("concepts per scene are capped", len(by_scene["scene_1"]) <= 3)
check("primary flag is preserved", by_scene["scene_1"][0]["primary"] is True)
check("non-primary flag is preserved", by_scene["scene_1"][1]["primary"] is False)
check("scene with no id is dropped", "" not in by_scene)
check("garbage entries are dropped", len(by_scene) == 1)
check("valid prerequisite kept", ("light-reactions", "calvin-cycle") in edges)
check("self-referential prerequisite dropped", len(edges) == 1)

# --- item normalising -------------------------------------------------
items = _normalise_items({"items": [
    {"kind": "recall", "prompt": "Why?", "answer": "Because.",
     "must_include": ["a", "b"]},
    {"kind": "mcq", "prompt": "Which?", "answer": "G3P",
     "options": ["G3P", "ATP", "O2", "H2O"]},
    {"kind": "mcq", "prompt": "Broken?", "answer": "missing",
     "options": ["a", "b", "c", "d"]},          # answer not among options
    {"kind": "weird", "prompt": "Odd?", "answer": "yes"},   # unknown kind
    {"prompt": "No answer?"},                                # unusable
    {"answer": "No prompt"},                                 # unusable
]})
check("valid items survive", len(items) == 4)
check("mcq keeps its options", items[1]["rubric"]["options"] == ["G3P", "ATP", "O2", "H2O"])
check("mcq whose answer is absent degrades to recall", items[2]["kind"] == "recall")
check("unknown kind degrades to recall", items[3]["kind"] == "recall")
check("rubric carries must_include", items[0]["rubric"]["must_include"] == ["a", "b"])
check("items missing prompt or answer are dropped",
      all(i["prompt"] and i["answer"] for i in items))

# --- grading ----------------------------------------------------------
g, fb = _normalise_grade({"grade": 3, "feedback": "Good."})
check("grade parses", g == 3 and fb == "Good.")
check("grade above range is clamped", _normalise_grade({"grade": 9})[0] == 4)
check("grade below range is clamped", _normalise_grade({"grade": 0})[0] == 1)
try:
    _normalise_grade({"feedback": "no grade"})
    check("missing grade is rejected", False)
except ReviewGenerationError:
    check("missing grade is rejected", True)

check("mcq exact match scores good", grade_mcq("G3P", "G3P")[0] == 3)
check("mcq mismatch scores again", grade_mcq("ATP", "G3P")[0] == 1)
check("mcq mismatch reveals the answer", "G3P" in grade_mcq("ATP", "G3P")[1])
check("mcq tolerates surrounding space", grade_mcq(" G3P ", "G3P")[0] == 3)

# --- json extraction --------------------------------------------------
check("parses bare json", _extract_json('{"a": 1}')["a"] == 1)
check("parses fenced json", _extract_json('```json\n{"a": 2}\n```')["a"] == 2)
check("parses json with a preamble",
      _extract_json('Sure, here you go:\n{"a": 3}')["a"] == 3)
try:
    _extract_json("no json here")
    check("unparseable response is rejected", False)
except ReviewGenerationError:
    check("unparseable response is rejected", True)


# --- json repair, from responses that actually failed in production ----
_dropped_key = '{"scenes": [{"scene_3", "concepts": [{"name": "x"}]}]}'
check("repairs a dropped object key",
      _extract_json(_dropped_key)["scenes"][0]["scene_id"] == "scene_3")

check("repairs a trailing comma",
      _extract_json('{"items": [{"a": 1},]}')["items"][0]["a"] == 1)

_truncated = '{"items": [{"kind": "recall", "prompt": "Why?", "answer": "Because."}, {"kind": "mcq", "prom'
_recovered = _extract_json(_truncated)
check("recovers complete entries from a truncated response",
      len(_recovered["items"]) == 1 and _recovered["items"][0]["answer"] == "Because.")

check("repair does not corrupt already-valid json",
      _extract_json('{"scenes": [{"scene_id": "s1", "concepts": []}]}')["scenes"][0]["scene_id"] == "s1")


def test_no_failures():
    """Pytest entry point. The checks above run at import; this asserts them."""
    assert not failures, "; ".join(failures)


if __name__ == "__main__":
    print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED: {failures}")
    sys.exit(0 if not failures else 1)
