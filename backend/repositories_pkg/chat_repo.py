import logging
from typing import List, Dict, Optional, Any
from sqlalchemy import select, func, and_, or_, text
from models import Conversation, ChatMessage
from backend.database.session import db_session
from services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

class ChatRepository:
