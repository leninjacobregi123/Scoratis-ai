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
from datetime import datetime, timezone
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


def _cached_render(db, user_id: int, title: str) -> Optional[Dict[str, str]]:
    """A previous render of this same idea, if there is one.

    Matched on the title embedding, then confirmed by a shared content word.
    Both are needed: the embedding alone puts "Four-Stroke Engine Cycle
    Animation" and "Calvin Cycle Animation" at 0.50 on the strength of
    "cycle" and "animation", and generic scene vocabulary should never be
    what makes two scenes look alike.

    Returns None on any doubt. A miss costs one re-render, which is what
    used to happen every time anyway; a false hit puts the wrong animation
    in front of a student.
    """
    from pathlib import Path
    from models import RenderedScene, SCENE_REUSE_THRESHOLD, meaningful_tokens
    from services.review.mastery import _cosine
    from services.review.extractor import slug_for

    tokens = meaningful_tokens(title)
    if not tokens:
        return None

    try:
        from services.embedding_service import get_embedding_service
        service = get_embedding_service()
        vector = service.embed_text(title) if service else None
    except Exception as exc:
        logger.warning(f"Scene-reuse lookup unavailable: {exc}")
        return None
    if vector is None:
        return None

    candidates = (
        db.query(RenderedScene)
        .filter(RenderedScene.user_id == user_id, RenderedScene.embedding.isnot(None))
        .order_by(RenderedScene.embedding.cosine_distance(vector))
        .limit(5)
        .all()
    )

    root = Path(__file__).parent.parent
    for cached in candidates:
        similarity = _cosine(vector, list(cached.embedding))
        if similarity < SCENE_REUSE_THRESHOLD:
            break  # ordered by distance, so nothing further can qualify
        if not (tokens & meaningful_tokens(cached.title)):
            continue
        # The row can outlive the file - renders get cleaned up, disks get
        # restored. Serving a path to a missing mp4 would give the student a
        # broken player rather than a lesson.
        on_disk = root / cached.video_path.lstrip("/")
        if not on_disk.exists():
            logger.info(f"Cached render {cached.id} missing from disk, re-rendering")
            continue

        cached.use_count = (cached.use_count or 1) + 1
        cached.last_used_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            f"Reusing render {cached.id} ({cached.title!r}, similarity "
            f"{similarity:.3f}) instead of rendering {title!r}"
        )
        return {"src": cached.video_path, "poster": cached.poster_path or ""}

    return None


def _remember_render(
    db, user_id: int, title: str, result: Dict[str, str], lesson_id: Optional[int]
) -> None:
    """Record a finished render so the next lesson on this idea can reuse it."""
    from models import RenderedScene
    from services.review.extractor import slug_for

    try:
        from services.embedding_service import get_embedding_service
        service = get_embedding_service()
        vector = service.embed_text(title) if service else None
    except Exception:
        vector = None

    try:
        db.add(RenderedScene(
            user_id=user_id,
            title=title[:500],
            slug=slug_for(title),
            embedding=vector,
            video_path=result["src"],
            poster_path=result.get("poster"),
            source_lesson_id=lesson_id,
            last_used_at=datetime.now(timezone.utc),
        ))
        db.commit()
    except Exception as exc:
        # Never fail a lesson over a cache write - the render itself
        # succeeded and the scene is already usable.
        logger.warning(f"Could not cache render for {title!r}: {exc}")
        db.rollback()


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
                # A previous lesson may already have animated this idea.
                # Rendering is the most expensive step in the pipeline, so
                # check before paying for it again.
                media = _cached_render(db, lesson.user_id, so["title"])
                if media:
                    _update(db, lesson, message=f"Reusing animation: {so['title'][:40]}")
                else:
                    media = _render_video_scene(lesson.user_id, so, lesson.session_id)
                    if media:
                        _remember_render(db, lesson.user_id, so["title"], media, lesson_id)
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
