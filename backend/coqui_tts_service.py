"""
Coqui TTS Service for Scoratis - Voice Synthesis
Provides high-quality male voices for each tutor personality
Falls back to Edge TTS if Coqui TTS is not available
"""

import hashlib
import logging
import sys
from pathlib import Path
from typing import Optional
import threading
import asyncio
import subprocess

logger = logging.getLogger(__name__)

# Voice configurations for each tutor mode using VCTK male speakers
TUTOR_VOICES = {
    "socrates": {
        "speaker": "p232",
        "description": "Deep, authoritative, questioning tone"
    },
    "mentor": {
        "speaker": "p273",
        "description": "Warm, confident, supportive tone"
    },
    "coach": {
        "speaker": "p256",
        "description": "Energetic, motivating, direct tone"
    },
    "buddy": {
        "speaker": "p227",
        "description": "Casual, friendly, approachable tone"
    },
    "expert": {
        "speaker": "p270",
        "description": "Measured, precise, academic tone"
    }
}

# Audio cache directory
AUDIO_CACHE_DIR = Path(__file__).parent / "audio_cache"
AUDIO_CACHE_DIR.mkdir(exist_ok=True)

# Edge TTS voice mapping (used as fallback)
EDGE_TTS_VOICES = {
    "socrates": "en-US-ChristopherNeural",  # Deep, authoritative
    "mentor": "en-US-GuyNeural",            # Warm, supportive
    "coach": "en-US-DavisNeural",           # Energetic, direct
    "buddy": "en-US-JasonNeural",           # Casual, friendly
    "expert": "en-US-TonyNeural",           # Measured, academic
}


class CoquiTTSService:
    """
    Text-to-Speech service using Coqui TTS for offline voice synthesis.
    Uses VCTK multi-speaker model with different male voices per tutor.
    """

    def __init__(self):
        self.cache_dir = AUDIO_CACHE_DIR
        self.tts = None
        self._lock = threading.Lock()
        self._initialized = False
        self._use_edge_tts = False  # Flag to use edge-tts as fallback
        self._edge_tts_available = self._check_edge_tts()
        logger.info("Coqui TTS Service created (lazy initialization)")

    def _check_edge_tts(self) -> bool:
        """Check if edge-tts is available.

        Invoked as `python -m edge_tts` (module form), not the bare `edge-tts`
        console script - the console script only resolves if this process's
        PATH happens to include the venv's bin directory, which isn't
        guaranteed depending on how the backend was launched (same issue
        fixed in tasks_pkg/video_tasks.py's narration synthesis).
        `sys.executable` always correctly identifies this interpreter's
        environment regardless of PATH.
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "edge_tts", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _ensure_initialized(self):
        """Lazy initialization of TTS model"""
        if self._initialized:
            return True

        with self._lock:
            if self._initialized:
                return True

            try:
                from TTS.api import TTS
                logger.info("Loading Coqui TTS VCTK model...")
                self.tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False)
                self._initialized = True
                self._use_edge_tts = False
                logger.info("Coqui TTS VCTK model loaded successfully")
                return True
            except Exception as e:
                logger.warning(f"Coqui TTS not available: {e}")
                if self._edge_tts_available:
                    logger.info("Using Edge TTS as fallback")
                    self._use_edge_tts = True
                    self._initialized = True
                    return True
                else:
                    logger.error("No TTS engine available")
                    return False

    def get_voice_config(self, tutor_mode: str) -> dict:
        """Get voice configuration for a tutor mode"""
        return TUTOR_VOICES.get(tutor_mode, TUTOR_VOICES["socrates"])

    def _generate_cache_key(self, text: str, tutor_mode: str) -> str:
        """Generate a cache key for the audio"""
        content = f"coqui:{tutor_mode}:{text}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def synthesize(
        self,
        text: str,
        tutor_mode: str = "socrates",
        use_cache: bool = True
    ) -> Optional[Path]:
        """
        Convert text to speech using the tutor's voice.

        Args:
            text: Text to synthesize
            tutor_mode: Which tutor voice to use
            use_cache: Whether to use cached audio if available

        Returns:
            Path to the generated audio file, or None if failed
        """
        if not text or len(text.strip()) < 2:
            return None

        # Clean text for TTS
        clean_text = self._clean_text_for_tts(text)
        if not clean_text:
            return None

        # Check cache (check both wav and mp3 extensions)
        cache_key = self._generate_cache_key(clean_text, tutor_mode)
        cache_path_wav = self.cache_dir / f"{cache_key}.wav"
        cache_path_mp3 = self.cache_dir / f"{cache_key}.mp3"

        if use_cache:
            if cache_path_mp3.exists():
                logger.debug(f"Using cached audio (mp3): {cache_key}")
                return cache_path_mp3
            if cache_path_wav.exists():
                logger.debug(f"Using cached audio (wav): {cache_key}")
                return cache_path_wav

        cache_path = cache_path_wav  # Default to wav for Coqui TTS

        # Ensure TTS is initialized
        if not self._ensure_initialized():
            logger.error("TTS not initialized")
            return None

        # Use Edge TTS if Coqui TTS is not available
        if self._use_edge_tts:
            return self._synthesize_edge_tts(clean_text, tutor_mode, cache_path)

        # Get voice config for Coqui TTS
        voice_config = self.get_voice_config(tutor_mode)
        speaker = voice_config["speaker"]

        try:
            logger.info(f"Synthesizing with speaker {speaker} for {tutor_mode} mode")

            self.tts.tts_to_file(
                text=clean_text,
                speaker=speaker,
                file_path=str(cache_path)
            )

            if cache_path.exists():
                logger.info(f"Audio generated: {cache_path.name}")
                return cache_path

            return None

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    def _synthesize_edge_tts(self, text: str, tutor_mode: str, cache_path: Path) -> Optional[Path]:
        """Synthesize using Edge TTS as fallback"""
        voice = EDGE_TTS_VOICES.get(tutor_mode, EDGE_TTS_VOICES["socrates"])

        # Edge TTS outputs MP3, so use mp3 extension
        mp3_path = cache_path.with_suffix('.mp3')

        try:
            logger.info(f"Synthesizing with Edge TTS voice {voice}")

            # Run edge-tts via module form (see _check_edge_tts's docstring)
            result = subprocess.run(
                [
                    sys.executable, "-m", "edge_tts",
                    "--voice", voice,
                    "--text", text,
                    "--write-media", str(mp3_path)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and mp3_path.exists():
                logger.info(f"Edge TTS audio generated: {mp3_path.name}")
                return mp3_path
            else:
                logger.error(f"Edge TTS error: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return None

    def _clean_text_for_tts(self, text: str, max_length: int = 500) -> str:
        """Clean text for TTS synthesis"""
        import re

        # Remove markdown formatting
        clean = text

        # Remove code blocks
        clean = re.sub(r'```[\s\S]*?```', '', clean)
        clean = re.sub(r'`[^`]+`', '', clean)

        # Remove pedagogical plan tags
        clean = re.sub(r'<pedagogical_plan>[\s\S]*?</pedagogical_plan>', '', clean)

        # Remove markdown headers
        clean = re.sub(r'^#+\s+', '', clean, flags=re.MULTILINE)

        # Remove bold/italic
        clean = re.sub(r'\*+([^*]+)\*+', r'\1', clean)
        clean = re.sub(r'_+([^_]+)_+', r'\1', clean)

        # Remove links
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)

        # Remove bullet points
        clean = re.sub(r'^[-*]\s+', '', clean, flags=re.MULTILINE)

        # Clean up whitespace
        clean = re.sub(r'\n+', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean)
        clean = clean.strip()

        # Limit length (Coqui TTS handles longer text less well)
        if len(clean) > max_length:
            # Try to cut at sentence boundary
            sentences = clean[:max_length].split('.')
            if len(sentences) > 1:
                clean = '.'.join(sentences[:-1]) + '.'
            else:
                clean = clean[:max_length-3] + '...'

        return clean

    def get_available_voices(self) -> dict:
        """Get all available tutor voices with their descriptions"""
        return {
            mode: {
                "speaker": config["speaker"],
                "description": config["description"]
            }
            for mode, config in TUTOR_VOICES.items()
        }

    def clear_cache(self) -> int:
        """Clear the audio cache. Returns number of files deleted."""
        count = 0
        for file in self.cache_dir.glob("*.wav"):
            file.unlink()
            count += 1
        for file in self.cache_dir.glob("*.mp3"):
            file.unlink()
            count += 1
        logger.info(f"Cleared {count} cached audio files")
        return count


# Global instance
coqui_tts_service = CoquiTTSService()
