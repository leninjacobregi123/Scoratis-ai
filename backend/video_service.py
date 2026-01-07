"""
Video Generation Service for Scoratis
Interfaces with maestro-studio for AI-powered educational video generation
"""

import os
import sys
import asyncio
import uuid
import json
import httpx
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Add maestro-studio to path (use environment variable or default)
MAESTRO_PATH = Path(os.environ.get("MAESTRO_PATH", str(Path.home() / "maestro-studio")))
if MAESTRO_PATH.exists():
    sys.path.insert(0, str(MAESTRO_PATH))


class OllamaVideoClient:
    """
    Ollama client wrapper compatible with LlamaCppClient interface.
    Used for generating video content (titles, bullet points, narration, etc.)
    """

    def __init__(self, base_url: str = None, model: str = "llama3.2"):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model
        logger.info(f"OllamaVideoClient initialized: {self.base_url} with model {self.model}")

    def check_model_exists(self) -> bool:
        """Check if the model exists in Ollama"""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return any(m.get("name", "").startswith(self.model) for m in models)
        except Exception:
            pass
        return False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[list] = None
    ) -> str:
        """Generate text completion using Ollama."""
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": top_p,
                            "num_predict": max_tokens,
                            "stop": stop or []
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                output = result.get("response", "").strip()
                logger.info(f"OllamaVideoClient generated {len(output)} chars using {self.model}")
                return output
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise


class SmartVideoClient:
    """
    Smart video client that automatically chooses between API and local Ollama.
    - If API key is configured → Use cloud API (Groq, OpenAI, etc.)
    - If no API key → Fallback to local Ollama
    """

    def __init__(self):
        self._api_client = None
        self._ollama_client = None
        self._use_api = False
        self._initialize()

    def _initialize(self):
        """Initialize the appropriate client based on API key availability"""
        try:
            from llm_service import llm_service
            config = llm_service.get_current_config()

            if config:
                provider = config.get("provider", "ollama")
                # Check if using a cloud provider (not ollama/local)
                if provider not in ["ollama", "lmstudio", "localai", "textgenwebui"]:
                    # Check if API key is available by checking the current config has encrypted key
                    if llm_service.current_config and llm_service.current_config.api_key_encrypted:
                        self._use_api = True
                        self._llm_service = llm_service
                        logger.info(f"SmartVideoClient: Using API ({provider}/{config.get('model')})")
                    else:
                        logger.info(f"SmartVideoClient: No API key for {provider}, falling back to Ollama")

            if not self._use_api:
                self._ollama_client = OllamaVideoClient()
                logger.info("SmartVideoClient: Using local Ollama")

        except Exception as e:
            logger.warning(f"SmartVideoClient init error: {e}, falling back to Ollama")
            self._ollama_client = OllamaVideoClient()

    @property
    def model(self) -> str:
        """Get the current model name"""
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("model", "unknown") if config else "unknown"
        return self._ollama_client.model if self._ollama_client else "llama3.2"

    @property
    def provider(self) -> str:
        """Get the current provider name"""
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("provider", "api") if config else "api"
        return "ollama"

    def check_model_exists(self) -> bool:
        """Check if the model is available"""
        if self._use_api:
            return True  # Assume API is available if configured
        return self._ollama_client.check_model_exists() if self._ollama_client else False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[list] = None
    ) -> str:
        """Generate text using the best available model"""
        if self._use_api:
            return self._generate_with_api(prompt, max_tokens, temperature)
        return self._ollama_client.generate(prompt, max_tokens, temperature, top_p, stop)

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
    Smart Manim code generator that automatically chooses between API and local Ollama.
    - If API key is configured → Use cloud API for better code generation
    - If no API key → Fallback to local Ollama with code-optimized models
    """

    CODE_MODELS = ["manim-llama", "deepseek-coder", "codellama", "llama3.2", "mistral"]

    def __init__(self):
        self._use_api = False
        self._ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self._ollama_model = "llama3.2"
        self._initialize()

    def _initialize(self):
        """Initialize the appropriate backend"""
        try:
            from llm_service import llm_service
            config = llm_service.get_current_config()

            if config:
                provider = config.get("provider", "ollama")
                if provider not in ["ollama", "lmstudio", "localai", "textgenwebui"]:
                    if llm_service.current_config and llm_service.current_config.api_key_encrypted:
                        self._use_api = True
                        self._llm_service = llm_service
                        logger.info(f"SmartManimClient: Using API ({provider}/{config.get('model')})")
                        return

            # Fallback to Ollama - detect best code model
            self._ollama_model = self._detect_best_ollama_model()
            logger.info(f"SmartManimClient: Using local Ollama ({self._ollama_model})")

        except Exception as e:
            logger.warning(f"SmartManimClient init error: {e}")
            self._ollama_model = self._detect_best_ollama_model()

    def _detect_best_ollama_model(self) -> str:
        """Detect the best available Ollama model for code generation"""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self._ollama_base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]

                    for preferred in self.CODE_MODELS:
                        if any(preferred in name for name in model_names):
                            return preferred

                    if model_names:
                        return model_names[0].split(":")[0]
        except Exception as e:
            logger.warning(f"Could not detect Ollama models: {e}")

        return "llama3.2"

    @property
    def model(self) -> str:
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("model", "unknown") if config else "unknown"
        return self._ollama_model

    @property
    def provider(self) -> str:
        if self._use_api:
            config = self._llm_service.get_current_config()
            return config.get("provider", "api") if config else "api"
        return "ollama"

    def generate_manim_code(
        self,
        topic: str,
        description: str = "",
        duration: int = 30,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Manim code using the best available model"""
        prompt = self._build_manim_prompt(topic, description, duration, context)

        if self._use_api:
            code = self._generate_with_api(prompt)
        else:
            code = self._generate_with_ollama(prompt)

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

    def _generate_with_ollama(self, prompt: str) -> str:
        """Generate using local Ollama"""
        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    f"{self._ollama_base_url}/api/generate",
                    json={
                        "model": self._ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 6000,
                        }
                    }
                )
                response.raise_for_status()
                code = response.json().get("response", "").strip()
                logger.info(f"SmartManimClient generated {len(code)} chars using Ollama/{self._ollama_model}")
                return code
        except Exception as e:
            logger.error(f"Ollama Manim generation failed: {e}")
            return self._generate_fallback_code(prompt.split('\n')[0], 30)

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


class ManimCodeClient:
    """
    Pure AI-driven Manim code generator.
    Uses LLM to generate complete, contextual Manim animations based on conversation context.
    No hardcoded templates - everything is generated dynamically by AI.
    """

    # Preferred models for code generation (in order of preference)
    CODE_MODELS = ["deepseek-coder", "codellama", "llama3.2", "mistral"]

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = self._detect_best_model()
        logger.info(f"ManimCodeClient initialized: {self.base_url} with model {self.model}")

    def _detect_best_model(self) -> str:
        """Detect the best available model for code generation"""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]

                    # Check for preferred code models in order
                    for preferred in self.CODE_MODELS:
                        if any(preferred in name for name in model_names):
                            logger.info(f"Using code-optimized model: {preferred}")
                            return preferred

                    # Use first available model
                    if model_names:
                        return model_names[0].split(":")[0]

        except Exception as e:
            logger.warning(f"Could not detect models: {e}")

        return "llama3.2"  # Default fallback

    def generate_manim_code(
        self,
        topic: str,
        description: str = "",
        duration: int = 30,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate complete Manim animation code using AI.
        All code is generated dynamically based on topic and context - no templates.

        Args:
            topic: The topic to animate
            description: Additional description or context
            duration: Target video duration in seconds
            context: Conversation context including key_concepts, visual_elements, animation_suggestions

        Returns:
            Complete Manim Python code as a string
        """
        # Build comprehensive context for AI
        context_sections = []

        if context:
            if context.get("key_concepts"):
                context_sections.append(f"Key concepts to visualize:\n- " + "\n- ".join(context["key_concepts"][:5]))

            if context.get("visual_elements"):
                context_sections.append(f"Visual elements to include:\n- " + "\n- ".join(context["visual_elements"][:5]))

            if context.get("animation_suggestions"):
                context_sections.append(f"Animation suggestions:\n- " + "\n- ".join(context["animation_suggestions"][:5]))

            if context.get("visualization_type"):
                context_sections.append(f"Visualization type: {context['visualization_type']}")

            if context.get("conversation_summary"):
                context_sections.append(f"Conversation context:\n{context['conversation_summary'][:500]}")

        context_info = "\n\n".join(context_sections) if context_sections else "No additional context provided."

        prompt = f"""You are an expert Manim animator creating educational videos.
Generate a complete, working Manim animation for the following topic.

## TOPIC
{topic}

## ADDITIONAL DESCRIPTION
{description if description else "Create an engaging educational animation that clearly explains this concept."}

## CONTEXT FROM CONVERSATION
{context_info}

## REQUIREMENTS

1. **Code Structure:**
   - Use ManimCE (Community Edition) syntax
   - Create a class called `ManimScene` that inherits from `Scene`
   - Implement the `construct(self)` method
   - Import everything needed: `from manim import *`

2. **Animation Guidelines:**
   - Target duration: approximately {duration} seconds
   - Use smooth, educational animations
   - Include clear text labels and explanations
   - Use appropriate colors for different elements
   - Add pauses (self.wait()) for readability
   - Build up complexity gradually

3. **Visual Quality:**
   - Use Create(), Write(), FadeIn(), Transform() for smooth animations
   - Group related elements together
   - Use VGroup for organizing multiple objects
   - Include a title at the start
   - Use appropriate positioning (UP, DOWN, LEFT, RIGHT, etc.)

4. **Educational Focus:**
   - Make the animation self-explanatory
   - Highlight key concepts with color or emphasis
   - Use arrows, labels, and annotations
   - Show cause and effect relationships
   - Build understanding step by step

## OUTPUT FORMAT
Return ONLY valid Python code. Start with `from manim import *` and end with the complete class definition.
Do NOT include any explanations, comments outside the code, or markdown formatting.

```python
from manim import *

class ManimScene(Scene):
    def construct(self):
        # Your animation code here
        pass
```"""

        try:
            with httpx.Client(timeout=300.0) as client:  # Longer timeout for complex code
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,  # Low temperature for reliable code
                            "top_p": 0.9,
                            "num_predict": 6000,  # Allow longer code output
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                code = result.get("response", "").strip()

                # Clean and validate the code
                code = self._clean_manim_code(code)
                code = self._validate_and_fix_code(code, topic)

                logger.info(f"ManimCodeClient generated {len(code)} chars of Manim code using {self.model}")
                return code

        except Exception as e:
            logger.error(f"Manim code generation failed: {e}")
            # Return a minimal working fallback
            return self._generate_fallback_code(topic, duration)

    def _clean_manim_code(self, code: str) -> str:
        """Clean up generated Manim code"""
        # Remove markdown code blocks if present
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0]

        # Ensure it starts with imports
        if not code.strip().startswith("from manim"):
            if "from manim" in code:
                code = code[code.find("from manim"):]
            else:
                code = "from manim import *\n\n" + code

        return code.strip()

    def _validate_and_fix_code(self, code: str, topic: str) -> str:
        """Validate and fix common issues in generated Manim code"""
        lines = code.split("\n")
        fixed_lines = []
        has_class = False
        has_construct = False

        for line in lines:
            # Check for class definition
            if "class ManimScene" in line or "class " in line and "Scene" in line:
                has_class = True
            if "def construct" in line:
                has_construct = True
            fixed_lines.append(line)

        code = "\n".join(fixed_lines)

        # Add missing class structure if needed
        if not has_class:
            code = code + f"""

class ManimScene(Scene):
    def construct(self):
        title = Text("{topic}", font_size=48)
        self.play(Write(title))
        self.wait(2)
        self.play(FadeOut(title))
"""
        elif not has_construct:
            # Find the class and add construct method
            code = code.replace(
                "class ManimScene(Scene):",
                f"""class ManimScene(Scene):
    def construct(self):
        title = Text("{topic}", font_size=48)
        self.play(Write(title))
        self.wait(2)"""
            )

        return code

    def _generate_fallback_code(self, topic: str, duration: int) -> str:
        """Generate a minimal working Manim animation as fallback"""
        return f'''from manim import *

class ManimScene(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=48, color=BLUE)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Main content
        content = Text(
            "Visual explanation coming soon...",
            font_size=32
        )
        self.play(FadeIn(content))
        self.wait({max(2, duration - 4)})

        # Outro
        self.play(FadeOut(content), FadeOut(title))
'''


# =============================================================================
# ENHANCED VIDEO GENERATION PROMPTS
# =============================================================================

SCRIPT_PLANNING_PROMPT = """You are an expert educational video scriptwriter creating content for visual learners.
Create a detailed scene-by-scene breakdown for: {topic}

TARGET DURATION: {duration} seconds
AUDIENCE: High school to undergraduate level
VISUAL DENSITY: 8-10 visual elements per concept

## SCENE STRUCTURE (5 scenes required):

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
- Memorable closing statement

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

ENHANCED_MANIM_PROMPT = """You are an expert Manim animator creating professional educational videos.
Generate a complete, production-quality Manim animation based on this script:

{script_json}

## CRITICAL REQUIREMENTS:

### 1. CODE STRUCTURE
```python
from manim import *

class ManimScene(Scene):
    def construct(self):
        self.scene_1_hook()
        self.scene_2_foundation()
        self.scene_3_explanation()
        self.scene_4_application()
        self.scene_5_summary()

    def scene_1_hook(self):
        # Scene 1 implementation
        pass

    # ... other scene methods
```

### 2. VISUAL DENSITY (8-10 elements per major concept)
- Use VGroup for organizing related elements
- Layer elements for visual depth
- Include labels, annotations, and arrows
- Show relationships with connecting lines
- Add step numbers for processes (①②③)

### 3. ANIMATION TIMING
- Title animations: 2-3 seconds with Write()
- Concept introductions: 3-4 seconds with Create()/FadeIn()
- Diagram building: 2-3 seconds per stage
- Key points: 2 second pause with Indicate()
- Transitions: 1 second with FadeOut()/FadeIn()
- Use self.wait(2) after important information

### 4. PROFESSIONAL STYLING
- Title: font_size=48, color=BLUE
- Headers: font_size=36, color=YELLOW
- Body text: font_size=28, color=WHITE
- Key terms: color=GREEN with Indicate()
- Formulas: MathTex with color=GOLD
- Minimum 24pt for all text

### 5. VISUAL HIERARCHY
- Primary concept: Center, large, bold color
- Supporting details: Positioned around primary
- Annotations: Smaller, positioned with arrows
- Use buff=0.5 for consistent spacing

### 6. EDUCATIONAL BEST PRACTICES
- Build complexity gradually (simple → complex)
- Show cause → effect with animated arrows
- Use before/after comparisons
- Highlight key terms when mentioned in narration
- Include visual metaphors for abstract concepts

### 7. COLOR PALETTE
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

    # Local fallback duration
    DURATION_LOCAL = 25       # Quick videos for local mode

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

            if config:
                provider = config.get("provider", "ollama")
                # Check if using cloud provider with API key
                if provider not in ["ollama", "lmstudio", "localai", "textgenwebui"]:
                    if llm_service.current_config and llm_service.current_config.api_key_encrypted:
                        self._use_api = True
                        logger.info(f"EnhancedVideoGenerator: API mode enabled ({provider})")
                        return

            logger.info("EnhancedVideoGenerator: Local mode (quick videos)")
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
                "recommended_duration": self.DURATION_LOCAL,
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
            return self.DURATION_LOCAL

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
            # Quick script for local mode
            return {
                "title": topic[:50],
                "total_duration": duration,
                "scenes": [{"scene_number": 1, "name": "Main", "duration": duration}],
                "key_concepts": [topic],
                "visual_style": "diagram"
            }

        try:
            prompt = SCRIPT_PLANNING_PROMPT.format(
                topic=topic,
                duration=duration
            )

            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are an expert educational video scriptwriter. Output only valid JSON."
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

    async def generate_manim_code(self, script: dict, topic: str) -> str:
        """
        Phase 2: Generate Manim animation code from script.
        """
        if not self._use_api or not script.get("scenes"):
            # Use SmartManimClient for local mode
            client = SmartManimClient()
            return client.generate_manim_code(
                topic=topic,
                duration=script.get("total_duration", 25)
            )

        try:
            prompt = ENHANCED_MANIM_PROMPT.format(
                script_json=json.dumps(script, indent=2)
            )

            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_service.generate(
                messages=messages,
                system_prompt="You are an expert Manim animator. Generate only valid Python code."
            )

            # Clean code
            code = self._clean_manim_code(response)
            code = self._validate_and_fix_code(code, topic)

            logger.info(f"EnhancedVideoGenerator: Generated {len(code)} chars of Manim code")
            return code

        except Exception as e:
            logger.error(f"Manim code generation failed: {e}")
            return self._generate_fallback_code(topic, script.get("total_duration", 60))

    async def generate_enhanced_video(self, topic: str, context: dict = None) -> dict:
        """
        Full enhanced video generation pipeline.
        Returns script, manim code, and metadata.
        """
        # Phase 0: Analyze complexity
        complexity_info = await self.analyze_complexity(topic, context)
        complexity = complexity_info.get("complexity", "moderate")
        duration = self.get_optimal_duration(complexity)

        logger.info(f"EnhancedVideoGenerator: {topic} -> {complexity} complexity, {duration}s duration")

        # Phase 1: Generate script
        script = await self.generate_script(topic, duration, context)

        # Phase 2: Generate Manim code
        manim_code = await self.generate_manim_code(script, topic)

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
