"""
Celery task: generate a full interactive lesson.

Pipeline (mirrors OpenMAIC's, reduced to what we can actually serve):

    outline  ->  per-scene content  ->  per-scene actions  ->  persist

`slide` scenes are authored by the LLM as @maic/dsl JSON. `video` scenes are
handed to the EXISTING Manim pipeline (tasks/video_tasks.py) and the result is
embedded as a PPTVideoElement - which is why this needed no DSL changes.

Runs synchronously inside one task rather than fanning scenes out to separate
tasks: the whole lesson is one unit of work for the user, partial results are
not useful, and progress reporting stays simple. If lessons grow past ~10
scenes this is the obvious thing to parallelise.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from config import settings
from models import Lesson, LessonStatus
from services.lesson.generator import (
    LessonGenerationError,
    build_video_slide,
    generate_actions,
    generate_outline,
    generate_slide,
)

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _update(db, lesson: Lesson, **fields) -> None:
    for k, v in fields.items():
        setattr(lesson, k, v)
    db.commit()


def _make_llm_callable(user_id: int):
    """Bind an async LLM callable to this user's configured provider.

    Same resolution rule as video_tasks._configure_llm_for_user: the user's
    default/most-recent active provider, whichever provider that is. Raises if
    they have none - there is no app-wide fallback by design.
    """
    from models import LLMProviderConfig, ProviderType, PROVIDER_INFO
    from services.litellm_service import get_litellm_service

    db = SessionLocal()
    try:
        cfg = (
            db.query(LLMProviderConfig)
            .filter(LLMProviderConfig.user_id == user_id, LLMProviderConfig.is_active == True)
            .order_by(LLMProviderConfig.is_default.desc(), LLMProviderConfig.updated_at.desc())
            .first()
        )
        if not cfg:
            raise LessonGenerationError(
                f"No active LLM provider configured for user {user_id} - "
                "add a provider and API key in AI Settings."
            )
        provider = cfg.provider if isinstance(cfg.provider, ProviderType) else ProviderType(cfg.provider)
        model = (cfg.extra_settings or {}).get("default_model") or next(
            iter(PROVIDER_INFO.get(provider, {}).get("models", [])), None
        )
        if not model:
            raise LessonGenerationError(f"No model configured for the {provider.value} provider.")
        key, base_url = cfg.api_key_encrypted, cfg.base_url
    finally:
        db.close()

    svc = get_litellm_service()

    async def call(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        return await svc.generate(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            api_key_encrypted=key,
            base_url=base_url,
            max_tokens=max_tokens,
            timeout=120,
        )

    return call


def _render_video_scene(user_id: int, outline: Dict[str, Any], session_id: Optional[str]) -> Optional[Dict[str, str]]:
    """Run a video scene through the existing Manim pipeline, synchronously.

    Calls render_video_task's body directly instead of dispatching another
    Celery task and polling for it: we are already inside a worker, and
    enqueueing from here would deadlock if the pool has a single slot.
    Returns None on failure so the lesson can degrade to a slide.
    """
    from services.video_job_service import start_video_job  # noqa: F401  (kept for parity)
    from models import VideoJob, VideoJobStatus
    from tasks.video_tasks import render_video_task

    db = SessionLocal()
    try:
        job = VideoJob(
            user_id=user_id,
            topic=outline["title"],
            session_id=session_id,
            quality="medium",
            # A lesson's animation is the centrepiece of its scene, not an
            # inline aside like the chat-triggered clips - so it gets real
            # room to develop an idea. 90s buys roughly 4-5 animated beats
            # instead of a title card plus one.
            duration_seconds=90,
            auto_generated=True,
            context={
                "topic_title": outline["title"],
                "key_concepts": outline.get("keyPoints", []),
                "duration_suggestion": 90,
                "scene_description": outline.get("description", ""),
            },
        )
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    try:
        result = render_video_task(job_id)  # direct call, not .delay()
    except Exception as e:
        logger.warning("video scene render raised for '%s': %s", outline["title"], e)
        return None

    if not isinstance(result, dict) or result.get("status") != "success":
        logger.warning("video scene render failed for '%s': %s", outline["title"],
                       (result or {}).get("message", "unknown"))
        return None

    video_path = result.get("video_path")
    if not video_path:
        return None
    # tasks/video_tasks.py writes a sibling .jpg poster next to every render.
    return {"src": video_path, "poster": video_path.rsplit(".", 1)[0] + ".jpg"}


@celery_app.task(bind=True, max_retries=0)
def generate_lesson_task(self, lesson_id: int) -> dict:
    logger.info(f"Starting lesson generation: lesson_id={lesson_id}")
    db = SessionLocal()
    lesson: Optional[Lesson] = None

    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {"status": "error", "message": "Lesson not found"}

        _update(db, lesson, status=LessonStatus.GENERATING, stage="outline",
                progress_percent=5, message="Designing the lesson...")

        llm = _make_llm_callable(lesson.user_id)

        # ---- Stage 1: outline
        # What this learner has already proved they know, so the outline can
        # skip it and spend the scenes on what they have not. Empty for a
        # new student, which reads as an ordinary request.
        from services.review.mastery import mastery_context_sync
        mastery_context = mastery_context_sync(db, lesson.user_id, lesson.requirement)
        if mastery_context:
            logger.info(f"Lesson {lesson_id} personalised: {mastery_context[:160]}")
        outline = asyncio.run(
            generate_outline(llm, lesson.requirement, context=mastery_context)
        )
        scene_outlines: List[Dict[str, Any]] = outline["outlines"]
        _update(db, lesson, title=outline["title"], summary=outline["summary"],
                outline=outline, stage="scenes", progress_percent=15,
                message=f"Building {len(scene_outlines)} scenes...")

        # ---- Stage 2+3: per scene content, then choreography
        scenes: List[Dict[str, Any]] = []
        total = len(scene_outlines)
        for idx, so in enumerate(scene_outlines):
            base = 15 + int(75 * idx / max(total, 1))
            _update(db, lesson, progress_percent=base,
                    message=f"Scene {idx + 1} of {total}: {so['title']}")

            scene_type = so["type"]
            slide: Optional[Dict[str, Any]] = None

            if scene_type == "video":
                media = _render_video_scene(lesson.user_id, so, lesson.session_id)
                if media:
                    slide = build_video_slide(media["src"], media.get("poster"), so["title"])
                else:
                    # Degrade rather than fail the lesson: the learner gets a
                    # slide covering the same key points instead of a gap.
                    logger.info("video scene '%s' degraded to slide", so["title"])
                    scene_type = "slide"

            if slide is None:
                try:
                    slide = asyncio.run(generate_slide(llm, lesson.title or "", so))
                except LessonGenerationError as e:
                    logger.warning("slide generation failed for '%s': %s", so["title"], e)
                    continue

            actions = asyncio.run(generate_actions(llm, lesson.title or "", so, slide))
            scenes.append({
                "id": so["id"],
                "type": scene_type,
                "title": so["title"],
                "description": so["description"],
                "order": so["order"],
                "slide": slide,
                "actions": actions,
            })
            _update(db, lesson, scenes=scenes)  # incremental: player can preview

        if not scenes:
            raise LessonGenerationError("no scenes could be generated")

        _update(db, lesson, status=LessonStatus.COMPLETED, stage="completed",
                progress_percent=100, message="Lesson ready", scenes=scenes)
        logger.info(f"Lesson complete: lesson_id={lesson_id} ({len(scenes)} scenes)")

        # Tag concepts and write review questions on a separate queue. The
        # lesson is already usable, so this must never delay it - and a
        # failure here must never fail a lesson that generated fine.
        try:
            from tasks.review_tasks import process_lesson_review_task
            process_lesson_review_task.delay(lesson_id)
        except Exception as exc:
            logger.warning(f"Could not queue review processing for {lesson_id}: {exc}")

        return {"status": "success", "lesson_id": lesson_id, "scene_count": len(scenes)}

    except Exception as e:
        logger.error(f"Lesson generation failed for {lesson_id}: {e}")
        try:
            db.rollback()
            if lesson is None:
                lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if lesson:
                _update(db, lesson, status=LessonStatus.FAILED, stage="error",
                        error_message=str(e)[:2000], message="Lesson generation failed")
        except Exception:
            logger.error(f"Could not persist FAILED status for lesson {lesson_id}")
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
