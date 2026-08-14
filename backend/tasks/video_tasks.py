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
from typing import List, Optional

from celery.exceptions import Retry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from config import settings
from models import VideoJob, VideoJobStatus, ProviderType, PROVIDER_INFO, LLMProviderConfig
from video_service import get_enhanced_generator, reset_video_clients
from llm_service import llm_service

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
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
    process's llm_service starts out unconfigured with no key attached
    (api_key_encrypted is only ever resolved per-request in the API process -
    it never reaches the worker). Without this, EnhancedVideoGenerator.
    _initialize() always sees "no key" and silently downgrades to its
    one-scene, no-narration local-mode placeholder script - which is exactly
    the "video content isn't proper" symptom this fixes.

    Mirrors chat.py's _resolve_llm_config: use the user's own default/most-
    recent active provider config, for WHICHEVER provider they actually
    configured - not a single hardcoded provider. There is no app-wide
    default provider to fall back to anymore - a user with no active
    LLMProviderConfig can't generate videos, and that's raised here rather
    than silently attempting a keyless request that would only fail later
    with a more confusing error.
    """
    provider_config = (
        db.query(LLMProviderConfig)
        .filter(
            LLMProviderConfig.user_id == user_id,
            LLMProviderConfig.is_active == True,
        )
        .order_by(LLMProviderConfig.is_default.desc(), LLMProviderConfig.updated_at.desc())
        .first()
    )

    if not provider_config:
        raise ValueError(
            f"No active LLM provider configured for user {user_id} - "
            "configure a provider in AI Settings before generating videos."
        )

    provider = (
        provider_config.provider
        if isinstance(provider_config.provider, ProviderType)
        else ProviderType(provider_config.provider)
    )
    model = (
        (provider_config.extra_settings or {}).get("default_model")
        or next(iter(PROVIDER_INFO.get(provider, {}).get("models", [])), None)
    )
    if not model:
        raise ValueError(
            f"No model configured for user {user_id}'s {provider.value} provider."
        )
    encrypted_key = provider_config.api_key_encrypted
    base_url = provider_config.base_url

    llm_service.set_provider(
        model=model,
        provider=provider.value,
        base_url=base_url,
        api_key_encrypted=encrypted_key,
    )
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


def _extract_thumbnail(video_path: Path, output_path: Path) -> bool:
    """Grab a poster frame so the Video Vault has something to show.

    frontend/src/pages/VideoVault.jsx derives the thumbnail URL by swapping
    the .mp4 extension for .jpg, so the filename here must match the video's
    exactly apart from the extension.

    Seeks 1s in rather than to frame 0 - Manim scenes open on an empty
    background and fade content in, so the very first frame is usually a
    blank rectangle. Best-effort: a failure here must not fail the job,
    since the video itself is already rendered and usable.
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", "1",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "3",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0 or not output_path.exists():
            logger.warning(f"Thumbnail extraction failed: {result.stderr[-300:]}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Thumbnail extraction error: {e}")
        return False


def _probe_duration(path: Path) -> Optional[float]:
    """Duration of a media file in seconds, or None if ffprobe can't tell."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe failed for {path.name}: {e}")
    return None


def _content_end(path: Path) -> Optional[float]:
    """Timestamp of the last frame that still shows something.

    Manim scenes end by fading everything out, so the literal last frame is
    blank. That matters because narration routinely outruns the animation
    and `tpad` clones the last frame to cover the gap - cloning a blank one
    turns the whole tail black. Measured on a real render: 57s of content
    followed by 35s of frozen black, well over a third of the video.

    ffmpeg's own `blackdetect` is the obvious tool and is the wrong one
    here: it only fires once a frame is *almost entirely* black, which on a
    dark theme lands partway through the fade, so the held frame is still
    nearly invisible. Sampling average luminance and taking the last frame
    that is clearly above the floor finds the end of the content itself.

    Returns None if the video never goes dark or on any failure, in which
    case the caller pads exactly as it did before.
    """
    try:
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", str(path), "-vf",
             "fps=4,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
             "-f", "null", "/dev/null"],
            capture_output=True, text=True, timeout=300,
        )
        samples: List[tuple] = []
        t: Optional[float] = None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("frame:"):
                for token in line.split():
                    if token.startswith("pts_time:"):
                        t = float(token.split(":", 1)[1])
            elif "YAVG=" in line and t is not None:
                samples.append((t, float(line.split("=", 1)[1])))
        if len(samples) < 8:
            return None

        ys = sorted(y for _, y in samples)
        y_min = ys[0]
        y_med = ys[len(ys) // 2]
        # A video that never darkens has nothing to trim.
        if y_med - y_min < 1.0:
            return None
        floor = y_min + 0.35 * (y_med - y_min)

        last = None
        for ts, y in samples:
            if y >= floor:
                last = ts
        return last
    except Exception as exc:
        logger.warning(f"content-end detection failed for {path.name}: {exc}")
        return None


def _mux_audio_video(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Overlay narration onto the rendered video without truncating either.

    This used to pass `-shortest`, which ends the output at whichever track
    finishes first. Because the Manim animation and the TTS narration are
    generated independently, their lengths never match - so in practice every
    render was cut off: an animation that outran its narration was chopped
    mid-motion, and narration that outran its animation was cut mid-sentence.

    Instead: probe both, then pad the shorter one to the longer.
      - audio shorter -> pad with silence (`apad`), so the animation finishes
      - video shorter -> hold the final frame (`tpad`), so narration finishes

    Falls back to a plain copy-mux if probing fails, since a slightly
    mismatched video still beats no video at all.
    """
    v_dur = _probe_duration(video_path)
    a_dur = _probe_duration(audio_path)

    cmd = ["ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path)]

    if v_dur and a_dur:
        target = max(v_dur, a_dur)
        # Pad the video by holding its last frame, and/or the audio with
        # silence. -t pins the result so neither stream runs past the target.
        if a_dur < v_dur - 0.05:
            cmd += ["-af", "apad", "-c:v", "copy"]
        elif v_dur < a_dur - 0.05:
            # Hold the last frame that still shows something. Cloning the
            # literal last frame means cloning the closing fade-to-black,
            # which leaves the viewer staring at nothing while the narration
            # finishes. Trim the blank tail first, then pad from there.
            content_at = _content_end(video_path)
            keep = v_dur
            filters = []
            # A threshold in seconds is the wrong instinct here: what makes
            # the tail black is not how LONG the fade is but that the frame
            # being cloned is the faded one. A half-second closing fade with
            # 18s of narration left still blanks 18s of video, so trim any
            # blank end at all.
            if content_at is not None and content_at > 1.0 and (v_dur - content_at) > 0.3:
                keep = content_at
                filters.append(f"trim=end={keep:.2f}")
                filters.append("setpts=PTS-STARTPTS")
                logger.info(
                    f"Trimming {v_dur - keep:.1f}s of blank tail before padding "
                    f"(content ends at {keep:.1f}s)"
                )
            filters.append(f"tpad=stop_mode=clone:stop_duration={a_dur - keep:.2f}")
            # tpad re-encodes the video (can't clone frames with -c:v copy).
            cmd += ["-vf", ",".join(filters), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
        else:
            cmd += ["-c:v", "copy"]
        cmd += ["-t", f"{target:.2f}"]
        logger.info(
            f"Muxing: video={v_dur:.1f}s audio={a_dur:.1f}s -> {target:.1f}s "
            f"(padding {'audio' if a_dur < v_dur else 'video' if v_dur < a_dur else 'neither'})"
        )
    else:
        cmd += ["-c:v", "copy"]
        logger.warning("Could not probe durations - muxing without padding")

    cmd += ["-c:a", "aac", str(output_path)]

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
        # _retry_feedback is stashed into job.context below on a failed
        # render, before self.retry() re-invokes this same task fresh - lets
        # the regeneration prompt see exactly what broke last time instead
        # of blindly rerolling with no memory of the previous mistake.
        retry_feedback = (job.context or {}).get("_retry_feedback")
        generator = get_enhanced_generator()
        result = asyncio.run(generator.generate_enhanced_video(
            job.topic, job.context, retry_feedback=retry_feedback
        ))
        script = result["script"]
        manim_code = result["manim_code"]

        _update_job(db, job, script=script, stage="content", progress_percent=25,
                    message="Script ready, rendering animation...")

        # Phase 2: render with the manim CLI
        scene_file = work_dir / "scene.py"
        scene_file.write_text(manim_code)

        # Keep a copy outside work_dir, which is wiped in `finally`. Without
        # it the only record of what was actually rendered is the video
        # itself, so diagnosing a layout problem means guessing at the code
        # from pixels. Cheap (a few KB) and the file is overwritten per job.
        try:
            archive = OUTPUT_DIR / "scene_sources"
            archive.mkdir(parents=True, exist_ok=True)
            (archive / f"{job.id}_scene.py").write_text(manim_code)
        except Exception as exc:  # never fail a render over a debug artefact
            logger.warning(f"Could not archive scene source for job {job.id}: {exc}")

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
            _update_job(db, job, context={
                **(job.context or {}),
                "_retry_feedback": {"error": error_detail, "previous_code": manim_code},
            })
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

        # Poster frame for the Video Vault grid - best-effort, never fatal.
        _extract_thumbnail(final_path, final_path.with_suffix(".jpg"))

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
        try:
            db.rollback()
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
            # The session/connection itself may be the thing that died (e.g.
            # the OperationalError we're handling *was* the DB connection
            # dropping) - a fresh session is the only way to still persist
            # the FAILED status instead of silently losing it.
            db.close()
            fresh_db = SessionLocal()
            try:
                fresh_job = fresh_db.query(VideoJob).filter(VideoJob.id == video_job_id).first()
                if fresh_job:
                    _update_job(
                        fresh_db, fresh_job,
                        status=VideoJobStatus.FAILED,
                        stage="error",
                        error_message=str(e)[:2000],
                        message="Video generation failed",
                    )
            except Exception:
                logger.error(f"Could not persist FAILED status for job {video_job_id} even with a fresh session")
            finally:
                fresh_db.close()
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
