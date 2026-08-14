"""
Video Generation Service for Scoratis
Interfaces with maestro-studio for AI-powered educational video generation
"""

import ast
import builtins
import os
import re
import sys
import asyncio
import uuid
import json
import httpx
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from enum import Enum

import manim as manim_module

logger = logging.getLogger(__name__)

# Add maestro-studio to path (use environment variable or default)
MAESTRO_PATH = Path(os.environ.get("MAESTRO_PATH", str(Path.home() / "maestro-studio")))
if MAESTRO_PATH.exists():
    sys.path.insert(0, str(MAESTRO_PATH))


class SmartVideoClient:
    """
    Video content client (titles, bullet points, narration).

    Cloud/API only - local providers (Ollama/LM Studio/LocalAI/Text Gen
    WebUI) were removed from the product in migration 010, so there is no
    local fallback to degrade to. Callers must have a configured provider
    with an API key; generate() raises otherwise rather than silently
    emitting placeholder content.
    """

    def __init__(self):
        self._llm_service = None
        self._use_api = False
        self._initialize()

    def _initialize(self):
        """Initialize from the current per-user LLM config."""
        try:
            from llm_service import llm_service
            config = llm_service.get_current_config()

            if config and llm_service.has_api_key():
                self._use_api = True
                self._llm_service = llm_service
                logger.info(f"SmartVideoClient: Using API ({config.get('provider')}/{config.get('model')})")
            else:
                logger.warning("SmartVideoClient: No configured provider/API key available")

        except Exception as e:
            logger.warning(f"SmartVideoClient init error: {e}")

    @property
    def model(self) -> str:
        """Get the current model name"""
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("model", "unknown") if config else "unknown"
        return "unconfigured"

    @property
    def provider(self) -> str:
        """Get the current provider name"""
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("provider", "api") if config else "api"
        return "unconfigured"

    def check_model_exists(self) -> bool:
        """Check if the model is available"""
        return self._use_api

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[list] = None
    ) -> str:
        """Generate text using the configured provider."""
        if not self._use_api:
            raise RuntimeError(
                "No LLM provider configured - add a provider and API key in AI Settings."
            )
        return self._generate_with_api(prompt, max_tokens, temperature)

    def _generate_with_api(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using the configured API"""
        import asyncio

        async def _async_generate():
            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are an expert educational content creator. Generate clear, engaging, and accurate content. Output only the requested content without extra commentary.",
            )
            logger.info(f"SmartVideoClient generated {len(response)} chars using {self.provider}/{self.model}")
            return response

        # Handle async in sync context
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - use thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_generate())
                return future.result(timeout=120)
        except RuntimeError:
            # No running loop
            return asyncio.run(_async_generate())


class SmartManimClient:
    """
    Manim code generator.

    Cloud/API only - see SmartVideoClient's docstring. There is no local
    model fallback; generate_manim_code() raises if no provider is
    configured rather than emitting a placeholder scene.
    """

    def __init__(self):
        self._use_api = False
        self._llm_service = None
        self._initialize()

    def _initialize(self):
        """Initialize from the current per-user LLM config."""
        try:
            from llm_service import llm_service
            config = llm_service.get_current_config()

            if config and llm_service.has_api_key():
                self._use_api = True
                self._llm_service = llm_service
                logger.info(f"SmartManimClient: Using API ({config.get('provider')}/{config.get('model')})")
            else:
                logger.warning("SmartManimClient: No configured provider/API key available")

        except Exception as e:
            logger.warning(f"SmartManimClient init error: {e}")

    @property
    def model(self) -> str:
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("model", "unknown") if config else "unknown"
        return "unconfigured"

    @property
    def provider(self) -> str:
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("provider", "api") if config else "api"
        return "unconfigured"

    def generate_manim_code(
        self,
        topic: str,
        description: str = "",
        duration: int = 30,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Manim code using the configured provider."""
        if not self._use_api:
            raise RuntimeError(
                "No LLM provider configured - add a provider and API key in AI Settings."
            )

        prompt = self._build_manim_prompt(topic, description, duration, context)
        code = self._generate_with_api(prompt)

        # Clean and validate
        code = self._clean_manim_code(code)
        code = self._validate_and_fix_code(code, topic)
        return code

    def _build_manim_prompt(self, topic: str, description: str, duration: int, context: Optional[Dict]) -> str:
        """Build the prompt for Manim code generation"""
        context_sections = []
        if context:
            if context.get("key_concepts"):
                context_sections.append(f"Key concepts: {', '.join(context['key_concepts'][:5])}")
            if context.get("visual_elements"):
                context_sections.append(f"Visual elements: {', '.join(context['visual_elements'][:5])}")

        context_info = "\n".join(context_sections) if context_sections else ""

        return f"""Generate a complete Manim animation for: {topic}

{description if description else "Create an engaging educational animation."}

{context_info}

REQUIREMENTS:
1. Use ManimCE syntax with `from manim import *`
2. Create class `ManimScene(Scene)` with `construct(self)` method
3. Target duration: {duration} seconds
4. Include title, smooth animations, text labels
5. Use Create(), Write(), FadeIn(), Transform() for animations

OUTPUT: Return ONLY valid Python code starting with `from manim import *`"""

    def _generate_with_api(self, prompt: str) -> str:
        """Generate using configured API"""
        import asyncio

        async def _async_generate():
            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are an expert Manim animator. Generate only valid Python code without explanations.",
            )
            logger.info(f"SmartManimClient generated {len(response)} chars using API")
            return response

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_generate())
                return future.result(timeout=180)
        except RuntimeError:
            return asyncio.run(_async_generate())

    def _clean_manim_code(self, code: str) -> str:
        """Clean up generated Manim code"""
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0]

        if not code.strip().startswith("from manim"):
            if "from manim" in code:
                code = code[code.find("from manim"):]
            else:
                code = "from manim import *\n\n" + code

        return code.strip()

    def _validate_and_fix_code(self, code: str, topic: str) -> str:
        """Validate and fix common issues in generated code"""
        if "class ManimScene" not in code:
            # Try to find any Scene class and rename it
            import re
            match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', code)
            if match:
                old_name = match.group(1)
                code = code.replace(f"class {old_name}(Scene)", "class ManimScene(Scene)")

        if "def construct(self)" not in code and "def construct(" not in code:
            code = code.replace("class ManimScene(Scene):",
                              "class ManimScene(Scene):\n    def construct(self):\n        pass")

        # No-ops for this client's single-construct output, but keeps both
        # generators behaving identically if the prompt ever grows scenes.
        code = _inject_manim_compat(code)
        code = _enforce_scene_isolation(code)
        code = _stub_undefined_names(code)

        return code

    def _generate_fallback_code(self, topic: str, duration: int) -> str:
        """Generate minimal working Manim animation as fallback"""
        return f'''from manim import *

class ManimScene(Scene):
    def construct(self):
        title = Text("{topic[:50]}", font_size=36)
        self.play(Write(title))
        self.wait(2)
        self.play(FadeOut(title))
'''



# =============================================================================
# ENHANCED VIDEO GENERATION PROMPTS
# =============================================================================

def _script_scene_structure(duration: int) -> str:
    """Scene-structure section of SCRIPT_PLANNING_PROMPT, sized to the
    target duration instead of a fixed 5-scene structure.

    The original 5-scene breakdown's own per-scene minimums summed to
    71-99 seconds regardless of what TARGET DURATION said above it - a
    direct, silent self-contradiction for every short auto-generated clip
    (10-30s, which is every video the agent's generate_video tool and the
    video_analyzer_service auto-generation path produce). The model was
    being told both "keep this to 20 seconds" and "these 5 scenes need
    71+ seconds minimum" in the same prompt, and likely resolved that by
    writing a full-length script anyway - directly contributing to the
    token-truncation failures the max_tokens fix above addresses, and
    almost certainly still producing badly rushed 5-scene pacing even
    when it happened to fit.
    """
    if duration <= 30:
        half = max(5, duration // 2)
        return f"""## SCENE STRUCTURE (2 scenes required, sized for a {duration}-second clip):

### Scene 1: HOOK + CONCEPT (roughly {half} seconds)
- Open with the core question or why this matters, then introduce the concept directly
- 2-3 visual elements - keep it focused, not exhaustive

### Scene 2: EXPLANATION + TAKEAWAY (roughly {duration - half} seconds)
- Show the key mechanism or process with 2-3 visual elements
- One concrete example, then a single memorable closing line"""
    elif duration <= 60:
        edge = max(5, duration // 6)
        return f"""## SCENE STRUCTURE (3 scenes required, sized for a {duration}-second clip):

### Scene 1: HOOK (roughly {edge} seconds)
- Attention-grabbing question or surprising fact

### Scene 2: EXPLANATION (roughly {duration - 2 * edge} seconds)
- Step-by-step breakdown with visuals, 1-2 concrete examples

### Scene 3: SUMMARY (roughly {edge} seconds)
- Key takeaway, memorable closing statement"""
    else:
        return """## SCENE STRUCTURE (5 scenes required):

### Scene 1: HOOK (8-12 seconds)
- Attention-grabbing question or surprising fact
- Visual that immediately captures interest
- Why this topic matters to the viewer

### Scene 2: FOUNDATION (15-20 seconds)
- Core concept introduction with 3-4 visual elements
- Key definitions displayed on screen
- Building blocks for understanding

### Scene 3: EXPLANATION (25-35 seconds)
- Step-by-step breakdown with numbered visuals
- Diagrams, arrows, and relationships
- Cause-effect demonstrations
- At least 2 concrete examples with visuals

### Scene 4: APPLICATION (15-20 seconds)
- Real-world example with visual demonstration
- Problem-solving walkthrough
- Practical connection to viewer's life

### Scene 5: SUMMARY (8-12 seconds)
- 3 key takeaways displayed as bullet points
- Visual recap of main diagram/concept
- Memorable closing statement"""


SCRIPT_PLANNING_PROMPT = """You are an expert educational video scriptwriter creating content for visual learners.
Create a detailed scene-by-scene breakdown for: {topic}

TARGET DURATION: {duration} seconds
AUDIENCE: High school to undergraduate level
VISUAL DENSITY: 8-10 visual elements per concept

{scene_structure}

## VISUAL TYPES
Every visual's "type" field must be one of: text, diagram, equation, numbered_list, shape.
There are no photo/image assets available - never use "image" or "photo" as a type.
Represent any photographic or real-world visual idea (a sunset, a leaf, an
apparatus) as a "diagram" built from simple shapes instead, described in
words for the animator to draw.

## ANIMATION NAMES
Every visual's "animation" field must be one of exactly these (they map
directly to real Manim animation classes - inventing other names like "Pop",
"SlideIn", "ZoomIn", or "Bounce" will crash the renderer, since no such
classes exist): Write, Create, FadeIn, FadeOut, GrowFromCenter, Indicate,
DrawBorderThenFill.

## OUTPUT FORMAT (JSON only, no markdown):
{{
  "title": "Engaging title (max 8 words)",
  "total_duration": {duration},
  "complexity": "simple|moderate|complex",
  "scenes": [
    {{
      "scene_number": 1,
      "name": "Hook",
      "duration": 10,
      "narration": "Full narration text for this scene...",
      "visuals": [
        {{"type": "text", "content": "Title text", "style": "title", "animation": "Write", "duration": 2}},
        {{"type": "diagram", "description": "What to show", "animation": "FadeIn", "duration": 3}},
        {{"type": "equation", "latex": "E=mc^2", "animation": "Write", "duration": 2}}
      ],
      "key_point": "Main takeaway from this scene"
    }}
  ],
  "key_concepts": ["concept1", "concept2", "concept3"],
  "visual_style": "scientific|mathematical|process|comparison|timeline",
  "color_scheme": "blue-primary|green-growth|red-energy|purple-abstract"
}}

IMPORTANT: Output ONLY valid JSON. No explanations, no markdown code blocks."""

RETRY_FEEDBACK_TEMPLATE = """
## YOUR PREVIOUS ATTEMPT FAILED - FIX THIS SPECIFIC ISSUE

Your last attempt at this exact video produced code that crashed during rendering.
Do not repeat this mistake. Read the error carefully and fix the root cause.

Previous code:
```python
{previous_code}
```

Error it raised:
```
{error}
```
"""

def _manim_code_structure(script: dict) -> str:
    """CODE STRUCTURE section of ENHANCED_MANIM_PROMPT, sized to however
    many scenes the script actually has - previously hardcoded exactly 5
    scene methods regardless of the script passed in, so a short auto-
    generated script (now 2-3 scenes via _script_scene_structure above)
    was still being told to implement a 5-method construct(), silently
    reintroducing the same duration/content mismatch the script-side fix
    just removed.
    """
    scenes = script.get("scenes") or []
    if not scenes:
        scenes = [{"scene_number": i, "name": f"Scene {i}"} for i in range(1, 6)]

    method_names = [f"scene_{s.get('scene_number', i + 1)}" for i, s in enumerate(scenes)]
    calls = "\n".join(f"        self.{name}()" for name in method_names)
    first_def = f"""    def {method_names[0]}(self):
        # {scenes[0].get('name', 'Scene 1')}: {scenes[0].get('key_point', '')}
        pass"""

    return f"""```python
from manim import *

class ManimScene(Scene):
    def construct(self):
{calls}

{first_def}

    # ... one method per scene above, same pattern
```"""


# A scene call that isn't already followed by a clear - the negative
# lookahead keeps the transform idempotent, so a re-run (e.g. the render
# retry path) can't stack duplicate cleanups.
_SCENE_CALL_RE = re.compile(
    r'^([ \t]*)self\.(scene_\w+)\(\)[ \t]*$(?!\n[ \t]*self\._clear_screen\(\))',
    re.MULTILINE,
)

# `self.play(FadeOut(*self.mobjects))` and `self.play(*[FadeOut(m) for m in
# self.mobjects])`, with or without trailing kwargs like run_time=. Both
# raise ValueError when the stage happens to be empty.
_FULL_STAGE_FADE_RE = re.compile(
    r'^([ \t]*)self\.play\(\s*(?:FadeOut\(\s*\*\s*self\.mobjects\s*\)'
    r'|\*\s*\[\s*FadeOut\([^\]]*\)\s+for\s+\w+\s+in\s+self\.mobjects\s*\])'
    r'[^\n)]*\)[ \t]*$',
    re.MULTILINE,
)

# NOTE: _clear_screen's body deliberately iterates a local `_mobs` copy
# rather than `self.mobjects` directly. Iterating self.mobjects here would
# make the helper itself match _FULL_STAGE_FADE_RE, so re-running the
# transform would rewrite the helper's own body into a call to itself -
# infinite recursion. Keeping it off that pattern is what makes the pass
# idempotent.
#
# _resolve_overlaps fixes the *within-scene* half of the overlap problem.
# The model routinely anchors a caption to a thin connector rather than to
# the tall shapes around it - e.g.
#     arrow = Arrow(box_a.get_right(), box_b.get_left())   # at box mid-height
#     caption.next_to(arrow, DOWN, buff=0.5)               # 0.5 < box half-height
# which lands the caption inside both boxes. Prompt rules don't reliably
# prevent this, so the overridden wait() de-clutters the frame right before
# it's held on screen (every scene ends up calling wait()).
#
# A label fully INSIDE a shape is intentional ("Master" centred in its box)
# and is left alone; only partial intersections - the ones that read as
# broken - get nudged clear.
# Colour names the model reaches for that Manim CE does not define, mapped
# to the nearest real constant. Single source of truth: the injected shim
# and the undefined-name checker are both built from this, so they cannot
# drift apart and start flagging names the shim already supplies.
_COLOR_ALIASES = (
    ("BROWN", "DARK_BROWN"), ("CYAN", "TEAL"), ("MAGENTA", "PINK"),
    ("SILVER", "GREY_B"), ("INDIGO", "PURPLE_E"), ("VIOLET", "PURPLE"),
    ("LIME", "GREEN_A"), ("OLIVE", "GREEN_E"), ("NAVY", "BLUE_E"),
    ("BEIGE", "LIGHT_BROWN"), ("TAN", "LIGHT_BROWN"), ("CRIMSON", "RED_E"),
    ("SCARLET", "RED"), ("AMBER", "YELLOW_E"), ("TURQUOISE", "TEAL_A"),
    ("EMERALD", "GREEN_D"), ("CHARCOAL", "GREY_E"), ("IVORY", "WHITE"),
    ("LIGHTBLUE", "BLUE_B"), ("DARKBLUE", "BLUE_E"),
    ("LIGHTGREEN", "GREEN_B"), ("DARKGREEN", "GREEN_E"),
    ("LIGHTRED", "RED_B"), ("DARKRED", "RED_E"),
    ("LIGHTGRAY", "GREY_B"), ("LIGHTGREY", "GREY_B"),
    ("DARKGRAY", "GREY_E"), ("DARKGREY", "GREY_E"),
    ("LIGHTYELLOW", "YELLOW_B"), ("DARKYELLOW", "YELLOW_E"),
    ("LIGHTPURPLE", "PURPLE_B"), ("DARKPURPLE", "PURPLE_E"),
    ("LIGHTORANGE", "GOLD_B"), ("DARKORANGE", "GOLD_E"),
)

_SHIM_SHAPES = ("Diamond", "Oval")

_MANIM_COMPAT = '''
# --- injected: names the model reaches for that Manim CE does not define ---
# A NameError anywhere in the file aborts the entire render, and the lesson
# then silently degrades that scene to a static slide - real examples from
# one lesson: `BROWN` (Manim has DARK_BROWN) and `Diamond` (no such class).
# Purely additive: an alias is skipped whenever Manim defines that name.
for _alias, _target in (
''' + "".join(
    f'    ("{a}", "{b}"),\n' for a, b in _COLOR_ALIASES
) + '''):
    if _alias not in globals() and _target in globals():
        globals()[_alias] = globals()[_target]

if "Diamond" not in globals():
    def Diamond(**kwargs):
        return Square(**kwargs).rotate(PI / 4)

if "Oval" not in globals():
    def Oval(**kwargs):
        return Ellipse(**kwargs)


# arrange_in_grid(rows=1, cols=4) on a VGroup holding 8 things raises
# "Too few rows and columns to fit all submobjects" and kills the render.
# The model picks the grid from how it imagines the diagram, not from how
# many mobjects it actually built, so widen the grid to fit rather than
# refusing to lay it out.
try:
    import math as _math

    _orig_arrange_in_grid = Mobject.arrange_in_grid

    def _safe_arrange_in_grid(self, *args, **kwargs):
        _rows, _cols = kwargs.get("rows"), kwargs.get("cols")
        _n = len(self.submobjects)
        if _rows and _cols and _rows * _cols < _n:
            kwargs["cols"] = int(_math.ceil(_n / float(_rows)))
        try:
            return _orig_arrange_in_grid(self, *args, **kwargs)
        except Exception:
            # Positional rows/cols, or some other shape mismatch - let
            # Manim choose the grid itself.
            _clean = {k: v for k, v in kwargs.items() if k not in ("rows", "cols")}
            return _orig_arrange_in_grid(self, **_clean)

    Mobject.arrange_in_grid = _safe_arrange_in_grid
except Exception:
    pass

'''

_MISSING_REF_CLASS = '''

class _MissingRef:
    """Stands in for a name the model used but never defined.

    The model writes things like `Text("RuBP").move_to(CIRCLE.get_center())`
    where `CIRCLE` was never assigned - it means "the circle I just made".
    Python raises NameError, the render dies, and the scene silently becomes
    a static slide, so the student loses the whole animation over one bad
    identifier. Answering positional queries with ORIGIN keeps the render
    alive; the object lands at the centre instead of nowhere at all, and
    the layout passes then push it clear of whatever it overlaps.
    """

    def __init__(self, name="?"):
        self._name = name

    def _origin(self, *a, **k):
        return ORIGIN

    get_center = get_top = get_bottom = get_left = get_right = _origin
    get_corner = get_start = get_end = get_center_of_mass = _origin

    @property
    def width(self):
        return 1.0

    @property
    def height(self):
        return 1.0

    def __getattr__(self, item):
        # Any other method call resolves to ORIGIN rather than exploding.
        return lambda *a, **k: ORIGIN

    def __add__(self, other):
        return ORIGIN + other

    def __radd__(self, other):
        return other + ORIGIN

    def __sub__(self, other):
        return ORIGIN - other

    def __rsub__(self, other):
        return other - ORIGIN

    def __mul__(self, other):
        return ORIGIN

    __rmul__ = __mul__

    def __truediv__(self, other):
        return ORIGIN

    def __iter__(self):
        return iter(ORIGIN)
'''


def _inject_manim_compat(code: str) -> str:
    """Put the compatibility shim straight after the manim import."""
    if "_alias, _target" in code:
        return code
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("from manim import"):
            lines.insert(i + 1, _MANIM_COMPAT)
            return "\n".join(lines)
    return _MANIM_COMPAT + "\n" + code


def _undefined_names(code: str) -> List[str]:
    """Names the code reads but never binds anywhere.

    Deliberately scope-blind: it unions every binding in the file, so a name
    is reported only when nothing in the module defines it under any
    circumstances. That makes false positives very unlikely, which matters
    because each one becomes a stubbed-out object.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    bound: Set[str] = set()
    loaded: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            (bound if isinstance(node.ctx, (ast.Store, ast.Del)) else loaded).add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(node.name)
            args = node.args
            for a in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                bound.add(a.arg)
            if args.vararg:
                bound.add(args.vararg.arg)
            if args.kwarg:
                bound.add(args.kwarg.arg)
        elif isinstance(node, ast.ClassDef):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)

    known = set(dir(builtins)) | set(dir(manim_module)) | bound
    known.update(a for a, _ in _COLOR_ALIASES)
    known.update(_SHIM_SHAPES)
    known.update({"self", "_MissingRef", "__name__", "__file__"})
    return sorted(n for n in loaded - known if not n.startswith("__"))


def _stub_undefined_names(code: str) -> str:
    """Bind every unresolvable name to a placeholder before the render.

    `from manim import *` means most names resolve, so whatever is left is
    genuinely invented. Stubbing beats failing: the alternative is the whole
    animation disappearing and the lesson quietly showing a static slide in
    its place.
    """
    missing = _undefined_names(code)
    if not missing:
        return code
    logger.warning(
        f"Generated Manim code references {len(missing)} undefined name(s), "
        f"stubbing to keep the render alive: {', '.join(missing[:10])}"
    )

    # What the name is used FOR decides what it should become. `CIRCLE` in
    # `CIRCLE.get_center()` needs an object; `LIGHTBLUE` in `color=LIGHTBLUE`
    # needs a colour, and handing Manim a placeholder object there just
    # trades a NameError for a TypeError. Anything touched with an attribute
    # or called is an object; everything else is a bare constant.
    object_like: Set[str] = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                object_like.add(node.value.id)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                object_like.add(node.func.id)
    except SyntaxError:
        object_like = set(missing)

    stubs = "\n".join(
        f'{name} = _MissingRef("{name}")' if name in object_like else f"{name} = WHITE"
        for name in missing
    )
    # Carries its own class definition rather than relying on the compat
    # shim having been injected first. Re-running the pipeline over code
    # that already contains a shim skips re-injection, and this block would
    # then reference a _MissingRef that was never defined - swapping one
    # NameError for another.
    prelude = "" if "class _MissingRef" in code else _MISSING_REF_CLASS
    block = (
        f"\n# --- injected: names used but never defined ---{prelude}\n{stubs}\n"
    )

    lines = code.splitlines()
    # After the shim (which defines _MissingRef) but before the class that
    # uses these names.
    for i, line in enumerate(lines):
        if line.startswith("class ") and "Scene" in line:
            lines.insert(i, block)
            return "\n".join(lines)
    return code + block


_LAYOUT_HELPERS = '''
    def _run_scene(self, _name):
        """Run one scene method, surviving a crash inside it.

        Manim aborts the whole render on any exception, so a single bad
        call in scene 4 of 6 used to cost every scene - and the lesson then
        quietly showed a static slide where the animation should be. Losing
        one scene is a far better failure than losing the video.
        """
        try:
            getattr(self, _name)()
        except Exception as _exc:
            print(f"[scoratis] scene {_name} failed, skipping: "
                  f"{type(_exc).__name__}: {_exc}")
            # Whatever it managed to draw before dying stays on stage;
            # the _clear_screen() that follows this call wipes it.

    def _clear_screen(self):
        """Injected - fade out everything the previous scene left on stage so
        the next one starts on a blank frame. No-ops on an empty stage, where
        FadeOut() would otherwise raise."""
        _mobs = list(self.mobjects)
        if _mobs:
            self.play(*[FadeOut(_m) for _m in _mobs], run_time=0.4)
            self.clear()

    def _bbox(self, m):
        return (m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1])

    def _overlaps(self, a, b):
        al, ar, ab, at = self._bbox(a)
        bl, br, bb, bt = self._bbox(b)
        return al < br and bl < ar and ab < bt and bb < at

    def _inside(self, outer, inner):
        ol, orr, ob, ot = self._bbox(outer)
        il, ir, ib, it = self._bbox(inner)
        return ol <= il and ir <= orr and ob <= ib and it <= ot

    def _is_box(self, m):
        """A small closed shape used as a container - a label centred in one
        of these is deliberate and must not be moved. Deliberately excludes
        VGroup/NumberLine/Axes: a caption landing inside one of THOSE
        bounding boxes is an accident (it collides with the ticks and
        numbers inside), not an intentional label."""
        try:
            return isinstance(m, (Rectangle, RoundedRectangle, Square, Circle, Ellipse, Polygon))
        except NameError:
            return False

    def _is_caption(self, m):
        """True for a pure block of text - a bare label, or a group whose
        every leaf is a label (a legend, a bullet list).

        Checking `isinstance(m, Text)` alone missed the common case: the
        model builds its bullet lists and legends with
        VGroup(Text, Text, ...).arrange(DOWN), so `self.mobjects` holds a
        VGroup, not Text, and the whole block sailed straight through the
        old filter and over the diagram beside it.

        A group mixing text WITH geometry (a labelled box, an annotated
        arrow) is deliberately not a caption: its parts are positioned
        relative to each other, and nudging it apart would break the very
        thing it draws.
        """
        try:
            _types = (Text, MathTex, Tex)
        except NameError:
            return False
        if isinstance(m, _types):
            return True
        _subs = getattr(m, "submobjects", None) or []
        if not _subs:
            return False
        return all(self._is_caption(_c) for _c in _subs)

    def _resolve_overlaps(self):
        """Nudge captions off anything they collide with, along whichever
        axis needs the smaller move.

        Pushing purely vertically (what this used to do) is the wrong
        instinct for a caption sitting beside a diagram: the short sideways
        step that clears it gets passed over in favour of a long slide up or
        down, which just lands the caption on the title instead.
        """
        _labels = [m for m in self.mobjects if self._is_caption(m)]
        if not _labels:
            return
        _others = [m for m in self.mobjects if not self._is_caption(m)]
        try:
            _hw = config.frame_width / 2 - 0.35
            _hh = config.frame_height / 2 - 0.35
        except Exception:
            _hw, _hh = 7.0, 3.9

        for _ in range(8):
            _moved = False
            # Labels vs everything else, then labels vs each other - two
            # captions colliding reads just as broken as a caption on a box.
            for _lab in _labels:
                for _sh in _others + [x for x in _labels if x is not _lab]:
                    if not self._overlaps(_lab, _sh):
                        continue
                    if self._is_box(_sh) and self._inside(_sh, _lab):
                        continue  # deliberate label-in-box
                    _al, _ar, _ab, _at = self._bbox(_lab)
                    _bl, _br, _bb, _bt = self._bbox(_sh)
                    _pad = 0.22
                    # How far to push along each axis to break contact,
                    # signed towards the nearer way out.
                    _dx = (_br - _al + _pad) if (_br - _al) < (_ar - _bl) \
                        else -(_ar - _bl + _pad)
                    _dy = (_bt - _ab + _pad) if (_bt - _ab) < (_at - _bb) \
                        else -(_at - _bb + _pad)
                    # Cheaper axis first, but never off the edge of the
                    # frame - a caption pushed out of shot is worse than a
                    # caption that still touches something.
                    _cands = [(_dx, 0.0), (0.0, _dy)] if abs(_dx) <= abs(_dy) \
                        else [(0.0, _dy), (_dx, 0.0)]
                    _placed = False
                    for _mx, _my in _cands:
                        if (_al + _mx >= -_hw and _ar + _mx <= _hw
                                and _ab + _my >= -_hh and _at + _my <= _hh):
                            _lab.shift(RIGHT * _mx + UP * _my)
                            _moved = True
                            _placed = True
                            break
                    if _placed or self._is_caption(_sh):
                        continue
                    # The caption has nowhere to go: a full-width bullet
                    # block spans the frame, so every shift takes it off
                    # screen and it was simply left lying across the
                    # diagram. Move the DIAGRAM out from under it instead -
                    # it is the smaller of the two, and shifting the whole
                    # group keeps its internal composition intact.
                    _shifted = False
                    for _mx, _my in [(-_a, -_b) for _a, _b in _cands]:
                        if (_bl + _mx >= -_hw and _br + _mx <= _hw
                                and _bb + _my >= -_hh and _bt + _my <= _hh):
                            _sh.shift(RIGHT * _mx + UP * _my)
                            _moved = True
                            _shifted = True
                            break
                    if _shifted:
                        continue
                    # Neither can move: the shape is nearly as big as the
                    # frame, so there is no empty space to move anything
                    # into - a title laid over a circle that fills the shot.
                    # Make room by shrinking the shape a little. Bounded by
                    # the outer loop, and only when the shape is clearly the
                    # bigger of the two, so a caption never shrinks a
                    # diagram it merely brushes against.
                    if (_sh.width * _sh.height) > 4.0 * max(
                            _lab.width * _lab.height, 0.01):
                        _sh.scale(0.9)
                        _moved = True
            if not _moved:
                break

    def _separate_labels_from_shapes(self):
        """Move a single line of a caption off a shape it lands on.

        _resolve_overlaps moves a caption as a WHOLE and gives up when the
        whole block has nowhere to go - the normal case for a full-width
        bullet list. _separate_labels only handles text meeting other text.
        One line of a list struck through by a circle fell between the two,
        and looked exactly like that: a single bullet crossed out by a
        diagram while every other line sat clear.

        Only leaves of pure captions move. A label inside a mixed group
        belongs to the shape it annotates, and moving it independently
        would tear the label off its own arrow.
        """
        _shapes = [m for m in self.mobjects if not self._is_caption(m)]
        if not _shapes:
            return
        _leaves = []
        for _m in self.mobjects:
            if self._is_caption(_m):
                _leaves.extend(self._text_leaves(_m))
        if not _leaves:
            return
        try:
            _hw = config.frame_width / 2 - 0.35
            _hh = config.frame_height / 2 - 0.35
        except Exception:
            _hw, _hh = 7.0, 3.9

        for _ in range(6):
            _moved = False
            for _lab in _leaves:
                for _sh in _shapes:
                    if not self._overlaps(_lab, _sh):
                        continue
                    if self._is_box(_sh) and self._inside(_sh, _lab):
                        continue  # deliberate label-in-box
                    _al, _ar, _ab, _at = self._bbox(_lab)
                    _bl, _br, _bb, _bt = self._bbox(_sh)
                    _pad = 0.20
                    _dx = (_br - _al + _pad) if (_br - _al) < (_ar - _bl) \
                        else -(_ar - _bl + _pad)
                    _dy = (_bt - _ab + _pad) if (_bt - _ab) < (_at - _bb) \
                        else -(_at - _bb + _pad)
                    _cands = [(_dx, 0.0), (0.0, _dy)] if abs(_dx) <= abs(_dy) \
                        else [(0.0, _dy), (_dx, 0.0)]
                    for _mx, _my in _cands:
                        if (_al + _mx >= -_hw and _ar + _mx <= _hw
                                and _ab + _my >= -_hh and _at + _my <= _hh):
                            _lab.shift(RIGHT * _mx + UP * _my)
                            _moved = True
                            break
            if not _moved:
                break

    def _fit_to_frame(self):
        """Pull anything hanging off the edge back into the visible frame.

        Manim renders only x in [-frame_width/2, +frame_width/2] and y in
        [-frame_height/2, +frame_height/2]; anything outside is simply not in
        the video. The model routinely places wide diagrams and long titles
        past those bounds, so the viewer sees text clipped mid-word and graphs
        running off the side. Scale down what is too big, then shift what is
        merely misplaced.
        """
        try:
            half_w = config.frame_width / 2 - 0.35
            half_h = config.frame_height / 2 - 0.35
        except Exception:
            return

        for _m in list(self.mobjects):
            try:
                if _m.width <= 0 or _m.height <= 0:
                    continue
                # 1. Too large to ever fit -> scale about its own centre.
                _s = min((2 * half_w) / _m.width, (2 * half_h) / _m.height, 1.0)
                if _s < 0.999:
                    _m.scale(_s)
                # 2. Now shift it fully inside.
                _dx = _dy = 0.0
                if _m.get_left()[0] < -half_w:
                    _dx = -half_w - _m.get_left()[0]
                elif _m.get_right()[0] > half_w:
                    _dx = half_w - _m.get_right()[0]
                if _m.get_bottom()[1] < -half_h:
                    _dy = -half_h - _m.get_bottom()[1]
                elif _m.get_top()[1] > half_h:
                    _dy = half_h - _m.get_top()[1]
                if abs(_dx) > 0.01 or abs(_dy) > 0.01:
                    _m.shift(RIGHT * _dx + UP * _dy)
            except Exception:
                continue

    def _text_leaves(self, m):
        try:
            _types = (Text, MathTex, Tex)
        except NameError:
            return []
        if isinstance(m, _types):
            return [m]
        _out = []
        for _c in getattr(m, "submobjects", None) or []:
            _out.extend(self._text_leaves(_c))
        return _out

    def _separate_labels(self):
        """Push apart two pieces of text that landed on each other, wherever
        they sit in the hierarchy.

        _resolve_overlaps only ever moves whole captions, so two labels that
        each belong to a mixed group - the 'F = Force' annotation on one
        arrow and the 'a = Acceleration' one on the arrow beside it - could
        sit directly on top of each other with neither eligible to move.
        Nudging the leaves themselves, half the distance each, keeps every
        label near the thing it annotates while making both readable.
        """
        _leaves = []
        for _m in self.mobjects:
            _leaves.extend(self._text_leaves(_m))
        if len(_leaves) < 2:
            return
        for _ in range(6):
            _moved = False
            for _i in range(len(_leaves)):
                for _j in range(_i + 1, len(_leaves)):
                    _a, _b = _leaves[_i], _leaves[_j]
                    if not self._overlaps(_a, _b):
                        continue
                    _al, _ar, _ab, _at = self._bbox(_a)
                    _bl, _br, _bb, _bt = self._bbox(_b)
                    _pad = 0.18
                    _dx = (_br - _al + _pad) if (_br - _al) < (_ar - _bl) \
                        else -(_ar - _bl + _pad)
                    _dy = (_bt - _ab + _pad) if (_bt - _ab) < (_at - _bb) \
                        else -(_at - _bb + _pad)
                    if abs(_dx) <= abs(_dy):
                        _a.shift(RIGHT * (_dx / 2.0))
                        _b.shift(LEFT * (_dx / 2.0))
                    else:
                        _a.shift(UP * (_dy / 2.0))
                        _b.shift(DOWN * (_dy / 2.0))
                    _moved = True
            if not _moved:
                break

    def _relayout(self):
        # Order matters: fit first (scaling/shifting changes geometry), then
        # de-overlap the corrected positions. Separating individual labels
        # can push one back over an edge, so fit again to finish.
        self._fit_to_frame()
        self._resolve_overlaps()
        # Shapes first - those displacements are the larger ones - then
        # tidy up any text-on-text the shape moves created.
        self._separate_labels_from_shapes()
        self._separate_labels()
        self._fit_to_frame()

    def wait(self, *args, **kwargs):
        self._relayout()
        return super().wait(*args, **kwargs)

    def _preplace(self, args):
        """Lay out what an animation is about to reveal, BEFORE it plays.

        Correcting only after play() returns leaves the collision on screen
        for the whole animation - a `FadeIn(..., run_time=3)` means three
        seconds of a diagram sitting on top of the text it landed on, which
        is most of a short scene. Positioning the incoming mobject up front
        means it fades in already clear of everything else.
        """
        _added = []
        try:
            for _a in args:
                _m = getattr(_a, "mobject", None)
                if _m is None:
                    continue
                # `in` on a Mobject list is an identity check here; anything
                # already on stage is being transformed, not introduced, and
                # its placement is the author's business.
                if not any(_m is _x for _x in self.mobjects):
                    _added.append(_m)
            if not _added:
                return
            self.add(*_added)
            self._relayout()
            # Hand them back to the animation to add for real, so play()
            # behaves exactly as it would have.
            self.remove(*_added)
        except Exception:
            return

    def play(self, *args, **kwargs):
        # Hooking wait() alone left a hole: whatever the LAST play() of a
        # scene puts on screen is never checked, because no wait() follows
        # it. That is exactly where collisions survived - a caption written
        # in at the end sat on top of one already there, and stayed there
        # for the rest of the shot. Correcting after the animation settles
        # costs a single-frame nudge and catches every one of those.
        self._preplace(args)
        _r = super().play(*args, **kwargs)
        self._relayout()
        return _r
'''


def _enforce_scene_isolation(code: str) -> str:
    """Guarantee each scene method starts from a blank frame, safely.

    The generated construct() is a flat list of scene calls:

        def construct(self):
            self.scene_1()
            self.scene_2()

    Manim keeps every mobject on stage until something explicitly removes
    it, so unless each method fades out what it added, scene_2 renders ON
    TOP of scene_1 - the title, labels and diagrams from every scene all
    pile up in one unreadable frame.

    Two transforms, both needed:

    1. Rewrite every whole-stage fade (`self.play(FadeOut(*self.mobjects))`
       and the list-comprehension spelling) into `self._clear_screen()`.
       The model emits these unguarded, including at the TOP of the first
       scene where the stage is still empty - and `FadeOut()` with zero
       mobjects raises "At least one mobject must be passed", failing the
       whole render. The helper guards on `self.mobjects` first.

    2. Insert `self._clear_screen()` between consecutive scene calls, so
       isolation holds even when the model forgets to clean up at all.

    The helper is appended only if something references it and it isn't
    already defined, so this is safe to run repeatedly.
    """
    # 1. Make every whole-stage fade empty-safe.
    code = _FULL_STAGE_FADE_RE.sub(lambda m: f"{m.group(1)}self._clear_screen()", code)

    # 2. Separate consecutive scenes.
    if len(_SCENE_CALL_RE.findall(code)) >= 2:
        def _insert_clear(match: "re.Match") -> str:
            indent, name = match.group(1), match.group(2)
            # Route through _run_scene so one scene raising does not destroy
            # the entire video. Before this, a single bad call anywhere in a
            # six-scene file - a ValueError from arrange_in_grid, say - lost
            # all six, and the lesson silently showed a static slide instead.
            return f'{indent}self._run_scene("{name}")\n{indent}self._clear_screen()'

        code = _SCENE_CALL_RE.sub(_insert_clear, code)

    # 3. Always attach the layout helpers. Even a scene that never needs a
    #    cleanup still benefits from the wait() override, which de-clutters
    #    overlapping captions before each held frame.
    if "def _clear_screen" not in code and "class ManimScene(Scene):" in code:
        code = code.rstrip() + "\n" + _LAYOUT_HELPERS

    return code


ENHANCED_MANIM_PROMPT = """You are an expert Manim animator creating professional educational videos.
Generate a complete, production-quality Manim animation based on this script:

{script_json}
{retry_feedback_section}

## CRITICAL REQUIREMENTS:

### 1. CODE STRUCTURE
{code_structure}

### 2. SCENE ISOLATION (MOST IMPORTANT - GET THIS RIGHT)
Manim never removes a mobject on its own: anything you draw stays on screen
until you explicitly fade or remove it. If a scene method ends without
cleaning up, the NEXT scene draws directly on top of it and the frame turns
into unreadable overlapping text.

- EVERY scene method MUST end by removing everything it added:
  `self.play(FadeOut(*self.mobjects))`
- Do NOT put that call at the START of a method. The stage is already blank
  when a scene begins, and `FadeOut()` with nothing on stage raises
  "At least one mobject must be passed" and fails the whole render.
  Clean up at the END only.
- Within a single scene, never place two elements at the same position.
  Anchor every element explicitly with `.to_edge()`, `.next_to()`, `.shift()`
  or `.move_to()`. Two bare `Text(...)` objects with no positioning both land
  dead-center and overlap.
- Keep a title at `.to_edge(UP)` and body content below it - never both at
  the center.

### 3. EVERYTHING MUST FIT THE FRAME (CRITICAL)

The camera shows ONLY x from -7.1 to +7.1 and y from -4.0 to +4.0. Anything
outside is invisible - text gets clipped mid-word, graphs run off the side.

- Keep every element within x in [-6.5, 6.5] and y in [-3.5, 3.5].
- A full-width title must be `font_size<=44` and `.to_edge(UP)`. Long titles
  need a smaller size, not more width.
- Axes/graphs: use `x_length<=10` and `y_length<=5.5`, then `.move_to(ORIGIN)`
  or `.to_edge(DOWN)`. Never let a plotted region extend past the axes.
- After building any wide group, constrain it explicitly:
  `group.scale_to_fit_width(12)` and `group.move_to(ORIGIN)`.
- Never place a label at an absolute position you have not checked; anchor it
  to the object it describes with `.next_to(obj, DIRECTION, buff=0.3)`.

If a scene has both a title and a diagram, the diagram gets the middle of the
frame and the title sits at the top edge - they must not occupy the same band.

### 4. VISUAL DENSITY (8-10 elements per major concept)
- Use VGroup for organizing related elements
- Layer elements for visual depth
- Include labels, annotations, and arrows
- Show relationships with connecting lines
- Add step numbers for processes (①②③)
- No photo/image/icon asset files exist in this environment: never call
  ImageMobject, SVGMobject, or reference any external file. Build every
  visual - including anything the script describes as an "image" - out of
  native Manim primitives only (Text, MathTex, Circle, Rectangle, Arrow,
  Line, Polygon, VGroup, etc.)
- Never reference a variable inside its own definition - e.g. do NOT write
  `group = VGroup(a, b, Text("x").next_to(group, UP))`, since `group`
  doesn't exist yet on that line and this raises UnboundLocalError. Build
  every sub-element as its own variable first (positioning each with
  `.next_to()`/`.shift()` against the other sub-elements, not the group),
  then combine them into the VGroup as the last step.

### 5. THIS IS AN ANIMATION, NOT A SLIDESHOW

The whole reason this is a video and not a slide is MOTION. If a frame could
be a screenshot, it does not belong here.

Every scene must show something CHANGING:
- values moving, updating, or being recomputed step by step
- a pointer/arrow/highlight travelling across a structure
- a shape being built up piece by piece, or transformed into another
- a graph being drawn, a region filling in, a curve being traced
- a before state visibly BECOMING an after state (use Transform)

Concretely, per scene: at least 4-6 separate `self.play(...)` calls that each
advance the idea, with `self.wait()` between them so the viewer can follow.
A scene that writes a title, shows a bullet list and waits is a FAILURE -
that is a slide, and the lesson already has slides.

Walk through worked examples on screen: show the actual numbers changing at
each step rather than stating the result. If a value updates, animate the
update so the viewer sees WHICH value changed.

### 6. ANIMATION TIMING
- Title animations: 2-3 seconds with Write()
- Concept introductions: 3-4 seconds with Create()/FadeIn()
- Diagram building: 2-3 seconds per stage
- Key points: 2 second pause with Indicate()
- Transitions: 1 second with FadeOut()/FadeIn()
- Use self.wait(2) after important information
- ONLY use these animation classes - every one of them is a real Manim
  class, nothing else is guaranteed to exist: Write, Create, FadeIn,
  FadeOut, GrowFromCenter, Indicate, DrawBorderThenFill, Transform. Do not
  invent plausible-sounding animation names (e.g. PopUp, SlideIn, ZoomIn,
  Bounce) - they don't exist in Manim and will crash the render with a
  NameError. If the script's "animation" hint isn't in this list, substitute
  FadeIn.

### 7. PROFESSIONAL STYLING
- Title: font_size=48, color=BLUE
- Headers: font_size=36, color=YELLOW
- Body text: font_size=28, color=WHITE
- Key terms: color=GREEN with Indicate()
- Formulas: MathTex with color=GOLD
- Minimum 24pt for all text

### 8. VISUAL HIERARCHY
- Primary concept: Center, large, bold color
- Supporting details: Positioned around primary
- Annotations: Smaller, positioned with arrows
- Use buff=0.5 for consistent spacing

### 9. EDUCATIONAL BEST PRACTICES
- Build complexity gradually (simple → complex)
- Show cause → effect with animated arrows
- Use before/after comparisons
- Highlight key terms when mentioned in narration
- Include visual metaphors for abstract concepts

### 10. COLOR PALETTE
- Primary (concepts): BLUE, BLUE_C, BLUE_D
- Highlights: YELLOW, GOLD
- Success/Growth: GREEN, GREEN_C
- Energy/Important: RED, ORANGE
- Neutral: WHITE, GRAY

OUTPUT: Return ONLY valid Python code starting with 'from manim import *'
No explanations, no markdown blocks, just code."""

COMPLEXITY_ANALYSIS_PROMPT = """Analyze the complexity of this educational topic for video generation:

TOPIC: {topic}
CONTEXT: {context}

Rate the complexity as one of:
- "simple": Single concept, definition, or fact (e.g., "What is gravity?")
- "moderate": Process, relationship, or formula (e.g., "How photosynthesis works")
- "complex": Multi-step process, proof, or system (e.g., "Derive the quadratic formula")

Also identify:
- Key visual elements needed
- Recommended visualization type
- Suggested duration

OUTPUT FORMAT (JSON only):
{{
  "complexity": "simple|moderate|complex",
  "recommended_duration": 60,
  "visual_elements": ["element1", "element2"],
  "visualization_type": "diagram|process|equation|comparison|timeline",
  "reasoning": "Brief explanation"
}}"""


class EnhancedVideoGenerator:
    """
    Enhanced video generator for API mode.
    Produces longer, more detailed educational videos with:
    - Multi-scene structure (5 scenes)
    - 8-10 visual elements per concept
    - 60-120 second duration
    - Educational pacing (2.0-2.2 words/sec)

    Automatically activates when API key is configured.
    Falls back to quick generation for local Ollama.
    """

    # Duration tiers based on complexity
    DURATION_SIMPLE = 60      # 1 minute for simple concepts
    DURATION_MODERATE = 90    # 1.5 minutes for moderate
    DURATION_COMPLEX = 120    # 2 minutes for complex topics

    # Duration used when no provider is configured and only the minimal
    # placeholder path is reachable.
    DURATION_MINIMAL = 25

    def __init__(self):
        self._use_api = False
        self._llm_service = None
        self._initialize()

    def _initialize(self):
        """Initialize and check for API availability"""
        try:
            from llm_service import llm_service
            self._llm_service = llm_service
            config = llm_service.get_current_config()

            if config and llm_service.has_api_key():
                self._use_api = True
                logger.info(f"EnhancedVideoGenerator: API mode enabled ({config.get('provider')})")
                return

            logger.warning("EnhancedVideoGenerator: No configured provider/API key available")
        except Exception as e:
            logger.warning(f"EnhancedVideoGenerator init error: {e}")

    @property
    def is_enhanced_mode(self) -> bool:
        """Check if enhanced mode (API) is available"""
        return self._use_api

    async def analyze_complexity(self, topic: str, context: dict = None) -> dict:
        """
        Analyze topic complexity to determine optimal duration and visual approach.
        """
        if not self._use_api:
            return {
                "complexity": "simple",
                "recommended_duration": self.DURATION_MINIMAL,
                "visual_elements": [],
                "visualization_type": "diagram"
            }

        try:
            prompt = COMPLEXITY_ANALYSIS_PROMPT.format(
                topic=topic,
                context=json.dumps(context) if context else "{}"
            )

            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are a curriculum designer. Analyze educational content complexity. Output only JSON."
            )

            # Parse JSON response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            return json.loads(response)
        except Exception as e:
            logger.warning(f"Complexity analysis failed: {e}")
            return {
                "complexity": "moderate",
                "recommended_duration": self.DURATION_MODERATE,
                "visual_elements": [],
                "visualization_type": "diagram"
            }

    def get_optimal_duration(self, complexity: str) -> int:
        """Get optimal duration based on complexity"""
        if not self._use_api:
            return self.DURATION_MINIMAL

        duration_map = {
            "simple": self.DURATION_SIMPLE,
            "moderate": self.DURATION_MODERATE,
            "complex": self.DURATION_COMPLEX
        }
        return duration_map.get(complexity, self.DURATION_MODERATE)

    async def generate_script(self, topic: str, duration: int, context: dict = None) -> dict:
        """
        Phase 1: Generate structured video script with scene breakdown.
        """
        if not self._use_api:
            raise RuntimeError(
                "No LLM provider configured - add a provider and API key in AI Settings."
            )

        try:
            prompt = SCRIPT_PLANNING_PROMPT.format(
                topic=topic,
                duration=duration,
                scene_structure=_script_scene_structure(duration),
            )

            messages = [{"role": "user", "content": prompt}]
            # Default max_tokens (2048) routinely truncates a full 5-scene
            # script mid-JSON-string - confirmed via "Unterminated string"
            # JSON-parse failures in production. A structured multi-scene
            # script with visuals/narration per scene genuinely needs more
            # headroom than a typical chat turn.
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are an expert educational video scriptwriter. Output only valid JSON.",
                max_tokens=4096,
            )

            # Clean and parse JSON
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            script = json.loads(response)
            logger.info(f"EnhancedVideoGenerator: Generated script with {len(script.get('scenes', []))} scenes")
            return script

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {
                "title": topic,
                "total_duration": duration,
                "scenes": [],
                "key_concepts": [topic],
                "visual_style": "diagram"
            }

    async def generate_manim_code(
        self,
        script: dict,
        topic: str,
        retry_feedback: Optional[dict] = None,
    ) -> str:
        """
        Phase 2: Generate Manim animation code from script.

        retry_feedback: {"error": str, "previous_code": str} from a prior
        failed render attempt on this same job (see tasks/video_tasks.py) -
        when present, the regeneration prompt includes the exact previous
        mistake so the model can fix that specific issue instead of a blind
        reroll that's just as likely to hit a different bug.
        """
        if not self._use_api or not script.get("scenes"):
            # Single-scene path: no structured script to expand, so fall back
            # to the simpler prompt. Still API-backed - SmartManimClient
            # raises if no provider is configured.
            client = SmartManimClient()
            return client.generate_manim_code(
                topic=topic,
                duration=script.get("total_duration", 25)
            )

        try:
            retry_section = ""
            if retry_feedback and retry_feedback.get("error"):
                retry_section = RETRY_FEEDBACK_TEMPLATE.format(
                    previous_code=retry_feedback.get("previous_code", "")[:3000],
                    error=retry_feedback["error"][:1500],
                )

            prompt = ENHANCED_MANIM_PROMPT.format(
                script_json=json.dumps(script, indent=2),
                retry_feedback_section=retry_section,
                code_structure=_manim_code_structure(script),
            )

            messages = [{"role": "user", "content": prompt}]
            # Default max_tokens (2048) was nowhere near enough for a full
            # 5-scene Manim implementation (8-10 visual elements/scene,
            # per ENHANCED_MANIM_PROMPT) - confirmed via repeated
            # "SyntaxError: '(' was never closed" failures where the
            # generated code cuts off mid-expression near the end of the
            # captured text, the classic signature of hitting an output
            # token limit rather than the model making a logic mistake.
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are an expert Manim animator. Generate only valid Python code.",
                max_tokens=8192,
            )

            # Clean code
            code = self._clean_manim_code(response)
            code = self._validate_and_fix_code(code, topic)

            logger.info(f"EnhancedVideoGenerator: Generated {len(code)} chars of Manim code")
            return code

        except Exception as e:
            logger.error(f"Manim code generation failed: {e}")
            return self._generate_fallback_code(topic, script.get("total_duration", 60))

    async def generate_enhanced_video(
        self,
        topic: str,
        context: dict = None,
        retry_feedback: Optional[dict] = None,
    ) -> dict:
        """
        Full enhanced video generation pipeline.
        Returns script, manim code, and metadata.
        """
        # Phase 0: Duration
        # If the caller already knows how long this should be - the agent's
        # own generate_video tool call and the (older) video_analyzer_service
        # auto-generation path both set context["duration_suggestion"] - use
        # that directly and skip analyze_complexity()'s LLM round trip
        # entirely. Previously this was ALWAYS overridden by
        # get_optimal_duration()'s 60/90/120s tiers regardless of what was
        # actually requested, silently turning every "20 second" auto-video
        # into a 60-120s one: the single biggest driver of both slow renders
        # and LLM code-gen mistakes (more requested duration -> more scenes
        # -> more surface area for the model to get wrong).
        requested_duration = (context or {}).get("duration_suggestion")
        if requested_duration:
            # Upper bound raised from 30s: a 30s cap forced every lesson
            # animation into a title card plus one idea, which is why they
            # felt scarce. Complexity now scales with the request instead of
            # being pinned to "simple" - that flag drives how many scenes the
            # script planner writes, so pinning it was the other half of the
            # same problem.
            duration = max(10, min(180, int(requested_duration)))
            if duration >= 90:
                complexity = "complex"
            elif duration >= 45:
                complexity = "moderate"
            else:
                complexity = "simple"
        else:
            complexity_info = await self.analyze_complexity(topic, context)
            complexity = complexity_info.get("complexity", "moderate")
            duration = self.get_optimal_duration(complexity)

        logger.info(f"EnhancedVideoGenerator: {topic} -> {complexity} complexity, {duration}s duration")

        # Phase 1: Generate script
        script = await self.generate_script(topic, duration, context)

        # Phase 2: Generate Manim code
        manim_code = await self.generate_manim_code(script, topic, retry_feedback=retry_feedback)

        return {
            "topic": topic,
            "complexity": complexity,
            "duration": duration,
            "script": script,
            "manim_code": manim_code,
            "enhanced_mode": self._use_api,
            "visual_elements_count": sum(
                len(s.get("visuals", [])) for s in script.get("scenes", [])
            )
        }

    def _clean_manim_code(self, code: str) -> str:
        """Clean up generated Manim code"""
        # Remove markdown code blocks
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0]

        # Ensure proper imports
        if not code.strip().startswith("from manim"):
            if "from manim" in code:
                code = code[code.find("from manim"):]
            else:
                code = "from manim import *\n\n" + code

        return code.strip()

    # Class names from the original (non-Community) Manim that the LLM
    # occasionally reaches for out of training-data habit - real Manim
    # classes, just not in the Manim Community fork this app actually runs,
    # so they crash with NameError instead of getting caught by any prompt
    # instruction telling it not to "invent" names (these aren't invented,
    # they're just from the wrong Manim variant). ENHANCED_MANIM_PROMPT
    # already tells the model to only use the modern names - this is a
    # mechanical backstop for when that instruction isn't followed, since
    # prompt compliance alone isn't 100% reliable.
    _DEPRECATED_MANIM_ALIASES = {
        "ShowCreation": "Create",
        "TextMobject": "Text",
        "TexMobject": "MathTex",
    }

    def _validate_and_fix_code(self, code: str, topic: str) -> str:
        """Validate and fix common issues in generated code"""
        import re

        # Ensure ManimScene class exists
        if "class ManimScene" not in code:
            match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', code)
            if match:
                old_name = match.group(1)
                code = code.replace(f"class {old_name}(Scene)", "class ManimScene(Scene)")

        # Ensure construct method exists
        if "def construct(self)" not in code and "def construct(" not in code:
            code = code.replace(
                "class ManimScene(Scene):",
                "class ManimScene(Scene):\n    def construct(self):\n        pass"
            )

        # Swap known deprecated/renamed class names for their modern
        # Manim Community equivalents - word-boundary match so this can't
        # clobber a substring inside an unrelated identifier.
        for old_name, new_name in self._DEPRECATED_MANIM_ALIASES.items():
            code = re.sub(rf'\b{old_name}\b', new_name, code)

        # Stop each scene from drawing on top of the previous one.
        code = _inject_manim_compat(code)
        code = _enforce_scene_isolation(code)
        code = _stub_undefined_names(code)

        return code

    def _generate_fallback_code(self, topic: str, duration: int) -> str:
        """Generate minimal working Manim animation as fallback"""
        return f'''from manim import *

class ManimScene(Scene):
    def construct(self):
        # Title
        title = Text("{topic[:40]}", font_size=42, color=BLUE)
        self.play(Write(title), run_time=2)
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Main content placeholder
        content = Text("Visual explanation", font_size=32, color=WHITE)
        self.play(FadeIn(content))
        self.wait({max(2, duration - 8)})

        # Outro
        self.play(FadeOut(content), FadeOut(title))
        self.wait(1)
'''


# Global enhanced video generator
_enhanced_generator: Optional[EnhancedVideoGenerator] = None


def get_enhanced_generator() -> EnhancedVideoGenerator:
    """Get or create the enhanced video generator"""
    global _enhanced_generator
    if _enhanced_generator is None:
        _enhanced_generator = EnhancedVideoGenerator()
    return _enhanced_generator


# Global LLM clients for video generation (initialized lazily)
# Uses SmartVideoClient and SmartManimClient for automatic API/local fallback
_video_llm_client: Optional[SmartVideoClient] = None
_manim_code_client: Optional[SmartManimClient] = None


def get_video_llm_client() -> SmartVideoClient:
    """
    Get or create the video LLM client (for narration).
    Automatically uses API if configured, otherwise falls back to local Ollama.
    """
    global _video_llm_client
    if _video_llm_client is None:
        _video_llm_client = SmartVideoClient()
    return _video_llm_client


def get_manim_code_client() -> SmartManimClient:
    """
    Get or create the Manim code generation client.
    Automatically uses API if configured, otherwise falls back to local Ollama.
    """
    global _manim_code_client
    if _manim_code_client is None:
        _manim_code_client = SmartManimClient()
    return _manim_code_client


def reset_video_clients():
    """Reset video clients to pick up new LLM configuration"""
    global _video_llm_client, _manim_code_client, _enhanced_generator
    _video_llm_client = None
    _manim_code_client = None
    _enhanced_generator = None
    logger.info("Video clients reset - will reinitialize with current LLM config")

class GenerationStage(str, Enum):
    CONTENT = "content"
    NARRATION = "narration"
    ANIMATION = "animation"
    MERGE = "merge"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class GenerationTask:
    task_id: str
    topic: str
    quality: str
    duration: int
    status: str = "pending"
    stage: str = "content"
    progress: int = 0
    message: str = ""
    video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    logs: List[str] = field(default_factory=list)

class VideoGenerationService:
    """Service for generating educational videos using maestro-studio"""

    def __init__(self):
        self.tasks: Dict[str, GenerationTask] = {}
        self.output_dir = Path("generated_videos")
        self.output_dir.mkdir(exist_ok=True)
        self.maestro_available = self._check_maestro()

    def _check_maestro(self) -> bool:
        """Check if maestro-studio is available"""
        try:
            if not MAESTRO_PATH.exists():
                return False
            # Check for key files
            orchestrator_path = MAESTRO_PATH / "src" / "video" / "orchestrator.py"
            return orchestrator_path.exists()
        except Exception:
            return False

    async def detect_visuals_ai(self, topic: str, context: dict = None) -> List[str]:
        """
        Use AI to detect what visual elements should be used for a topic.
        No hardcoded rules - completely AI-driven.
        """
        llm_client = get_video_llm_client()

        # Build context info
        context_info = ""
        if context:
            if context.get("key_concepts"):
                context_info += f"\nKey concepts: {', '.join(context['key_concepts'][:5])}"
            if context.get("visualization_type"):
                context_info += f"\nVisualization type: {context['visualization_type']}"
            if context.get("animation_suggestions"):
                context_info += f"\nSuggested animations: {', '.join(context['animation_suggestions'][:3])}"

        prompt = f"""Analyze this educational topic and determine the best visual elements for a Manim animation.

Topic: {topic}
{context_info}

What visual elements should be included in an educational animation about this topic?

Think about:
1. What objects/shapes need to be shown?
2. What transformations or movements would help explain the concept?
3. What text labels or annotations are needed?
4. What color schemes would be appropriate?

Return a JSON array of 3-5 visual element descriptions that should be animated:
["visual element 1", "visual element 2", "visual element 3"]

Each element should be specific and actionable for animation (e.g., "animated bar chart showing growth", "rotating 3D molecule structure", "step-by-step process arrows").

Return ONLY the JSON array, no other text."""

        try:
            response = llm_client.generate(prompt, max_tokens=500, temperature=0.7)
            # Parse JSON array
            import json
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            clean_response = clean_response.strip().strip("```")

            # Find the JSON array
            start = clean_response.find('[')
            end = clean_response.rfind(']')
            if start != -1 and end != -1:
                visuals = json.loads(clean_response[start:end+1])
                return visuals[:5]
        except Exception as e:
            logger.warning(f"AI visual detection failed: {e}")

        # Minimal fallback - let Manim code generation handle specifics
        return [f"Visual explanation of {topic}", "Animated text labels", "Smooth transitions"]

    def detect_visuals(self, topic: str, context: dict = None) -> List[str]:
        """
        Synchronous wrapper for visual detection.
        For backwards compatibility - prefers AI-based detection when possible.
        """
        # Return generic visuals - actual detection happens in AI code generation
        return [
            f"Educational visualization of {topic}",
            "Animated diagrams and labels",
            "Step-by-step explanations",
            "Smooth transitions and highlights"
        ]

    async def start_generation(
        self,
        topic: str,
        quality: str = "high",
        duration: int = 20,  # Default to 20 seconds for auto-generation
        context: dict = None,
        auto_generated: bool = False
    ) -> str:
        """Start a video generation task with optional conversation context.

        Args:
            topic: The topic for the video
            quality: Video quality (low, medium, high)
            duration: Target duration in seconds
            context: Optional conversation context for intelligent generation
            auto_generated: If True, applies short video optimizations
        """
        task_id = str(uuid.uuid4())[:8]

        # Check if enhanced mode is available (API key configured)
        enhanced_gen = get_enhanced_generator()

        if enhanced_gen.is_enhanced_mode:
            # ENHANCED MODE: Use longer durations and better quality
            # Analyze complexity to determine optimal duration
            try:
                complexity_info = await enhanced_gen.analyze_complexity(topic, context)
                complexity = complexity_info.get("complexity", "moderate")
                duration = enhanced_gen.get_optimal_duration(complexity)
                logger.info(f"Enhanced mode: {topic} -> {complexity} complexity, {duration}s duration")

                # Add enhanced mode flag to context
                if context is None:
                    context = {}
                context["enhanced_mode"] = True
                context["complexity"] = complexity
                context["visual_density"] = "high"  # 8-10 elements per concept
            except Exception as e:
                logger.warning(f"Complexity analysis failed, using default: {e}")
                duration = 90  # Default enhanced duration
        else:
            # LOCAL MODE: Use shorter durations
            # Adjust duration based on context if provided
            if context and context.get("duration_suggestion"):
                duration = context.get("duration_suggestion")

            # For auto-generated videos, clamp to short video range (10-30 seconds)
            if auto_generated:
                duration = max(10, min(30, duration))
                # Optimize context for short video
                if context:
                    context = self._optimize_for_short_video(context, duration)
                else:
                    context = self._optimize_for_short_video({}, duration)

        task = GenerationTask(
            task_id=task_id,
            topic=topic,
            quality=quality,
            duration=duration,
            status="running",
            stage="content",
            progress=0,
            message="Starting video generation..." if not auto_generated else "Creating quick visual explanation..."
        )

        self.tasks[task_id] = task

        # Start generation in background with context
        asyncio.create_task(self._run_generation(task_id, context))

        return task_id

    def _optimize_for_short_video(self, context: dict, duration: int) -> dict:
        """
        Optimize context for 10-30 second focused video.
        Limits concepts, simplifies structure for maximum clarity.
        """
        optimized = context.copy() if context else {}

        # Limit key concepts to 2-3 for short video (clarity over completeness)
        if "key_concepts" in optimized:
            optimized["key_concepts"] = optimized["key_concepts"][:3]

        # Add short video generation guidance
        optimized["video_style"] = "short_focused"
        optimized["max_scenes"] = 3  # Limit scene count for short video
        optimized["animation_speed"] = "moderate"  # Clear but not rushed
        optimized["narration_style"] = "concise"  # Brief, punchy narration

        # Calculate target word count for narration (roughly 2.5 words/second)
        optimized["target_narration_words"] = int(duration * 2.5)

        # Add specific generation hints for maestro-studio
        optimized["generation_hints"] = {
            "duration_seconds": duration,
            "focus": "single_concept",  # Focus on ONE main takeaway
            "skip_intro": True,  # No lengthy intros - get to the point
            "skip_outro": True,  # No lengthy outros
            "visual_density": "medium",  # Not too cluttered
            "pacing": "educational",  # Clear pacing for learning
            "text_on_screen": "minimal",  # Show key terms only
            "transitions": "simple"  # No fancy transitions eating time
        }

        # Mark as auto-generated for tracking
        optimized["auto_generated"] = True

        return optimized

    async def _run_generation(self, task_id: str, context: dict = None):
        """Run the video generation pipeline with optional conversation context"""
        task = self.tasks.get(task_id)
        if not task:
            return

        try:
            if self.maestro_available:
                await self._run_maestro_generation(task, context)
            else:
                await self._run_simulated_generation(task)
        except Exception as e:
            task.status = "error"
            task.stage = "error"
            task.error = str(e)
            task.message = f"Generation failed: {str(e)}"

    async def _run_maestro_generation(self, task: GenerationTask, context: dict = None):
        """Run actual maestro-studio generation with optional conversation context"""
        try:
            from src.video.orchestrator import EducationalVideoGenerator

            def progress_callback(progress_info):
                """Handle progress updates from maestro"""
                # Map stage names from maestro to our stage names
                stage_map = {
                    'content': 'content',
                    'narration': 'narration',
                    'script': 'animation',
                    'rendering': 'animation',
                    'merging': 'merge',
                    'completed': 'completed',
                    'error': 'error'
                }

                if hasattr(progress_info, 'stage'):
                    task.stage = stage_map.get(progress_info.stage, task.stage)

                if hasattr(progress_info, 'progress'):
                    task.progress = progress_info.progress

                if hasattr(progress_info, 'message'):
                    task.message = progress_info.message
                    task.logs.append(progress_info.message)

            # Get LLM client for content generation (CRITICAL for meaningful videos!)
            llm_client = get_video_llm_client()
            is_enhanced = context and context.get("enhanced_mode", False)

            if is_enhanced:
                task.logs.append(f"ENHANCED MODE: Using {llm_client.provider}/{llm_client.model} for high-quality generation")
                task.logs.append(f"Duration: {task.duration}s | Complexity: {context.get('complexity', 'unknown')}")
            else:
                task.logs.append(f"Using LLM for content generation: {llm_client.provider}/{llm_client.model}")

            # Create generator with LLM client and progress callback
            generator = EducationalVideoGenerator(
                llm_client=llm_client,
                progress_callback=progress_callback
            )

            # Map quality
            quality_map = {'low': 'l', 'medium': 'm', 'high': 'h'}
            manim_quality = quality_map.get(task.quality, 'h')

            # Build context hints for the generator if context is provided
            context_hints = None
            if context:
                context_hints = {
                    "topic_title": context.get("topic_title", task.topic),
                    "key_concepts": context.get("key_concepts", []),
                    "visualization_hints": context.get("visualization_hints", []),
                    "conversation_summary": self._build_conversation_summary(context),
                    "learning_state": context.get("learning_state", "initial"),
                    "content_richness": context.get("content_richness", "exploring"),
                    # Enhanced mode settings
                    "enhanced_mode": is_enhanced,
                    "visual_density": context.get("visual_density", "medium"),
                    "complexity": context.get("complexity", "moderate"),
                    "target_duration": task.duration
                }
                if is_enhanced:
                    task.logs.append(f"Enhanced context: 8-10 visual elements, 5-scene structure, educational pacing")
                task.logs.append(f"Using conversation context: {len(context.get('key_concepts', []))} concepts detected")

            # Generate video with context
            result = await generator.generate(
                topic=task.topic,
                duration=task.duration,
                quality=manim_quality,
                context=context_hints  # Pass context to orchestrator
            )

            if result.success and result.video_path:
                # Copy to our output directory
                output_path = self.output_dir / f"{task.task_id}_{self._safe_filename(task.topic)}.mp4"

                import shutil
                source_video = Path(result.video_path)

                if source_video.exists():
                    shutil.copy(source_video, output_path)
                    task.video_path = f"/generated_videos/{output_path.name}"
                else:
                    # Try to find the video in maestro output
                    topic_slug = self._safe_filename(task.topic).lower().replace(' ', '_')
                    maestro_final = MAESTRO_PATH / "output" / f"{topic_slug}_educational" / "video" / "final_video.mp4"

                    if maestro_final.exists():
                        shutil.copy(maestro_final, output_path)
                        task.video_path = f"/generated_videos/{output_path.name}"
                    else:
                        # Search for any final video
                        for final_mp4 in (MAESTRO_PATH / "output").rglob("final_video.mp4"):
                            if topic_slug in str(final_mp4.parent.parent.name).lower():
                                shutil.copy(final_mp4, output_path)
                                task.video_path = f"/generated_videos/{output_path.name}"
                                break

                task.status = "completed"
                task.stage = "completed"
                task.progress = 100
                task.message = "Video generated successfully!"

                if not task.video_path:
                    task.video_path = str(result.video_path)  # Use original path as fallback
            else:
                raise Exception(result.error or "Generation failed")

        except ImportError as e:
            # Fall back to simulated if import fails
            task.logs.append(f"Maestro import failed: {e}, using simulation")
            await self._run_simulated_generation(task)

    async def _run_simulated_generation(self, task: GenerationTask):
        """Simulated generation for demo/testing"""
        stages = [
            ("content", 0, 20, "Generating educational content..."),
            ("content", 20, 25, "Content structure created"),
            ("narration", 25, 40, "Synthesizing narration audio..."),
            ("narration", 40, 45, "Narration complete"),
            ("animation", 45, 80, "Rendering Manim animations..."),
            ("animation", 80, 90, "Animation rendering complete"),
            ("merge", 90, 100, "Merging audio and video..."),
        ]

        for stage, start_progress, end_progress, message in stages:
            task.stage = stage
            task.message = message
            task.logs.append(message)

            # Simulate progress
            for p in range(start_progress, end_progress + 1, 5):
                task.progress = p
                await asyncio.sleep(0.5)

        # Create placeholder video path (in real implementation, actual video would be here)
        task.status = "completed"
        task.stage = "completed"
        task.progress = 100
        task.video_path = f"/api/placeholder-video/{task.task_id}"
        task.message = "Video generated successfully! (Demo mode - maestro-studio not configured)"

    def _safe_filename(self, text: str) -> str:
        """Create safe filename from text"""
        safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
        return safe.replace(' ', '_')[:50]

    def _build_conversation_summary(self, context: dict) -> str:
        """
        Build a concise summary of the conversation for Manim code generation.
        This helps the LLM understand what was discussed and what to visualize.
        """
        summary_parts = []

        # Add main topic
        if context.get("main_topic"):
            summary_parts.append(f"Main topic: {context['main_topic']}")

        # Add topics discussed
        topics = context.get("topics_discussed", [])
        if topics:
            summary_parts.append(f"Topics covered: {', '.join(topics[:5])}")

        # Add key concepts
        concepts = context.get("key_concepts", [])
        if concepts:
            summary_parts.append(f"Key concepts: {', '.join(concepts[:5])}")

        # Add visualization hints
        hints = context.get("visualization_hints", [])
        if hints:
            summary_parts.append("Visualization needs:")
            for hint in hints[:3]:
                summary_parts.append(f"  - {hint}")

        # Add key discoveries if any
        discoveries = context.get("key_discoveries", [])
        if discoveries:
            summary_parts.append("Student discoveries to reinforce:")
            for discovery in discoveries[:2]:
                if discovery:
                    summary_parts.append(f"  - {discovery[:80]}")

        # Add recent conversation context
        recent = context.get("conversation_history", [])
        if recent:
            summary_parts.append("\nRecent conversation context:")
            for exchange in recent[-2:]:  # Last 2 exchanges
                user_msg = exchange.get("user", "")[:100]
                ai_msg = exchange.get("ai", "")[:150]
                if user_msg:
                    summary_parts.append(f"  User: {user_msg}")
                if ai_msg:
                    summary_parts.append(f"  AI: {ai_msg}...")

        return "\n".join(summary_parts)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a generation task"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "topic": task.topic,
            "status": task.status,
            "stage": task.stage,
            "progress": task.progress,
            "message": task.message,
            "video_path": task.video_path,
            "error": task.error,
            "log_entry": task.logs[-1] if task.logs else None
        }

    def get_generated_videos(self) -> List[Dict[str, Any]]:
        """Get list of generated videos"""
        videos = []

        # Check output directory
        if self.output_dir.exists():
            for video_file in self.output_dir.glob("*.mp4"):
                stat = video_file.stat()
                videos.append({
                    "id": video_file.stem,
                    "path": f"/generated_videos/{video_file.name}",
                    "topic": video_file.stem.split('_', 1)[-1].replace('_', ' '),
                    "duration": "1:30",  # Would need ffprobe for actual duration
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # Also check maestro output directory
        maestro_output = MAESTRO_PATH / "generated_videos"
        if maestro_output.exists():
            for video_file in maestro_output.glob("*.mp4"):
                if not any(v['id'] == video_file.stem for v in videos):
                    stat = video_file.stat()
                    videos.append({
                        "id": video_file.stem,
                        "path": str(video_file),
                        "topic": video_file.stem.replace('_', ' '),
                        "duration": "1:30",
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

        # Sort by creation date, newest first
        videos.sort(key=lambda x: x['created_at'], reverse=True)
        return videos

# Global service instance
video_service = VideoGenerationService()
