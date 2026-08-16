"""
Prompts for turning a finished lesson into concepts and review questions.

Both stages read the lesson's OWN content - the slide text and the spoken
narration that were actually shown to the student - rather than the original
one-line requirement. A question about something the lesson never covered is
worse than no question at all, because the student cannot tell whether they
forgot it or never saw it.
"""

CONCEPT_SYSTEM = """You extract the teachable ideas from a lesson.

For each scene you are given, list the concepts it teaches. A concept is a
single idea a student could know or not know - "photosynthesis converts light
energy to chemical energy", not "the slide about photosynthesis".

Rules:
- Name concepts as short noun phrases, 1-5 words. "Calvin cycle", "chain
  rule", "electron transport chain".
- Use the conventional name for the idea, not the lesson's phrasing. If the
  slide says "the light-catching stage", the concept is "light-dependent
  reactions". This is what lets the same idea taught in two different lessons
  be recognised as one concept.
- 1-3 concepts per scene. A scene that teaches five things is really a scene
  that teaches one thing plus context; pick the one it is actually about.
- Mark a concept "primary" when the scene teaches it, and not primary when
  the scene merely mentions it in passing.
- Also list prerequisite pairs where one concept in THIS lesson must be
  understood before another. Only within this lesson, and only where the
  dependency is real, not merely the order the scenes happen to be in.

Return ONLY JSON:
{
  "scenes": [
    {"scene_id": "scene_1", "concepts": [
      {"name": "photosynthesis", "primary": true,
       "description": "one sentence on what the student should end up knowing"}
    ]}
  ],
  "prerequisites": [
    {"before": "light-dependent reactions", "after": "Calvin cycle"}
  ]
}"""

CONCEPT_USER = """Lesson: {lesson_title}

Scenes:
{scenes_block}

Extract the concepts."""


ITEM_SYSTEM = """You write review questions that test whether a student still
remembers what a lesson taught.

These are for spaced repetition, so they are answered days or weeks later with
the lesson NOT in front of the student. Write accordingly.

Rules:
- Ask about the idea, not the lesson. The student answers this weeks later
  with nothing on screen, so the question must stand completely alone.
  Never write "this slide", "the diagram above", "in the video", "in the
  lesson", "discussed in the lesson", "as we saw" or "what we learned" -
  there is no we, and there is no lesson in front of them.
  "Why does a heavier cart accelerate less under the same force?" works.
  "What did the diagram on slide 3 show?" and "What is one application of
  integration discussed in the lesson?" are both unanswerable.
- Every question must be answerable from the lesson content given to you. Do
  not test anything the lesson did not cover.
- One idea per question. A question with "and" in the middle is two questions.
- The answer must be short enough to recall - a sentence or two, or a number.
  If the honest answer is three paragraphs, the question is too broad.
- Prefer questions that need the student to reconstruct or explain something
  over ones they can guess. "Why" and "what happens if" beat "what is called".
- For 'recall', give a rubric listing the points an answer must contain to
  count as correct. Be specific; these are used to mark real answers.
- For 'mcq', give exactly 4 options with one correct. The wrong options must
  be plausible - a student who half-remembers should be able to fall for one.
  Never use "all of the above" or "none of the above".

Return ONLY JSON. Every string must be on ONE line - no line breaks inside a
string value. Every object key must be present and quoted.

{
  "items": [
    {"kind": "recall", "prompt": "Why does a heavier cart accelerate less under the same push?", "answer": "Acceleration equals force divided by mass, so for a fixed force a greater mass gives a smaller acceleration.", "must_include": ["a = F/m relationship", "more mass means less acceleration"]},
    {"kind": "mcq", "prompt": "What does the Calvin cycle produce?", "answer": "G3P", "options": ["G3P", "Oxygen", "Chlorophyll", "ATP only"]}
  ]
}"""

ITEM_USER = """Lesson: {lesson_title}
Scene: {scene_title}
Concepts this scene teaches: {concepts}

What the slide showed:
{slide_text}

What the narrator said:
{narration}

Write {count} review questions on this scene. Mix 'recall' and 'mcq'."""


GRADE_SYSTEM = """You mark a student's answer to a review question.

You are given the question, the correct answer, the points the answer must
contain, and what the student wrote. Judge whether they recalled the idea -
not whether they phrased it the way the model would.

The scale, which decides when they see this question again:
  1 = again - wrong, or could not recall it
  2 = hard  - correct as far as it goes, but thin, hedged or incomplete
  3 = good  - correct, with the key points present
  4 = easy  - correct, complete, and clearly well understood

## The line between 1 and 2 is the one that matters

2 and above count as REMEMBERING, and push the question days into the
future. 1 brings it straight back. So:

**Grades 2, 3 and 4 all require the answer to be CORRECT.** 2 is for a
correct answer that is thin. It is never for an incorrect answer that is
well written.

**Give 1 whenever the answer contains something false** - a wrong
mechanism, a wrong direction, the wrong structure, anything that
contradicts the correct answer - no matter how confidently it is stated
or how much of the right vocabulary it uses.

Confidently wrong is the single most important case to catch. A student
who says "heavier things have more gravity pulling them forward so they
go faster" has used the words mass, gravity and speed and sounds sure of
themselves, and is completely wrong. That is a 1. They do not know they
are wrong, so nothing except being asked again will fix it - and marking
it 2 hides the question for days.

## Otherwise, mark generously

For answers that ARE correct, judge the idea and not the phrasing. A
student who says "the heavier one speeds up slower because mass fights
the force" has understood F=ma and gets a 3, symbols or no symbols.

A student who restates the question without answering it, or writes
something true but irrelevant, has not recalled anything: 1.

Return ONLY JSON:
{"grade": 3, "feedback": "one or two sentences, addressed to the student,
saying what they got and what they missed"}"""

GRADE_USER = """Question: {prompt}

Correct answer: {answer}
Points required: {must_include}

The student wrote:
{response}

Mark it."""
