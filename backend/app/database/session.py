"""Async SQLAlchemy database setup with SQLite (dev) / PostgreSQL (prod)."""
from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()


def normalize_async_database_url(url: str) -> str:
    """Add the async SQLAlchemy drivers when a standard SQLite/PostgreSQL URL is used."""
    database_url = make_url(url)
    if database_url.drivername in {"postgres", "postgresql"}:
        database_url = database_url.set(drivername="postgresql+asyncpg")
    elif database_url.drivername == "sqlite":
        database_url = database_url.set(drivername="sqlite+aiosqlite")
    return database_url.render_as_string(hide_password=False)


database_url_string = normalize_async_database_url(settings.database_url)
database_url = make_url(database_url_string)

engine = create_async_engine(
    database_url_string,
    echo=settings.debug,
    future=True,
    connect_args={"check_same_thread": False} if database_url.get_backend_name() == "sqlite" else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def _upgrade_legacy_sqlite_schema(connection: Connection) -> None:
    """Add columns required by the current models to older SQLite databases."""
    tables = set(inspect(connection).get_table_names())
    additions = {
        "chat_sessions": {
            "metadata_json": "TEXT",
        },
        "messages": {
            "provider": "VARCHAR(64)",
            "model": "VARCHAR(128)",
            "sources_json": "TEXT",
            "artifact_id": "VARCHAR(36)",
        },
        "knowledge_sources": {
            "author": "VARCHAR(256)",
            "file_path": "TEXT",
            "content": "TEXT",
            "chunk_count": "INTEGER NOT NULL DEFAULT 0",
            "content_hash": "VARCHAR(64)",
            "created_at": "DATETIME",
            "ingested_at": "DATETIME",
        },
        "artifacts": {
            "artifact_type": "VARCHAR(64) NOT NULL DEFAULT 'markdown'",
            "type": "VARCHAR(64)",
            "updated_at": "DATETIME",
        },
    }

    added: dict[str, set[str]] = {}
    for table_name, columns in additions.items():
        if table_name not in tables:
            continue
        existing = {
            column["name"]
            for column in inspect(connection).get_columns(table_name)
        }
        for column_name, definition in columns.items():
            if column_name not in existing:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {definition}"
                    )
                )
                added.setdefault(table_name, set()).add(column_name)

    if "sources_json" in added.get("messages", set()):
        message_columns = {
            column["name"] for column in inspect(connection).get_columns("messages")
        }
        if "citations" in message_columns:
            connection.execute(
                text(
                    "UPDATE messages SET sources_json = citations "
                    "WHERE sources_json IS NULL AND citations IS NOT NULL"
                )
            )

    if "artifact_type" in added.get("artifacts", set()):
        artifact_columns = {
            column["name"] for column in inspect(connection).get_columns("artifacts")
        }
        if "type" in artifact_columns:
            connection.execute(
                text(
                    "UPDATE artifacts SET artifact_type = type "
                    "WHERE type IS NOT NULL"
                )
            )

    if "updated_at" in added.get("artifacts", set()):
        connection.execute(
            text("UPDATE artifacts SET updated_at = created_at WHERE updated_at IS NULL")
        )

    if "ingested_at" in added.get("knowledge_sources", set()):
        source_columns = {
            column["name"]
            for column in inspect(connection).get_columns("knowledge_sources")
        }
        if "created_at" in source_columns:
            connection.execute(
                text(
                    "UPDATE knowledge_sources SET ingested_at = created_at "
                    "WHERE ingested_at IS NULL"
                )
            )
    if "created_at" in added.get("knowledge_sources", set()):
        connection.execute(
            text(
                "UPDATE knowledge_sources SET created_at = "
                "COALESCE(ingested_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL"
            )
        )


def _upgrade_legacy_postgres_schema(connection: Connection) -> None:
    """Add columns introduced after an existing PostgreSQL database was created."""
    tables = set(inspect(connection).get_table_names())
    additions = {
        "chat_sessions": {
            "metadata_json": "TEXT",
        },
        "messages": {
            "provider": "VARCHAR(64)",
            "model": "VARCHAR(128)",
            "sources_json": "TEXT",
            "artifact_id": "VARCHAR(36)",
        },
        "knowledge_sources": {
            "author": "VARCHAR(256)",
            "file_path": "TEXT",
            "content": "TEXT",
            "chunk_count": "INTEGER NOT NULL DEFAULT 0",
            "content_hash": "VARCHAR(64)",
            "created_at": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "ingested_at": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
        "artifacts": {
            "artifact_type": "VARCHAR(64) NOT NULL DEFAULT 'markdown'",
            "type": "VARCHAR(64)",
            "updated_at": "TIMESTAMP WITH TIME ZONE",
        },
    }

    added: dict[str, set[str]] = {}
    for table_name, columns in additions.items():
        if table_name not in tables:
            continue
        existing = {
            column["name"] for column in inspect(connection).get_columns(table_name)
        }
        for column_name, definition in columns.items():
            if column_name not in existing:
                connection.execute(
                    text(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {definition}'
                    )
                )
                added.setdefault(table_name, set()).add(column_name)

    if "sources_json" in added.get("messages", set()):
        message_columns = {
            column["name"] for column in inspect(connection).get_columns("messages")
        }
        if "citations" in message_columns:
            connection.execute(
                text(
                    "UPDATE messages SET sources_json = citations "
                    "WHERE sources_json IS NULL AND citations IS NOT NULL"
                )
            )

    if "artifact_type" in added.get("artifacts", set()):
        artifact_columns = {
            column["name"] for column in inspect(connection).get_columns("artifacts")
        }
        if "type" in artifact_columns:
            connection.execute(
                text(
                    "UPDATE artifacts SET artifact_type = type "
                    "WHERE type IS NOT NULL"
                )
            )

    if "updated_at" in added.get("artifacts", set()):
        connection.execute(
            text("UPDATE artifacts SET updated_at = created_at WHERE updated_at IS NULL")
        )

    if "ingested_at" in added.get("knowledge_sources", set()):
        source_columns = {
            column["name"]
            for column in inspect(connection).get_columns("knowledge_sources")
        }
        if "created_at" in source_columns:
            connection.execute(
                text(
                    "UPDATE knowledge_sources SET ingested_at = created_at "
                    "WHERE ingested_at IS NULL"
                )
            )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        from app.models import chat_session, message, knowledge_source, artifact  # noqa: F401
        if database_url.get_backend_name() == "sqlite":
            await conn.run_sync(_upgrade_legacy_sqlite_schema)
        await conn.run_sync(Base.metadata.create_all)
        if database_url.get_backend_name() == "postgresql":
            await conn.run_sync(_upgrade_legacy_postgres_schema)
