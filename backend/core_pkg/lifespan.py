import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from config import settings
from database import get_database
from llm_service import llm_service
from services import (
    get_rag_service, get_web_search_service, get_memory_service
)
from services.langgraph_service import initialize_langgraph_service
from services.video_analyzer_service import init_video_analyzer_service
from services.agent import create_agent
from services.guardrail_service import get_guardrail_service

import backend.core.services as services

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
