"""SQLAlchemy ORM model for Artifact."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(512), default="Untitled Artifact")
    artifact_type: Mapped[str] = mapped_column(String(64))  # markdown | html | prd | landing_page | growth_plan | strategy
    legacy_type: Mapped[str | None] = mapped_column("type", String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_artifact_session", "session_id"),)
