import os
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from .client import SmartVideoClient, SmartManimClient
from .generator import EnhancedVideoGenerator

logger = logging.getLogger(__name__)

MAESTRO_PATH = Path(os.environ.get("MAESTRO_PATH", str(Path.home() / "maestro-studio")))

class VideoGenerationService:
