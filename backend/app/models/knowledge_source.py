"""SQLAlchemy ORM model for KnowledgeSource."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="transcript")  # transcript | newsletter | demo_fixture
    is_demo: Mapped[bool] = mapped_column(default=False)
    chunk_count: Mapped[int] = mapped_column(default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # for dedup
    # Older local databases require this legacy column on inserts.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_source_hash", "content_hash"),)
