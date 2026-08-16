"""
Deterministic checks on what Scoratis produces.

Every check here encodes a bug that actually shipped in this project and was
found by a human looking at the output: text laid over a diagram, a video
whose last thirty seconds were frozen black, a slide with an empty shape
where a graphic should be, a multiple-choice question whose correct answer
was not among its options.

Deliberately no model in the loop. A judge that scores 4/5 tells you nothing
actionable and costs money to run; "lesson 12 scene 3 has an element 240px
outside the canvas" tells you exactly what to fix and costs nothing. The
judge-based checks live in socratic_probes.py and are opt-in.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Slide canvas, matching services/lesson/prompts.py.
CANVAS_W, CANVAS_H = 1000, 562
# The generator clamps to the canvas; anything beyond this is a real escape,
# not a rounding difference.
BOUNDS_TOLERANCE = 4

# A held frame at or below the video black level means the tail is dead.
BLACK_LUMA = 17.0
MIN_TAIL_SAMPLES = 3


@dataclass
class Finding:
    check: str
    subject: str
    detail: str
    severity: str = "error"  # error | warn


@dataclass
class CheckReport:
    checked: int = 0
    findings: List[Finding] = field(default_factory=list)

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "warn"]

    def add(self, check: str, subject: str, detail: str, severity: str = "error") -> None:
        self.findings.append(Finding(check, subject, detail, severity))


# ------------------------------------------------------------- review items --

def check_review_items(items: Iterable[Any], report: CheckReport) -> None:
    """Structural validity of generated questions.

    An unanswerable or unmarkable question is worse than a missing one: it
    sits in the queue and the student cannot get past it.
    """
    for item in items:
        report.checked += 1
        subject = f"review_item {item.id}"
        kind = item.kind.value if hasattr(item.kind, "value") else str(item.kind)
        rubric = item.rubric or {}

        if not (item.prompt or "").strip():
            report.add("item.prompt", subject, "prompt is empty")
        if not (item.answer or "").strip():
            report.add("item.answer", subject, "answer is empty")

        if kind == "mcq":
            options = rubric.get("options") or []
            if len(options) < 2:
                report.add("mcq.options", subject,
                           f"only {len(options)} option(s); cannot be answered")
            elif item.answer not in options:
                report.add("mcq.answer_present", subject,
                           "correct answer is not among the options")
            if len(set(options)) != len(options):
                report.add("mcq.duplicates", subject, "duplicate options")
            for bad in ("all of the above", "none of the above"):
                if any(bad in str(o).lower() for o in options):
                    report.add("mcq.lazy_option", subject, f"uses {bad!r}", "warn")

        if kind in ("recall", "problem"):
            if not rubric.get("must_include"):
                report.add("recall.rubric", subject,
                           "no must_include points, so grading has nothing to mark against",
                           "warn")
            # A question whose answer runs to an essay cannot be recalled in
            # the seconds a review item is meant to take.
            if len(item.answer or "") > 600:
                report.add("recall.answer_length", subject,
                           f"answer is {len(item.answer)} chars; too long to recall",
                           "warn")

        # A prompt referring to what is on screen cannot be answered weeks
        # later with the lesson closed.
        # Anything anchored to the lesson rather than the idea. Reviewed
        # weeks later with nothing on screen, "discussed in the lesson" is
        # as unanswerable as "shown above".
        for phrase in ("this slide", "the diagram above", "shown above",
                       "in the video", "in the lesson", "discussed in the",
                       "we learned", "as we saw", "from the lesson"):
            if phrase in (item.prompt or "").lower():
                report.add("item.self_contained", subject,
                           f"prompt refers to {phrase!r}, but review happens without the lesson")
                break


# ------------------------------------------------------------------ lessons --

def _elements_of(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    return ((scene.get("slide") or {}).get("elements")) or []


def check_lessons(lessons: Iterable[Any], report: CheckReport) -> None:
    """Slide geometry and content, per scene."""
    for lesson in lessons:
        scenes = lesson.scenes or []
        if not scenes:
            report.add("lesson.scenes", f"lesson {lesson.id}", "completed lesson has no scenes")
            continue

        for scene in scenes:
            report.checked += 1
            subject = f"lesson {lesson.id} / {scene.get('id')}"
            elements = _elements_of(scene)

            if not elements:
                report.add("scene.empty", subject, "scene has no elements")
                continue

            has_text = any(e.get("type") == "text" and str(e.get("content") or "").strip()
                           for e in elements)
            if not has_text:
                report.add("scene.no_text", subject, "scene has no readable text")

            for el in elements:
                el_id = el.get("id", "?")
                left, top = el.get("left"), el.get("top")
                width, height = el.get("width"), el.get("height")
                if None in (left, top, width, height):
                    continue

                if (left < -BOUNDS_TOLERANCE or top < -BOUNDS_TOLERANCE
                        or left + width > CANVAS_W + BOUNDS_TOLERANCE
                        or top + height > CANVAS_H + BOUNDS_TOLERANCE):
                    report.add(
                        "element.bounds", subject,
                        f"{el_id} at ({left:.0f},{top:.0f}) {width:.0f}x{height:.0f} "
                        f"escapes the {CANVAS_W}x{CANVAS_H} canvas",
                    )

                # The blank-shape bug: a shape with no path renders as
                # nothing, leaving a hole where a graphic was promised.
                if el.get("type") == "shape" and not el.get("path"):
                    report.add("element.blank_shape", subject,
                               f"{el_id} is a shape with no path")

            # Narration is what the TTS voice reads; a scene without it is
            # silent in the player.
            speech = [a for a in (scene.get("actions") or []) if a.get("type") == "speech"]
            if not speech:
                report.add("scene.no_narration", subject, "scene has no speech actions", "warn")


# ------------------------------------------------------------------ renders --

def _luma_samples(path: Path) -> List[float]:
    """Average luminance once per second, via ffmpeg."""
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-i", str(path), "-vf",
         "fps=1,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
         "-f", "null", "/dev/null"],
        capture_output=True, text=True, timeout=300,
    )
    return [
        float(line.split("=", 1)[1])
        for line in proc.stdout.splitlines()
        if "YAVG=" in line
    ]


def check_renders(video_paths: Iterable[Path], report: CheckReport,
                  sample: bool = True) -> None:
    """Duration, resolution, and whether the tail is dead.

    The frozen-black tail is the one worth automating: padding a video to
    match narration holds the LAST frame, which on a scene that fades out is
    black - measured at 35 seconds of nothing on a 92 second video, and
    invisible to anyone not watching to the end.
    """
    for path in video_paths:
        report.checked += 1
        subject = path.name

        if not path.exists():
            report.add("render.missing", subject, "file does not exist")
            continue

        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=width,height", "-of", "json", str(path)],
                capture_output=True, text=True, timeout=60,
            )
            meta = json.loads(probe.stdout or "{}")
            duration = float(meta.get("format", {}).get("duration") or 0)
            stream = (meta.get("streams") or [{}])[0]
            width, height = stream.get("width"), stream.get("height")
        except Exception as exc:
            report.add("render.probe", subject, f"could not probe: {exc}")
            continue

        if duration <= 0:
            report.add("render.duration", subject, "zero-length video")
            continue
        if duration < 20:
            report.add("render.duration", subject,
                       f"only {duration:.0f}s; scenes this short teach very little", "warn")
        if width and height and (width < 1280 or height < 720):
            report.add("render.resolution", subject, f"{width}x{height} is below 720p", "warn")

        if not sample:
            continue

        try:
            luma = _luma_samples(path)
        except Exception as exc:
            report.add("render.luma", subject, f"could not sample: {exc}", "warn")
            continue

        if len(luma) < MIN_TAIL_SAMPLES:
            continue

        tail = luma[-MIN_TAIL_SAMPLES:]
        if all(v <= BLACK_LUMA for v in tail):
            dark = 0
            for value in reversed(luma):
                if value > BLACK_LUMA:
                    break
                dark += 1
            report.add("render.black_tail", subject,
                       f"last {dark}s are blank (luma {tail[-1]:.1f})")

        # A completely static video is a slideshow, not an animation.
        if len(set(round(v, 1) for v in luma)) == 1:
            report.add("render.static", subject, "every sampled frame is identical", "warn")


# ------------------------------------------------------------------ concepts --

def check_concepts(concepts: Iterable[Any], report: CheckReport) -> None:
    """Catch concept-graph corruption.

    The merge bug that credited mastery of Newton's First Law to the Second
    is the case this exists for: two concepts whose names differ only by an
    ordinal must both survive as separate rows.
    """
    from models import meaningful_tokens

    seen: Dict[str, Any] = {}
    for concept in concepts:
        report.checked += 1
        subject = f"concept {concept.id} ({concept.name})"

        if not (concept.name or "").strip():
            report.add("concept.name", subject, "concept has no name")
        if concept.slug in seen:
            report.add("concept.duplicate_slug", subject,
                       f"shares slug {concept.slug!r} with concept {seen[concept.slug].id}")
        seen[concept.slug] = concept

        if not meaningful_tokens(concept.name or ""):
            report.add("concept.generic", subject,
                       "name is entirely generic vocabulary", "warn")


def format_report(title: str, report: CheckReport) -> str:
    lines = [f"{title}: {report.checked} checked, "
             f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"]
    for finding in report.errors + report.warnings:
        mark = "ERROR" if finding.severity == "error" else "warn "
        lines.append(f"  {mark}  [{finding.check}] {finding.subject}: {finding.detail}")
    return "\n".join(lines)
