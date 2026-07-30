from .base import SCORATIS_BASE_FRAMEWORK
from .citation import CITATION_INSTRUCTIONS, RAG_CONTEXT_AWARENESS
from .subjects import (
    SUBJECT_PROMPTS, SUBJECT_CHANNELS, GENERAL_PROMPT,
    get_subject_prompt, get_available_subjects
)
from .video_detection import detect_video_potential

__all__ = [
    "SCORATIS_BASE_FRAMEWORK",
    "CITATION_INSTRUCTIONS",
    "RAG_CONTEXT_AWARENESS",
    "SUBJECT_PROMPTS",
    "SUBJECT_CHANNELS",
    "GENERAL_PROMPT",
    "get_subject_prompt",
    "get_available_subjects",
    "detect_video_potential",
]
