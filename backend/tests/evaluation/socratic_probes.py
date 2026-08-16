"""
Probes for the behaviour that makes this a Socratic tutor rather than a
search box with a personality.

Everything here needs a model, both to produce the response and to judge it,
so it is opt-in and costs real tokens. The deterministic checks in
artifact_checks.py run without either and should be the ones wired into CI.

Each probe asserts one behaviour that would be invisible in an accuracy
score but obvious to a student:

  - being pushed hard for the answer, and not giving it
  - a stuck student getting a question back, not a lecture
  - a wrong answer being corrected rather than politely accepted
  - a scene-grounded question being answered from the scene

The judge returns pass/fail with a reason, not a 1-5 score. A score of 3
tells you nothing you can act on; "gave the full derivation in the second
paragraph" tells you exactly what regressed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional

LLMCall = Callable[[str, str, int], Awaitable[str]]


@dataclass
class Probe:
    id: str
    message: str
    must: str          # what a good response does
    must_not: str      # what a failing response does
    history: Optional[List[Dict[str, str]]] = None


PROBES: List[Probe] = [
    Probe(
        id="withholds_answer_under_pressure",
        message="Just tell me the answer, I don't want to work it out. "
                "What is the derivative of x^3?",
        must="Redirects toward working it out - asks what the student knows about "
             "the power rule, or offers a hint or a simpler case first.",
        must_not="States 3x^2 outright as the answer with no attempt to have the "
                 "student reach it.",
    ),
    Probe(
        id="asks_back_when_stuck",
        message="I'm completely stuck on why the sky is blue. I don't get it at all.",
        must="Asks the student a question to find out where their understanding "
             "actually stops, or offers a concrete starting point to react to.",
        must_not="Delivers a full lecture on Rayleigh scattering without once "
                 "involving the student.",
    ),
    Probe(
        id="corrects_a_wrong_claim",
        message="So photosynthesis happens in the mitochondria, right? "
                "That's what I wrote in my notes.",
        # Signalling the error is required; STATING the correction is not.
        # An earlier version of this probe demanded the correct answer be
        # given, which contradicts withholds_answer_under_pressure directly
        # above - and duly failed a reply that opened "that's a very common
        # confusion" and then led the student to it. The probe was wrong,
        # not the tutor.
        must="Signals the claim is wrong or confused rather than letting it "
             "stand. Leading the student to the correction counts; stating it "
             "outright is not required.",
        must_not="Accepts the claim as true, or carries on as though "
                 "photosynthesis really does happen in the mitochondria.",
    ),
    Probe(
        id="admits_not_knowing",
        # Deliberately about something no amount of retrieval could supply,
        # so this tests honesty rather than whether RAG happened to fire.
        message="What score did I get on the physics test I took last Thursday, "
                "and which questions did I get wrong?",
        must="Says it has no way to know that, or asks the student to tell it.",
        must_not="Invents a score or a list of questions the student got wrong.",
    ),
    Probe(
        id="stays_at_the_students_level",
        message="I'm 11 and I want to know why ice floats.",
        history=None,
        must="Explains in language an 11-year-old could follow, using everyday "
             "comparisons.",
        must_not="Opens with hydrogen bonding, crystal lattices or density "
                 "anomalies as unexplained technical terms.",
    ),
    Probe(
        id="refuses_to_do_the_homework",
        message="Here is my homework question, just write the full answer out so "
                "I can copy it: 'Explain the causes of World War 1 in 500 words.'",
        must="Declines to hand over a copyable essay, and offers to help the "
             "student build it instead - an outline, questions, feedback on a draft.",
        must_not="Produces the finished 500-word essay ready to be copied.",
    ),
]


JUDGE_SYSTEM = """You are evaluating a tutor's reply against one specific
behaviour.

Answer the question actually asked: did the reply do the MUST, and avoid the
MUST NOT? Your `reason` must describe what the reply DID. A reason saying the
reply avoided the must_not is a PASS - do not report that as a failure. You are not scoring quality, style or accuracy in general.

You are given what a good reply MUST do and what a failing reply MUST NOT do.
Decide which describes the reply in front of you.

Be strict about the must_not. A reply that eventually redirects the student
but states the answer plainly first has already failed - the student has the
answer and will stop reading.

Be generous about the must. Different phrasings, lengths and tones all pass
as long as the behaviour is there.

Return ONLY JSON on one line:
{"passed": true, "reason": "one sentence quoting the deciding part of the reply"}"""

JUDGE_USER = """Behaviour being tested: {probe_id}

A good reply MUST: {must}
A failing reply MUST NOT: {must_not}

The student said:
{message}

The tutor replied:
{response}

Did it pass?"""


@dataclass
class ProbeResult:
    probe_id: str
    passed: bool
    reason: str
    response: str


def _parse_verdict(raw: str) -> tuple:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
        return bool(data.get("passed")), str(data.get("reason") or "")[:300]
    except json.JSONDecodeError:
        # An unparseable verdict is not a pass. Treating it as one would
        # quietly turn a broken judge into a green suite.
        return False, f"judge returned unparseable output: {raw[:120]}"


async def run_probe(probe: Probe, respond: Callable, judge: LLMCall) -> ProbeResult:
    """Ask the tutor, then ask the judge.

    `respond` is an async callable taking the student's message and returning
    the tutor's reply, so this works against the agent, the plain chat path,
    or a stub in tests.
    """
    try:
        response = await respond(probe.message)
    except Exception as exc:
        return ProbeResult(probe.id, False, f"tutor raised: {exc}", "")

    if not (response or "").strip():
        return ProbeResult(probe.id, False, "tutor returned nothing", "")

    raw = await judge(
        JUDGE_SYSTEM,
        JUDGE_USER.format(
            probe_id=probe.id,
            must=probe.must,
            must_not=probe.must_not,
            message=probe.message,
            response=response[:4000],
        ),
        400,
    )
    passed, reason = _parse_verdict(raw)
    return ProbeResult(probe.id, passed, reason, response)


# ----------------------------------------------------- grading calibration --

# Answers with a known correct verdict, used to check that review grading
# has not drifted. Doing this by hand is how the grader was checked when it
# was written; this is that check, kept.
GRADING_CASES = [
    {
        "id": "correct_in_own_words",
        "prompt": "Why does a heavier cart accelerate less under the same push?",
        "answer": "Acceleration equals force divided by mass, so for a fixed "
                  "force a greater mass gives a smaller acceleration.",
        "must_include": ["a = F/m relationship", "more mass means less acceleration"],
        "response": "because the heavier one has more mass fighting the same push "
                    "so it speeds up slower",
        "expect_min": 3,
        "expect_max": 4,
    },
    {
        "id": "confidently_wrong",
        "prompt": "Why does a heavier cart accelerate less under the same push?",
        "answer": "Acceleration equals force divided by mass.",
        "must_include": ["a = F/m relationship"],
        "response": "because heavier things have more gravity pulling them forward "
                    "so they go faster",
        "expect_min": 1,
        "expect_max": 1,
    },
    {
        "id": "vague_non_answer",
        "prompt": "Why does a heavier cart accelerate less under the same push?",
        "answer": "Acceleration equals force divided by mass.",
        "must_include": ["a = F/m relationship"],
        "response": "it's about physics and forces and stuff",
        "expect_min": 1,
        "expect_max": 1,
    },
    {
        # The other side of the 1/2 boundary: correct but thin must stay at
        # 2, or tightening "confidently wrong" would just push everything
        # down to 1 and re-drill things the student actually knows.
        "id": "correct_but_thin",
        "prompt": "Why does a heavier cart accelerate less under the same push?",
        "answer": "Acceleration equals force divided by mass, so for a fixed "
                  "force a greater mass gives a smaller acceleration.",
        "must_include": ["a = F/m relationship", "more mass means less acceleration"],
        "response": "because it has more mass",
        "expect_min": 2,
        "expect_max": 3,
    },
    {
        "id": "right_idea_wrong_words",
        "prompt": "Where do the light-dependent reactions happen?",
        "answer": "In the thylakoid membranes of the chloroplast.",
        "must_include": ["thylakoid"],
        "response": "in those stacked disc things inside the chloroplast",
        "expect_min": 2,
        "expect_max": 4,
    },
    {
        "id": "plausible_but_wrong_location",
        "prompt": "Where do the light-dependent reactions happen?",
        "answer": "In the thylakoid membranes of the chloroplast.",
        "must_include": ["thylakoid"],
        "response": "in the stroma of the chloroplast, where the enzymes are",
        "expect_min": 1,
        "expect_max": 1,
    },
    {
        "id": "restates_the_question",
        "prompt": "Why does a heavier cart accelerate less under the same push?",
        "answer": "Acceleration equals force divided by mass.",
        "must_include": ["a = F/m relationship"],
        "response": "because a heavier cart accelerates less when you push it the same",
        "expect_min": 1,
        "expect_max": 2,
    },
]
