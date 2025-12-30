"""
Alembic Environment Configuration for Scoratis

Supports both sync and async database operations.
Automatically loads models and configures pgvector support.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine
from sqlalchemy import create_engine

from alembic import context

# Import your models' Base to access metadata
from models.base import Base

# Import all models to ensure they're registered with Base.metadata
from models import (
    User,
    Folder,
    Journal,
    Conversation,
    ChatMessage,
    LearningState,
    LLMProviderConfig,
    Document,
    Chunk,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """
    Get database URL from environment variable or alembic.ini.
    Supports both sync and async URLs.
    """
    # Try async URL first (for async migrations)
    url = os.getenv("DATABASE_URL_ASYNC")
    if url:
        return url

    # Fall back to sync URL
    url = os.getenv("DATABASE_URL")
    if url:
        # Convert to async format if needed
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    # Fall back to alembic.ini setting
    return config.get_main_option("sqlalchemy.url")


def get_sync_url() -> str:
    """Get synchronous database URL for offline migrations."""
    url = os.getenv("DATABASE_URL")
    if url:
        # Ensure it's sync format
        if "+asyncpg" in url:
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url

    url = config.get_main_option("sqlalchemy.url")
    if "+asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Include custom types like Vector
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects for autogenerate.

    Excludes certain objects from migration generation.
    """
    # Skip internal alembic version table
    if type_ == "table" and name == "alembic_version":
        return False

    return True


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using synchronous connection.

    This is the default mode that connects to a live database.
    """
    url = get_sync_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


async def run_async_migrations() -> None:
    """
    Run migrations using async engine.

    This is an alternative for fully async setups.
    """
    url = get_url()

    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online_async() -> None:
    """Entry point for async migrations."""
    asyncio.run(run_async_migrations())


# Determine which mode to run
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use sync mode by default (more compatible)
    run_migrations_online()
