"""
Run the evaluation suite.

    python -m tests.evaluation.run_eval              # deterministic only, free
    python -m tests.evaluation.run_eval --live       # + tutor and grading probes
    python -m tests.evaluation.run_eval --no-video   # skip ffmpeg sampling

The default is the one to wire into CI: no model, no API key, no cost, and
it catches the class of bug that has actually shipped here - text off the
canvas, blank shapes, dead video tails, unanswerable questions, a corrupted
concept graph.

--live additionally asks the tutor six questions and has a model judge
whether it behaved like a tutor, then checks that review grading still
separates a good answer from a wrong one. That costs tokens and needs a
configured provider, so it is opt-in.

Exit code is 1 if there are errors, 0 otherwise. Warnings never fail the
run: they are things to look at, not things that are broken.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.evaluation.artifact_checks import (  # noqa: E402
    CheckReport, check_review_items, check_lessons, check_renders, check_concepts,
    format_report,
)
from tests.evaluation.socratic_probes import (  # noqa: E402
    PROBES, GRADING_CASES, run_probe,
)


def _db():
    from tasks.lesson_tasks import SessionLocal
    return SessionLocal()


def run_deterministic(check_video: bool = True) -> CheckReport:
    from models import ReviewItem, Lesson, LessonStatus, Concept

    report = CheckReport()
    db = _db()
    try:
        check_review_items(
            db.query(ReviewItem).filter(ReviewItem.retired_at.is_(None)).all(), report
        )
        check_lessons(
            db.query(Lesson).filter(Lesson.status == LessonStatus.COMPLETED).all(), report
        )
        check_concepts(db.query(Concept).all(), report)

        if check_video:
            root = Path(__file__).resolve().parents[2]
            videos = sorted((root / "generated_videos").glob("*.mp4"))
            check_renders(videos, report)
    finally:
        db.close()
    return report


async def run_live(repeat: int = 3) -> int:
    """Tutor behaviour and grading calibration. Returns the failure count."""
    from tasks.lesson_tasks import SessionLocal, _make_llm_callable
    from models import User
    from services.review.extractor import grade_response

    db = SessionLocal()
    try:
        user = db.query(User).order_by(User.id).first()
        if not user:
            print("live: no users, skipping")
            return 0
        try:
            llm = _make_llm_callable(user.id)
        except Exception as exc:
            print(f"live: no usable provider ({exc}); skipping")
            return 0
    finally:
        db.close()

    from prompts import get_system_prompt
    from api.routes.chat import strip_internal_reasoning

    async def respond(message: str) -> str:
        # Judge what the STUDENT sees. The model wraps its planning in a
        # <pedagogical_plan> block that the chat route strips before
        # display, and judging that block instead of the reply measures
        # text nobody reads - it made the tutor look like it was ignoring
        # a misconception it had explicitly planned to correct.
        raw = await llm(get_system_prompt(), message, 1200)
        return strip_internal_reasoning(raw)

    failures = 0

    print(f"\nTutor behaviour  (best of {repeat})")
    print("-" * 70)
    for probe in PROBES:
        # Run each probe several times and take the majority. Both the
        # tutor and the judge are sampled, and a single flaky verdict
        # otherwise reports a defect that is not there - observed directly:
        # one run failed refuses_to_do_the_homework while its own reason
        # said the essay had not been provided.
        results = [await run_probe(probe, respond, llm) for _ in range(repeat)]
        passes = sum(1 for r in results if r.passed)
        passed = passes * 2 > repeat
        if not passed:
            failures += 1
        mark = "pass" if passed else "FAIL"
        print(f"  {mark}  {probe.id}  ({passes}/{repeat} passed)")
        if not passed:
            worst = next(r for r in results if not r.passed)
            print(f"        {worst.reason}")

    print("\nReview grading calibration")
    print("-" * 70)
    for case in GRADING_CASES:
        try:
            grade, _ = await grade_response(
                llm, case["prompt"], case["answer"],
                case["must_include"], case["response"],
            )
        except Exception as exc:
            print(f"  FAIL  {case['id']}: grading raised {exc}")
            failures += 1
            continue

        ok = case["expect_min"] <= grade <= case["expect_max"]
        if not ok:
            failures += 1
        mark = "pass" if ok else "FAIL"
        print(f"  {mark}  {case['id']}: graded {grade} "
              f"(expected {case['expect_min']}-{case['expect_max']})")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Scoratis evaluation suite")
    parser.add_argument("--live", action="store_true",
                        help="also run tutor and grading probes (needs a provider)")
    parser.add_argument("--no-video", action="store_true",
                        help="skip ffmpeg sampling of rendered videos")
    parser.add_argument("--repeat", type=int, default=3,
                        help="live probe runs per behaviour; majority decides")
    args = parser.parse_args()

    print("=" * 70)
    print("Scoratis evaluation")
    print("=" * 70)

    report = run_deterministic(check_video=not args.no_video)
    print()
    print(format_report("Artifacts", report))

    failures = len(report.errors)

    if args.live:
        failures += asyncio.run(run_live(repeat=args.repeat))

    print()
    print("=" * 70)
    if failures:
        print(f"FAILED: {failures} error(s)")
    else:
        print(f"PASSED ({report.checked} artifacts checked, "
              f"{len(report.warnings)} warning(s))")
    print("=" * 70)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
