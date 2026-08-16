"""
Lesson generation: the LLM half of the pipeline.

Pure functions over an injected LLM callable, so the Celery task can own
transactions/progress and this module stays unit-testable without a worker,
a database, or a live gateway.

Everything the model returns is treated as untrusted:
- JSON is extracted from possible code fences before parsing.
- Slide elements are validated and CLAMPED to the canvas, not just rejected -
  a slightly mispositioned element still teaches, whereas discarding the scene
  loses the whole generation. This is the structural advantage over the Manim
  path: bad coordinates are repairable, bad Python is not.
- Actions referencing element ids that don't exist are dropped, since the
  renderer would otherwise try to spotlight a missing element.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .prompts import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    OUTLINE_SYSTEM,
    OUTLINE_USER,
    SLIDE_CONTENT_SYSTEM,
    SLIDE_CONTENT_USER,
    ACTIONS_SYSTEM,
    ACTIONS_USER,
    VIDEO_NARRATION_SYSTEM,
    VIDEO_NARRATION_USER,
)

logger = logging.getLogger(__name__)

MARGIN = 50
VALID_SCENE_TYPES = {"slide", "video"}

# An async (system_prompt, user_prompt, max_tokens) -> str callable.
LLMCall = Callable[[str, str, int], Awaitable[str]]


class LessonGenerationError(RuntimeError):
    pass


# ----------------------------------------------------------------- parsing --

def _extract_json(raw: str) -> Any:
    """Parse JSON out of a model response.

    Handles the three shapes models actually emit: bare JSON, a ```json fence,
    and JSON with prose wrapped around it. Raises rather than guessing if none
    of those yield valid JSON.
    """
    if not raw or not raw.strip():
        raise LessonGenerationError("empty response from model")

    text = raw.strip()

    # ```json ... ``` or ``` ... ```
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost {...} or [...] span.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise LessonGenerationError(f"could not parse JSON from response: {raw[:200]}")


# ---------------------------------------------------------------- outline ---

async def generate_outline(llm: LLMCall, requirement: str, context: str = "") -> Dict[str, Any]:
    """Stage 1: learner request -> titled, ordered scene outline."""
    context_block = f"Additional context from the conversation:\n{context}\n\n" if context else ""
    raw = await llm(
        OUTLINE_SYSTEM,
        OUTLINE_USER.format(requirement=requirement, context_block=context_block),
        3000,
    )
    data = _extract_json(raw)

    if not isinstance(data, dict) or "outlines" not in data:
        raise LessonGenerationError("outline response missing 'outlines'")

    outlines: List[Dict[str, Any]] = []
    for i, o in enumerate(data.get("outlines") or [], start=1):
        if not isinstance(o, dict) or not o.get("title"):
            continue
        # Anything outside our two supported types degrades to a slide rather
        # than failing the lesson - the model occasionally reaches for
        # upstream MAIC types (quiz/interactive) that we don't render yet.
        scene_type = o.get("type") if o.get("type") in VALID_SCENE_TYPES else "slide"
        outlines.append({
            "id": o.get("id") or f"scene_{i}",
            "type": scene_type,
            "title": str(o["title"])[:200],
            "description": str(o.get("description") or "")[:500],
            "keyPoints": [str(k)[:200] for k in (o.get("keyPoints") or [])][:6],
            "order": i,
        })

    if not outlines:
        raise LessonGenerationError("outline contained no usable scenes")

    return {
        "title": str(data.get("title") or requirement)[:500],
        "summary": str(data.get("summary") or "")[:1000],
        "outlines": outlines,
    }


# ------------------------------------------------------------ slide content --

def _clamp_element(el: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Coerce one element into something the renderer can lay out.

    Returns None only when the element is unusable (no id/type). Otherwise
    geometry is clamped into the canvas rather than dropped - see module
    docstring.
    """
    if not isinstance(el, dict) or not el.get("type"):
        return None

    try:
        left = float(el.get("left", MARGIN))
        top = float(el.get("top", MARGIN))
        width = float(el.get("width", 200))
        height = float(el.get("height", 60))
    except (TypeError, ValueError):
        return None

    width = max(20.0, min(width, CANVAS_WIDTH - 2 * MARGIN))
    height = max(20.0, min(height, CANVAS_HEIGHT - 2 * MARGIN))
    left = max(float(MARGIN), min(left, CANVAS_WIDTH - MARGIN - width))
    top = max(float(MARGIN), min(top, CANVAS_HEIGHT - MARGIN - height))

    el = dict(el)
    el.update({
        "left": round(left, 2),
        "top": round(top, 2),
        "width": round(width, 2),
        "height": round(height, 2),
        "rotate": el.get("rotate", 0) or 0,
    })

    # Text elements need these or the renderer reads undefined props.
    if el["type"] == "text":
        el.setdefault("content", "")
        el.setdefault("defaultFontName", "Georgia")
        el.setdefault("defaultColor", "#f2f2f2")

    return _normalise_shape(el)


def _normalise_shape(el: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in the fields @maic/dsl's PPTShapeElement requires.

    The prompt deliberately teaches a simple vocabulary (path: "rect" |
    "ellipse") because asking a model to emit correct SVG path data inline is
    a reliable source of malformed output. The real contract needs
    `viewBox: [w, h]`, an actual SVG `path` string and `fixedRatio` - and the
    renderer crashes on `viewBox[0]` if they are missing, taking the whole
    lesson down with it. Translating here keeps the model's job easy and the
    output valid.
    """
    if el.get("type") != "shape":
        return el

    w, h = el["width"], el["height"]
    raw_path = str(el.get("path") or "rect").strip().lower()

    if raw_path in ("ellipse", "circle", "oval"):
        rx, ry = w / 2, h / 2
        path = (
            f"M 0 {ry} A {rx} {ry} 0 1 0 {w} {ry} A {rx} {ry} 0 1 0 0 {ry} Z"
        )
    elif raw_path.startswith("m ") or raw_path.startswith("M "):
        path = el["path"]  # already real SVG - trust it
    else:  # rect and anything unrecognised
        path = f"M 0 0 L {w} 0 L {w} {h} L 0 {h} Z"

    el["viewBox"] = [w, h]
    el["path"] = path
    el.setdefault("fill", "#1b2430")
    el["fixedRatio"] = bool(el.get("fixedRatio", False))

    # ShapeText needs its own defaults or the renderer reads undefined fields.
    text = el.get("text")
    if isinstance(text, dict):
        text.setdefault("content", "")
        text.setdefault("defaultFontName", "Georgia")
        text.setdefault("defaultColor", "#f2f2f2")
        text.setdefault("align", "middle")
    elif text is not None:
        el.pop("text", None)

    return el


_GENERIC_SHAPE_WORDS = {
    "shape", "box", "rect", "rectangle", "bg", "background", "container",
    "panel", "block", "area", "region", "frame", "border", "divider", "line",
    "bar", "highlight", "group", "wrapper", "element", "diagram", "visual",
    # Structural suffixes: "low_marker" means the thing is called "low", the
    # word "marker" is just how the model spelled "this is a shape".
    "marker", "pointer", "indicator", "node", "cell", "item", "label",
}


def _label_from_id(element_id: str) -> str:
    """Turn an element id into the label the model clearly meant.

    Ids like `low_marker`, `mid_pointer`, `step1_box` are the model naming a
    thing it forgot to label. Stripping the structural suffix recovers the
    intent ("low", "mid", "step1"). Returns "" when nothing meaningful is
    left, which is the signal to drop the shape instead of labelling it.
    """
    words = [w for w in re.split(r"[_\-\s]+", str(element_id or "").lower()) if w]
    kept = [w for w in words if w not in _GENERIC_SHAPE_WORDS and not w.isdigit()]
    if not kept:
        return ""
    label = " ".join(kept).strip()
    return label[:40].title() if label else ""


def _fill_blank_shapes(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stop empty shapes from rendering as meaningless coloured boxes.

    The model uses shapes two ways: as a BACKGROUND behind text (intentional -
    a panel under a bullet list), and as a LABELLED marker or node. It
    routinely emits the second kind with no text, which renders as an
    anonymous rectangle - three identical yellow bars where "low", "mid" and
    "high" were meant, or a 640px empty strip. Blank boxes take up teaching
    space and convey nothing.

    A shape is only a legitimate background if a text element actually sits on
    top of it. Otherwise: recover a label from its id, or drop it.
    """
    texts = [e for e in elements if e.get("type") == "text"]
    out: List[Dict[str, Any]] = []

    for el in elements:
        if el.get("type") != "shape":
            out.append(el)
            continue

        own_text = el.get("text") or {}
        has_own = bool(re.sub(r"<[^>]+>", "", str(own_text.get("content", ""))).strip())
        backs_text = any(_rects_overlap(el, t) for t in texts)

        if has_own or backs_text:
            out.append(el)
            continue

        label = _label_from_id(el.get("id", ""))
        if not label:
            logger.info("dropping blank decorative shape %r", el.get("id"))
            continue

        if el["width"] >= 60:
            el["text"] = {
                "content": f"<p>{label}</p>",
                "defaultFontName": "Georgia",
                "defaultColor": "#f2f2f2",
                "align": "middle",
            }
            out.append(el)
        else:
            # Too narrow to hold text (a pointer/marker bar). Caption it just
            # underneath instead, centred on the marker, so the learner can
            # tell three identical bars apart.
            out.append(el)
            cap_w = 90.0
            out.append({
                "id": f"{el.get('id', 'shape')}__label",
                "type": "text",
                "left": round(max(float(MARGIN),
                                  min(el["left"] + el["width"] / 2 - cap_w / 2,
                                      CANVAS_WIDTH - MARGIN - cap_w)), 2),
                "top": round(min(el["top"] + el["height"] + 6,
                                 CANVAS_HEIGHT - MARGIN - 26), 2),
                "width": cap_w,
                "height": 26.0,
                "rotate": 0,
                "content": f"<p>{label}</p>",
                "defaultFontName": "Georgia",
                "defaultColor": "#d9c27e",
                "fontSize": 16,
            })

    return out


def _rects_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (
        a["left"] < b["left"] + b["width"]
        and b["left"] < a["left"] + a["width"]
        and a["top"] < b["top"] + b["height"]
        and b["top"] < a["top"] + a["height"]
    )


def _h_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Do these share horizontal space? Two elements side by side in separate
    columns never collide however they are stacked, so only same-column
    elements need vertical separation."""
    return a["left"] < b["left"] + b["width"] and b["left"] < a["left"] + a["width"]


def _compact_column(group: List[Dict[str, Any]]) -> None:
    """Repack one column of elements to fit, in place.

    Used when push-down has run out of canvas. Stacks the group from its own
    topmost position with a uniform gap, shrinking the gap and then the
    element heights proportionally if the content still doesn't fit. Shrinking
    is preferable to leaving text sitting on top of other text: a slightly
    squashed row is readable, an overlap is not.
    """
    group.sort(key=lambda e: e["top"])
    top0 = max(float(MARGIN), min(e["top"] for e in group))
    min_needed = sum(e["height"] for e in group) + 3.0 * (len(group) - 1)

    # If the group cannot fit below where it currently starts, reclaim the
    # whole canvas rather than overflowing the bottom margin. Without this a
    # dense column silently runs off the slide.
    if min_needed > (CANVAS_HEIGHT - MARGIN) - top0:
        top0 = float(MARGIN)
    available = (CANVAS_HEIGHT - MARGIN) - top0

    for gap in (16.0, 10.0, 6.0, 3.0):
        needed = sum(e["height"] for e in group) + gap * (len(group) - 1)
        if needed <= available:
            cursor = top0
            for e in group:
                e["top"] = round(cursor, 2)
                cursor += e["height"] + gap
            return

    # Still too tall even at the tightest gap - scale heights to fit. No
    # minimum floor here: an element clipped off the slide teaches nothing,
    # whereas a very short one is at least visible and positioned correctly.
    gap = 3.0
    total_h = sum(e["height"] for e in group)
    room = max(1.0, available - gap * (len(group) - 1))
    scale = room / total_h
    cursor = top0
    for e in group:
        e["height"] = round(max(8.0, e["height"] * scale), 2)
        e["top"] = round(cursor, 2)
        cursor += e["height"] + gap


def _deoverlap(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Guarantee no two elements overlap.

    The prompt already forbids overlap, but prompt compliance is not a
    guarantee - the same lesson the Manim renderer taught, where trusting the
    model to lay things out produced unreadable frames. Here it is cheap to
    fix because we own the coordinates.

    Two passes, because push-down alone silently fails on dense slides: it
    runs out of canvas, clamps to the bottom margin, and leaves elements
    stacked on the same line. The second pass repacks whatever is still in
    conflict.
    """
    placed: List[Dict[str, Any]] = []
    for el in elements:
        guard = 0
        while guard < 40 and any(_rects_overlap(el, p) for p in placed):
            blocker = next(p for p in placed if _rects_overlap(el, p))
            el["top"] = round(blocker["top"] + blocker["height"] + 16, 2)
            if el["top"] + el["height"] > CANVAS_HEIGHT - MARGIN:
                el["top"] = float(CANVAS_HEIGHT - MARGIN - el["height"])
                break  # out of room - pass 2 deals with it
            guard += 1
        placed.append(el)

    # Pass 2: repack any column that is still colliding.
    for _ in range(3):
        conflicts = [
            (a, b) for i, a in enumerate(placed) for b in placed[i + 1:]
            if _rects_overlap(a, b)
        ]
        if not conflicts:
            break
        # Build the column containing every conflicting element, pulling in
        # anything horizontally aligned with it so the repack can't just
        # shove the problem onto a neighbour.
        involved = {id(e): e for pair in conflicts for e in pair}
        column = [e for e in placed if any(_h_overlap(e, v) for v in involved.values())]
        if len(column) < 2:
            break
        _compact_column(column)

    return placed


async def generate_slide(
    llm: LLMCall, lesson_title: str, outline: Dict[str, Any]
) -> Dict[str, Any]:
    """Stage 2 (slide scenes): outline -> @maic/dsl Slide."""
    raw = await llm(
        SLIDE_CONTENT_SYSTEM,
        SLIDE_CONTENT_USER.format(
            lesson_title=lesson_title,
            order=outline["order"],
            title=outline["title"],
            description=outline["description"],
            key_points="\n".join(f"- {k}" for k in outline["keyPoints"]),
        ),
        # Raised for the richer slides the prompt now asks for (6-10 elements
        # with worked examples). Too low and the JSON truncates mid-object,
        # which surfaces as "slide contained no usable elements".
        4500,
    )
    data = _extract_json(raw)
    if not isinstance(data, dict):
        raise LessonGenerationError("slide response was not an object")

    elements = []
    for i, el in enumerate(data.get("elements") or [], start=1):
        cleaned = _clamp_element(el)
        if cleaned is None:
            continue
        cleaned.setdefault("id", f"el_{i}")
        elements.append(cleaned)

    if not elements:
        raise LessonGenerationError("slide contained no usable elements")

    # Label or drop empty shapes BEFORE laying out - captions added here are
    # new elements that the de-overlap pass then has to place.
    elements = _fill_blank_shapes(elements)
    elements = _deoverlap(elements)
    background = data.get("background")
    if not isinstance(background, dict):
        background = {"type": "solid", "color": "#0f1115"}

    return build_slide(elements, background)


def build_slide(elements: List[Dict[str, Any]], background: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap elements in the Slide envelope @maic/dsl requires."""
    return {
        "id": "slide",
        "viewportSize": CANVAS_WIDTH,
        "viewportRatio": round(CANVAS_HEIGHT / CANVAS_WIDTH, 4),
        "theme": {
            "backgroundColor": background.get("color", "#0f1115"),
            "themeColors": ["#8aa578", "#d9c27e"],
            "fontColor": "#f2f2f2",
            "fontName": "Georgia",
        },
        "background": background,
        "elements": elements,
    }


def build_video_slide(video_url: str, poster_url: Optional[str], title: str) -> Dict[str, Any]:
    """A slide whose content is a Manim render.

    PPTVideoElement is part of the @maic/dsl element union, so a rendered
    animation is a first-class slide element - no special-casing needed in the
    player beyond the play_video action.
    """
    heading_h = 70
    video_top = MARGIN + heading_h + 20
    video_h = CANVAS_HEIGHT - video_top - MARGIN
    video_w = min(CANVAS_WIDTH - 2 * MARGIN, round(video_h * 16 / 9))

    return build_slide(
        [
            {
                "id": "video_title",
                "type": "text",
                "left": MARGIN + 10,
                "top": MARGIN,
                "width": CANVAS_WIDTH - 2 * MARGIN - 20,
                "height": heading_h,
                "rotate": 0,
                "content": f"<p>{title}</p>",
                "defaultFontName": "Georgia",
                "defaultColor": "#8aa578",
                "fontSize": 34,
            },
            {
                "id": "video_1",
                "type": "video",
                "left": round((CANVAS_WIDTH - video_w) / 2, 2),
                "top": video_top,
                "width": video_w,
                "height": video_h,
                "rotate": 0,
                "autoplay": False,
                "src": video_url,
                **({"poster": poster_url} if poster_url else {}),
            },
        ],
        {"type": "solid", "color": "#0f1115"},
    )


# ---------------------------------------------------------------- actions ---

def _sanitise_actions(raw_actions: Any, valid_ids: set) -> List[Dict[str, Any]]:
    """Keep only actions the player can execute."""
    out: List[Dict[str, Any]] = []
    for a in raw_actions or []:
        if not isinstance(a, dict):
            continue
        kind = a.get("type")
        if kind == "speech":
            content = str(a.get("content") or "").strip()
            if content:
                out.append({"type": "speech", "content": content[:2000]})
        elif kind in ("spotlight", "play_video"):
            target = a.get("elementId")
            # Dropping instead of repairing: pointing at the wrong element is
            # more confusing than not pointing at all.
            if target in valid_ids:
                out.append({"type": kind, "elementId": target})
    return out


async def generate_actions(
    llm: LLMCall, lesson_title: str, outline: Dict[str, Any], slide: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Stage 3: slide -> narration + choreography."""
    elements = slide.get("elements", [])
    valid_ids = {e["id"] for e in elements if e.get("id")}
    is_video = any(e.get("type") == "video" for e in elements)

    if is_video:
        system, user = VIDEO_NARRATION_SYSTEM, VIDEO_NARRATION_USER.format(
            lesson_title=lesson_title,
            order=outline["order"],
            title=outline["title"],
            description=outline["description"],
            key_points="\n".join(f"- {k}" for k in outline["keyPoints"]),
        )
    else:
        summary_lines = []
        for e in elements:
            label = re.sub(r"<[^>]+>", " ", str(e.get("content") or "")).strip()
            if not label and isinstance(e.get("text"), dict):
                label = re.sub(r"<[^>]+>", " ", str(e["text"].get("content") or "")).strip()
            summary_lines.append(f"- {e.get('id')} — {(label or e.get('type'))[:80]}")
        system, user = ACTIONS_SYSTEM, ACTIONS_USER.format(
            lesson_title=lesson_title,
            order=outline["order"],
            title=outline["title"],
            description=outline["description"],
            key_points="\n".join(f"- {k}" for k in outline["keyPoints"]),
            element_summary="\n".join(summary_lines),
        )

    try:
        actions = _sanitise_actions(_extract_json(await llm(system, user, 3500)), valid_ids)
    except LessonGenerationError as e:
        logger.warning("action generation failed for '%s': %s", outline["title"], e)
        actions = []

    # A scene with no narration would render as a silent slide the player just
    # sits on, so fall back to the outline text rather than shipping nothing.
    if not any(a["type"] == "speech" for a in actions):
        fallback = outline["description"] or outline["title"]
        actions.insert(0, {"type": "speech", "content": fallback})
    return actions
