"""
Celery task for real video generation.

Replaces video_service.py's `_run_maestro_generation` (external project that
doesn't exist in this environment) and `_run_simulated_generation` (fake
progress bar, dead-end video path) with an actual pipeline:

  1. LLM generates a scene script + Manim scene code (reuses
     video_service.py's EnhancedVideoGenerator/SmartManimClient unchanged -
     these are pure LLM-prompt generators with no external dependency)
  2. `manim` CLI renders the scene to an .mp4
  3. `edge-tts` CLI synthesizes narration audio from the script (free, no
     API key - already a working dependency, see coqui_tts_service.py's
     fallback path for the same CLI-invocation pattern)
  4. `ffmpeg` muxes narration onto the rendered video

Progress is written to the VideoJob DB row (see models/video_job.py),
not an in-memory dict, so it survives worker restarts and is visible from
any API process.
"""
import asyncio
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from celery.exceptions import Retry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from config import settings
from models import VideoJob, VideoJobStatus, ProviderType, LLMProviderConfig
from video_service import get_enhanced_generator, reset_video_clients
from llm_service import llm_service

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

OUTPUT_DIR = Path(__file__).parent.parent / "generated_videos"
OUTPUT_DIR.mkdir(exist_ok=True)

NARRATION_VOICE = "en-US-ChristopherNeural"  # matches coqui_tts_service.py's "socrates" voice
MANIM_QUALITY_FLAGS = {"low": "-ql", "medium": "-qm", "high": "-qh"}


def _update_job(db, job: VideoJob, **fields) -> None:
    for key, value in fields.items():
        setattr(job, key, value)
    db.commit()


def _configure_llm_for_user(db, user_id: int) -> None:
    """Point this worker process's llm_service singleton at the requesting
    user's configured provider/key before generating the script.

    Celery runs each task in its own process (prefork pool), and that
    process's llm_service starts out on the bare DEFAULT_LLM_PROVIDER/MODEL
    with no key attached (api_key_encrypted is only ever resolved per-request
    in the API process - it never reaches the worker). Without this,
    EnhancedVideoGenerator._initialize() always sees "no key" and silently
    downgrades to its one-scene, no-narration local-mode placeholder script -
    which is exactly the "video content isn't proper" symptom this fixes.
    """
    provider = ProviderType(settings.DEFAULT_LLM_PROVIDER)
    model = settings.DEFAULT_LLM_MODEL
    encrypted_key = None

    if provider not in (ProviderType.OLLAMA, ProviderType.LMSTUDIO, ProviderType.LOCALAI, ProviderType.TEXTGENWEBUI):
        provider_config = (
            db.query(LLMProviderConfig)
            .filter(
                LLMProviderConfig.user_id == user_id,
                LLMProviderConfig.provider == provider,
                LLMProviderConfig.is_active == True,
            )
            .order_by(LLMProviderConfig.is_default.desc(), LLMProviderConfig.updated_at.desc())
            .first()
        )
        encrypted_key = provider_config.api_key_encrypted if provider_config else None

    llm_service.set_provider(model=model, provider=provider.value, api_key_encrypted=encrypted_key)
    # Force EnhancedVideoGenerator/SmartVideoClient/SmartManimClient to
    # re-read llm_service.current_config instead of reusing whatever
    # _use_api they cached the first time this worker process ran a job.
    reset_video_clients()


def _safe_filename(text: str) -> str:
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in text)
    return safe.replace(" ", "_")[:50]


def _build_narration_text(script: dict) -> str:
    """Concatenate per-scene narration. Local-mode fallback scripts have no
    narration field (see EnhancedVideoGenerator.generate_script's fallback
    when no cloud API key is configured), in which case this returns ''
    and the caller skips audio synthesis - video-only is a legitimate
    degraded output, not a failure."""
    scenes = script.get("scenes") or []
    parts = [scene.get("narration", "") for scene in scenes if scene.get("narration")]
    return " ".join(parts).strip()


def _synthesize_narration(text: str, output_path: Path) -> bool:
    """Synthesize narration via edge-tts. Invoked as `python -m edge_tts`
    (module form) rather than the `edge-tts` console script - the console
    script only resolves if the worker's PATH happens to include the venv's
    bin directory, which isn't guaranteed depending on how the worker was
    launched (confirmed missing when the worker is started by invoking
    `.venv/bin/celery` directly without activating the venv first).
    `sys.executable` always correctly identifies this same interpreter's
    environment regardless of PATH."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "edge_tts",
             "--voice", NARRATION_VOICE, "--text", text, "--write-media", str(output_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return True
        logger.warning(f"edge-tts narration synthesis failed: {result.stderr[:500]}")
        return False
    except Exception as e:
        logger.warning(f"edge-tts narration synthesis error: {e}")
        return False


def _find_rendered_video(media_dir: Path, output_name: str) -> Optional[Path]:
    matches = list(media_dir.rglob(output_name))
    if matches:
        return matches[0]
    # Fall back to any mp4 manim produced, in case -o didn't apply cleanly
    matches = list(media_dir.rglob("*.mp4"))
    return matches[0] if matches else None


def _mux_audio_video(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Overlay narration onto the rendered video. `-shortest` truncates to
    whichever track is shorter rather than trying to time-stretch either -
    a simple, robust default until per-scene audio/video timing sync is
    built (a real future improvement, not attempted here)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mux failed: {result.stderr[-1000:]}")


@celery_app.task(bind=True, max_retries=1, default_retry_delay=30)
def render_video_task(self, video_job_id: int) -> dict:
    logger.info(f"Starting video render: video_job_id={video_job_id}")

    db = SessionLocal()
    job: Optional[VideoJob] = None
    work_dir: Optional[Path] = None

    try:
        job = db.query(VideoJob).filter(VideoJob.id == video_job_id).first()
        if not job:
            logger.error(f"VideoJob not found: {video_job_id}")
            return {"status": "error", "message": "Job not found"}

        _configure_llm_for_user(db, job.user_id)

        work_dir = Path(tempfile.mkdtemp(prefix=f"video_{job.id}_"))
        media_dir = work_dir / "media"

        _update_job(db, job, status=VideoJobStatus.RENDERING, stage="content",
                    progress_percent=5, message="Generating script...")

        # Phase 1: script + Manim scene code (LLM-prompt generation, reused as-is)
        generator = get_enhanced_generator()
        result = asyncio.run(generator.generate_enhanced_video(job.topic, job.context))
        script = result["script"]
        manim_code = result["manim_code"]

        _update_job(db, job, script=script, stage="content", progress_percent=25,
                    message="Script ready, rendering animation...")

        # Phase 2: render with the manim CLI
        scene_file = work_dir / "scene.py"
        scene_file.write_text(manim_code)

        quality_flag = MANIM_QUALITY_FLAGS.get(job.quality, "-qh")
        output_name = "scene_video.mp4"
        # Module form (see _synthesize_narration's docstring for why: PATH
        # isn't a reliable way to find this venv's console scripts from
        # inside a Celery worker process).
        manim_cmd = [
            sys.executable, "-m", "manim", quality_flag, "--disable_caching",
            "--media_dir", str(media_dir),
            "-o", output_name,
            str(scene_file), "ManimScene",
        ]
        proc = subprocess.run(manim_cmd, cwd=work_dir, capture_output=True, text=True, timeout=1500)
        if proc.returncode != 0:
            # The script/Manim code are freshly LLM-generated (non-deterministic)
            # on every attempt, so a render failure here is usually a one-off bad
            # generation rather than a systemic problem - retry once with a fresh
            # generation before giving up, rather than always failing the job on
            # the LLM's first mistake.
            error_detail = proc.stderr[-2000:]
            logger.warning(f"Manim render failed for job {video_job_id}, will retry: {error_detail[-500:]}")
            raise self.retry(exc=RuntimeError(f"Manim render failed:\n{error_detail}"), countdown=5)

        rendered_video = _find_rendered_video(media_dir, output_name)
        if not rendered_video:
            raise self.retry(exc=RuntimeError("Manim did not produce an output video"), countdown=5)

        _update_job(db, job, stage="narration", progress_percent=60, message="Generating narration audio...")

        # Phase 3: narration (best-effort - see _build_narration_text)
        narration_text = _build_narration_text(script)
        audio_path = work_dir / "narration.mp3"
        has_audio = bool(narration_text) and _synthesize_narration(narration_text, audio_path)

        _update_job(db, job, stage="merge", progress_percent=85, message="Merging audio and video...")

        # Phase 4: mux (or just copy through if there's no narration to add)
        final_path = OUTPUT_DIR / f"{job.id}_{_safe_filename(job.topic)}.mp4"
        if has_audio:
            _mux_audio_video(rendered_video, audio_path, final_path)
        else:
            shutil.copy(rendered_video, final_path)

        _update_job(
            db, job,
            status=VideoJobStatus.COMPLETED,
            stage="completed",
            progress_percent=100,
            message="Video generated successfully!",
            video_path=f"/generated_videos/{final_path.name}",
        )
        logger.info(f"Video render complete: video_job_id={video_job_id} -> {final_path.name}")
        return {"status": "success", "video_job_id": job.id, "video_path": job.video_path}

    except Retry:
        # Celery's own retry control-flow exception - must propagate
        # untouched, not be treated as a job failure.
        raise

    except Exception as e:
        logger.error(f"Video generation failed for job {video_job_id}: {e}")
        db.rollback()
        try:
            if job is None:
                job = db.query(VideoJob).filter(VideoJob.id == video_job_id).first()
            if job:
                _update_job(
                    db, job,
                    status=VideoJobStatus.FAILED,
                    stage="error",
                    error_message=str(e)[:2000],
                    message="Video generation failed",
                )
        except Exception:
            pass
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
