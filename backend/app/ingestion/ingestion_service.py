"""Ingestion service — ingest local TXT/MD files into the knowledge base."""
from __future__ import annotations
import hashlib
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge_source import KnowledgeSource
from app.retrieval.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)


class IngestionService:
    @staticmethod
    def _index_source(source: KnowledgeSource, text: str) -> None:
        metadata = {
            "source_id": source.id,
            "title": source.title,
            "author": source.author or "",
            "source_url": source.source_url or "",
            "is_demo": source.is_demo,
            "content_hash": source.content_hash or "",
        }
        source.chunk_count = retrieval_service.ingest_text(text, source.id, metadata)

    async def ingest_file(
        self,
        db: AsyncSession,
        file_path: str,
        title: str = "Untitled",
        author: str | None = None,
        source_url: str | None = None,
        source_type: str = "transcript",
        is_demo: bool = False,
    ) -> KnowledgeSource:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
            raise ValueError(f"Unsupported file type: {path.suffix}. Only .txt and .md files are supported.")

        text = path.read_text(encoding="utf-8", errors="replace")
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # Deduplication check
        existing = await db.execute(
            select(KnowledgeSource).where(KnowledgeSource.content_hash == content_hash)
        )
        existing_source = existing.scalar_one_or_none()
        if existing_source:
            self._index_source(existing_source, text)
            await db.flush()
            logger.info(f"Reused and indexed source (hash match): {existing_source.title}")
            return existing_source

        # Create DB record
        source = KnowledgeSource(
            title=title,
            author=author,
            source_url=source_url,
            content=text,
            file_path=str(path.resolve()),
            source_type=source_type,
            is_demo=is_demo,
            content_hash=content_hash,
        )
        db.add(source)
        await db.flush()  # Get the generated ID

        self._index_source(source, text)
        await db.flush()

        logger.info(f"Ingested: {title} ({source.chunk_count} chunks)")
        return source

    async def ingest_text_direct(
        self,
        db: AsyncSession,
        text: str,
        title: str,
        author: str | None = None,
        source_url: str | None = None,
        source_type: str = "transcript",
        is_demo: bool = False,
    ) -> KnowledgeSource:
        """Ingest raw text content directly (no file required)."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        existing = await db.execute(
            select(KnowledgeSource).where(KnowledgeSource.content_hash == content_hash)
        )
        if existing_source := existing.scalar_one_or_none():
            self._index_source(existing_source, text)
            await db.flush()
            return existing_source

        source = KnowledgeSource(
            title=title,
            author=author,
            source_url=source_url,
            content=text,
            source_type=source_type,
            is_demo=is_demo,
            content_hash=content_hash,
        )
        db.add(source)
        await db.flush()

        self._index_source(source, text)
        await db.flush()
        return source


ingestion_service = IngestionService()
