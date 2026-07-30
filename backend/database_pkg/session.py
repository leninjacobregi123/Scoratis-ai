import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings
from models import Base, User

logger = logging.getLogger(__name__)

class DatabaseSession:
        try:
            Base.metadata.create_all(self.sync_engine)
            with self.SyncSession() as session:
                if not session.get(User, 1):
                    session.add(User(id=1, username="Lenin", email="lenin@scoratis.com"))
                    session.commit()
        except Exception as e:
            logger.error(f"DB Init Error: {e}")

db_session = DatabaseSession()
