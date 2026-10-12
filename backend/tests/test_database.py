"""Tests for database URL handling and SQLite data migration."""
from __future__ import annotations

import uuid
import os

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.session import (
    Base,
    _upgrade_legacy_sqlite_schema,
    normalize_async_database_url,
)
from app.models import ChatSession, Message, KnowledgeSource, Artifact  # noqa: F401
from scripts.migrate_sqlite_to_postgres import migrate


def test_plain_postgresql_url_uses_asyncpg():
    normalized = normalize_async_database_url(
        "postgresql://lenny:local-password@127.0.0.1:5432/lenny_assistant"
    )
    assert normalized.startswith("postgresql+asyncpg://")


@pytest.mark.asyncio
async def test_migrate_copies_data_to_empty_async_sqlite_target(tmp_path):
    source_url = f"sqlite+aiosqlite:///{tmp_path / 'source.db'}"
    target_url = f"sqlite+aiosqlite:///{tmp_path / 'target.db'}"
    source_engine = create_async_engine(source_url)
    assert {
        model.__tablename__
        for model in (Artifact, ChatSession, KnowledgeSource, Message)
    } <= set(Base.metadata.tables)

    async with source_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_id = str(uuid.uuid4())
    async with source_engine.begin() as connection:
        await connection.execute(
            ChatSession.__table__.insert().values(
                id=session_id,
                title="Migration test",
                provider="ollama",
                model="llama3.2:3b",
            )
        )

    await source_engine.dispose()

    counts = await migrate(source_url, target_url)
    target_engine = create_async_engine(target_url)
    try:
        async with target_engine.connect() as connection:
            row_count = await connection.scalar(
                select(func.count()).select_from(ChatSession.__table__)
            )
        assert counts["chat_sessions"] == 1
        assert row_count == 1
        second_run = await migrate(source_url, target_url)
        assert second_run["chat_sessions"] == 0
        assert second_run["chat_sessions_skipped_existing"] == 1
    finally:
        await target_engine.dispose()


@pytest.mark.asyncio
async def test_migrate_preserves_existing_rows_and_copies_missing_rows(tmp_path):
    source_url = f"sqlite+aiosqlite:///{tmp_path / 'source.db'}"
    target_url = f"sqlite+aiosqlite:///{tmp_path / 'target.db'}"
    source_engine = create_async_engine(source_url)
    target_engine = create_async_engine(target_url)
    session_id = str(uuid.uuid4())

    async with source_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            ChatSession.__table__.insert().values(
                id=session_id,
                title="Original SQLite title",
                provider="ollama",
                model="llama3.2:3b",
            )
        )
        await connection.execute(
            Message.__table__.insert().values(
                id="migration-message",
                session_id=session_id,
                role="user",
                content="Preserved message",
            )
        )
    async with target_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            ChatSession.__table__.insert().values(
                id=session_id,
                title="Existing PostgreSQL title",
                provider="ollama",
                model="llama3.2:3b",
            )
        )
        await connection.execute(
            ChatSession.__table__.insert().values(
                id="destination-only",
                title="Do not remove",
                provider="ollama",
                model="llama3.2:3b",
            )
        )

    await source_engine.dispose()
    try:
        counts = await migrate(source_url, target_url)
        assert counts["chat_sessions"] == 0
        assert counts["chat_sessions_skipped_existing"] == 1
        assert counts["messages"] == 1

        rerun_counts = await migrate(source_url, target_url)
        assert rerun_counts["messages"] == 0
        assert rerun_counts["messages_skipped_existing"] == 1

        async with target_engine.connect() as connection:
            sessions = (
                await connection.execute(
                    select(ChatSession.id, ChatSession.title).order_by(ChatSession.id)
                )
            ).all()
            message_count = await connection.scalar(
                select(func.count()).select_from(Message.__table__)
            )
        assert (session_id, "Existing PostgreSQL title") in sessions
        assert ("destination-only", "Do not remove") in sessions
        assert message_count == 1
    finally:
        await target_engine.dispose()


@pytest.mark.asyncio
async def test_migrate_maps_legacy_sqlite_column_names(tmp_path):
    source_url = f"sqlite+aiosqlite:///{tmp_path / 'legacy.db'}"
    target_url = f"sqlite+aiosqlite:///{tmp_path / 'postgres-target.db'}"
    source_engine = create_async_engine(source_url)
    async with source_engine.begin() as connection:
        await connection.execute(
            text(
                "CREATE TABLE chat_sessions (id VARCHAR(36) PRIMARY KEY, "
                "title VARCHAR(255), provider VARCHAR(64), model VARCHAR(128), "
                "created_at DATETIME, updated_at DATETIME)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE messages (id VARCHAR(36) PRIMARY KEY, "
                "session_id VARCHAR(36), role VARCHAR(16), content TEXT, "
                "citations TEXT, created_at DATETIME)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE artifacts (id VARCHAR(36) PRIMARY KEY, "
                "title VARCHAR(512), type VARCHAR(64), content TEXT, "
                "session_id VARCHAR(36), created_at DATETIME)"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO chat_sessions VALUES "
                "('session-1', 'Legacy', 'ollama', 'llama3.2:3b', "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO messages VALUES "
                "('message-1', 'session-1', 'assistant', 'answer', "
                "'[{\"title\":\"old citation\"}]', '2026-01-01 00:00:00')"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO artifacts VALUES "
                "('artifact-1', 'Legacy artifact', 'html', '<h1>Hi</h1>', "
                "'session-1', '2026-01-01 00:00:00')"
            )
        )
    await source_engine.dispose()

    await migrate(source_url, target_url)
    target_engine = create_async_engine(target_url)
    try:
        async with target_engine.connect() as connection:
            message = (
                await connection.execute(
                    select(Message.__table__).where(Message.id == "message-1")
                )
            ).mappings().one()
            artifact = (
                await connection.execute(
                    select(Artifact.__table__).where(Artifact.id == "artifact-1")
                )
            ).mappings().one()
        assert message["sources_json"] == '[{"title":"old citation"}]'
        assert artifact["artifact_type"] == "html"
    finally:
        await target_engine.dispose()


def test_legacy_sqlite_schema_upgrade_preserves_values(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-schema.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE artifacts (id VARCHAR(36) PRIMARY KEY, "
                    "title VARCHAR(512), type VARCHAR(64), content TEXT, "
                    "session_id VARCHAR(36), created_at DATETIME)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE knowledge_sources (id VARCHAR(36) PRIMARY KEY, "
                    "title VARCHAR(512), source_type VARCHAR(64), is_demo BOOLEAN, "
                    "chunk_count INTEGER)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO artifacts VALUES "
                    "('artifact-1', 'Old title', 'html', '<h1>Hi</h1>', "
                    "NULL, '2026-01-01 00:00:00')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO knowledge_sources VALUES "
                    "('source-1', 'Legacy source', 'demo_fixture', 1, 0)"
                )
            )
            _upgrade_legacy_sqlite_schema(connection)
            columns = {
                column["name"] for column in inspect(connection).get_columns("artifacts")
            }
            row = connection.execute(
                text("SELECT artifact_type, updated_at FROM artifacts WHERE id = :id"),
                {"id": "artifact-1"},
            ).one()
            source_columns = {
                column["name"]
                for column in inspect(connection).get_columns("knowledge_sources")
            }
            source_created_at = connection.execute(
                text("SELECT created_at FROM knowledge_sources WHERE id = 'source-1'")
            ).scalar_one()
        assert {"artifact_type", "updated_at"} <= columns
        assert row.artifact_type == "html"
        assert row.updated_at == "2026-01-01 00:00:00"
        assert "created_at" in source_columns
        assert source_created_at is not None
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_ingestion_populates_required_legacy_created_at(tmp_path):
    from app.ingestion.ingestion_service import IngestionService
    from app.retrieval.retrieval_service import retrieval_service
    from app.models.knowledge_source import KnowledgeSource
    from unittest.mock import patch

    database_engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'legacy-source.db'}"
    )
    try:
        async with database_engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE knowledge_sources ("
                    "id VARCHAR(36) PRIMARY KEY, title VARCHAR(512) NOT NULL, "
                    "author VARCHAR(256), source_url TEXT, content TEXT, file_path TEXT, "
                    "source_type VARCHAR(64) NOT NULL, is_demo BOOLEAN NOT NULL, "
                    "chunk_count INTEGER NOT NULL, content_hash VARCHAR(64), "
                    "created_at DATETIME NOT NULL, ingested_at DATETIME NOT NULL)"
                )
            )

        session_factory = async_sessionmaker(database_engine, expire_on_commit=False)
        async with session_factory() as db:
            with patch.object(retrieval_service, "ingest_text", return_value=2):
                source = await IngestionService().ingest_text_direct(
                    db=db,
                    text="A transcript about retaining customers.",
                    title="Retention transcript",
                )
                await db.commit()

        assert source.chunk_count == 2
        assert source.created_at is not None
    finally:
        await database_engine.dispose()


@pytest.mark.asyncio
async def test_file_database_preserves_session_messages_after_reconnect(tmp_path):
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import ChatSession, Message

    database_url = f"sqlite+aiosqlite:///{tmp_path / 'persistent.db'}"
    first_engine = create_async_engine(database_url)
    session_id = str(uuid.uuid4())
    try:
        async with first_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncSession(first_engine, expire_on_commit=False) as db:
            db.add(ChatSession(id=session_id, title="Persistent session"))
            await db.flush()
            db.add(Message(
                session_id=session_id,
                role="user",
                content="Persist across a backend restart",
            ))
            await db.commit()
    finally:
        await first_engine.dispose()

    reopened_engine = create_async_engine(database_url)
    try:
        async with reopened_engine.connect() as connection:
            row = (
                await connection.execute(
                    select(Message.__table__).where(Message.session_id == session_id)
                )
            ).mappings().one()
        assert row["content"] == "Persist across a backend restart"
    finally:
        await reopened_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_persists_session_messages_when_test_database_is_configured():
    raw_url = os.environ.get("TEST_POSTGRES_URL")
    if not raw_url:
        pytest.skip("Set TEST_POSTGRES_URL to run the PostgreSQL persistence integration test")

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import ChatSession, Message

    postgres_engine = create_async_engine(normalize_async_database_url(raw_url))
    session_id = str(uuid.uuid4())
    try:
        async with postgres_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncSession(postgres_engine, expire_on_commit=False) as db:
            db.add(ChatSession(id=session_id, title="PostgreSQL persistence test"))
            await db.flush()
            db.add(Message(
                session_id=session_id,
                role="user",
                content="Persisted in PostgreSQL",
            ))
            await db.commit()
        async with AsyncSession(postgres_engine) as db:
            message = (
                await db.execute(
                    select(Message).where(Message.session_id == session_id)
                )
            ).scalar_one()
            assert message.content == "Persisted in PostgreSQL"
    finally:
        async with AsyncSession(postgres_engine) as db:
            await db.execute(delete(Message).where(Message.session_id == session_id))
            await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
            await db.commit()
        await postgres_engine.dispose()
