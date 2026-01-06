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
        """
        Generate text completion using Ollama.
        Compatible with LlamaCppClient.generate() interface.
        """
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
                logger.info(f"Ollama generated {len(output)} characters for video content")
                return output
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise


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


# Global LLM clients for video generation (initialized lazily)
_video_llm_client: Optional[OllamaVideoClient] = None
_manim_code_client: Optional[ManimCodeClient] = None


def get_video_llm_client() -> OllamaVideoClient:
    """Get or create the video LLM client (for narration)"""
    global _video_llm_client
    if _video_llm_client is None:
        _video_llm_client = OllamaVideoClient()
    return _video_llm_client


def get_manim_code_client() -> ManimCodeClient:
    """Get or create the Manim code generation client"""
    global _manim_code_client
    if _manim_code_client is None:
        _manim_code_client = ManimCodeClient()
    return _manim_code_client

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
            task.logs.append(f"Using Ollama LLM for content generation: {llm_client.model}")

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
                    "content_richness": context.get("content_richness", "exploring")
                }
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
