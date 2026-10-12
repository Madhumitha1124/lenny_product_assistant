"""Pydantic request and response schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


# ── Sessions ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    provider: str = Field(default="ollama")
    model: str = Field(default="llama3.2:3b")


class SessionResponse(BaseModel):
    id: str
    title: str
    provider: str
    model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    provider: str | None
    model: str | None
    sources: list[SourceCitation] = []
    artifact_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=8000)
    provider: str = Field(default="ollama")
    model: str = Field(default="llama3.2:3b")

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be blank")
        return v.strip()


class SourceCitation(BaseModel):
    source_id: str
    title: str
    author: str | None = None
    source_url: str | None = None
    excerpt: str
    is_demo: bool = False


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    content: str
    provider: str
    model: str
    sources: list[SourceCitation] = []
    artifact_id: str | None = None


# ── Ingestion ─────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    file_path: str | None = None
    title: str = Field(default="Untitled Source", max_length=512)
    author: str | None = None
    source_url: str | None = None
    source_type: str = Field(default="transcript")
    is_demo: bool = False


class IngestResponse(BaseModel):
    source_id: str
    title: str
    chunks_indexed: int
    message: str


# ── Knowledge ─────────────────────────────────────────────────────────────────

class KnowledgeSourceResponse(BaseModel):
    id: str
    title: str
    author: str | None
    source_url: str | None
    source_type: str
    is_demo: bool
    chunk_count: int
    ingested_at: datetime

    model_config = {"from_attributes": True}


# ── Artifacts ─────────────────────────────────────────────────────────────────

class ArtifactCreate(BaseModel):
    session_id: str | None = None
    title: str = Field(default="Untitled", max_length=512)
    artifact_type: str = Field(default="markdown")
    prompt: str = Field(..., min_length=1)
    provider: str = Field(default="ollama")
    model: str = Field(default="llama3.2:3b")

    @field_validator("artifact_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"markdown", "html", "prd", "landing_page", "growth_plan", "strategy", "essay"}
        if v not in allowed:
            raise ValueError(f"artifact_type must be one of {allowed}")
        return v


class ArtifactResponse(BaseModel):
    id: str
    session_id: str | None
    title: str
    artifact_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Ship30 ────────────────────────────────────────────────────────────────────

class Ship30Request(BaseModel):
    topic: str = Field(..., min_length=3, max_length=512)
    session_id: str | None = None
    provider: str = Field(default="ollama")
    model: str = Field(default="llama3.2:3b")


class Ship30Response(BaseModel):
    artifact_id: str
    title: str
    content: str
    word_count: int
    sources: list[SourceCitation] = []


# ── Models ────────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    available: bool
    description: str = ""


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    default_provider: str
    default_model: str


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    ollama: str
    knowledge_sources: int | None
