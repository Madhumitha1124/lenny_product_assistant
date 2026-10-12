"""Conversation service — manages sessions, messages, and grounded chat."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.chat_session import ChatSession
from app.models.message import Message
from app.retrieval.retrieval_service import retrieval_service
from app.retrieval.source_references import append_source_references
from app.services.model_router import ModelRouter, with_provider_fallback_notice
from app.schemas.schemas import ChatResponse, SourceCitation

logger = logging.getLogger(__name__)

GROUNDED_SYSTEM_PROMPT = """You are the Lenny Growth Assistant, an AI expert in product management, growth strategy, and startup tactics.

Your knowledge comes from Lenny's Podcast and Newsletter transcripts provided in each message.

RULES:
1. Answer ONLY from the provided transcript evidence when it exists.
2. Clearly distinguish between evidence-based answers and your general knowledge.
3. If the knowledge base does not support an answer, say: "The available knowledge base doesn't have specific content on this topic. Here's my general perspective based on product management principles:"
4. Never invent quotes, guest names, or episode references.
5. When citing a source, use the exact title provided in the evidence block.
6. Be specific, actionable, and concise.
7. DEMO fixtures are labeled — treat them as illustrative examples, not authoritative Lenny content."""


class ConversationService:
    def __init__(self):
        self._router = ModelRouter()

    async def create_session(self, db: AsyncSession, title: str = "New Chat", provider: str = "ollama", model: str = "llama3.2:3b") -> ChatSession:
        session = ChatSession(title=title, provider=provider, model=model)
        db.add(session)
        await db.flush()
        return session

    async def get_session(self, db: AsyncSession, session_id: str) -> ChatSession | None:
        result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        return result.scalar_one_or_none()

    async def list_sessions(self, db: AsyncSession) -> list[ChatSession]:
        result = await db.execute(
            select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(50)
        )
        return list(result.scalars().all())

    async def delete_session(self, db: AsyncSession, session_id: str) -> bool:
        result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            return False
        await db.execute(delete(Message).where(Message.session_id == session_id))
        await db.delete(session)
        return True

    async def get_messages(self, db: AsyncSession, session_id: str) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def chat(
        self,
        db: AsyncSession,
        session_id: str | None,
        user_message: str,
        provider: str,
        model: str,
    ) -> ChatResponse:
        # Ensure session exists
        if session_id:
            session = await self.get_session(db, session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
        else:
            # Auto-title from first message
            title = user_message[:60] + ("…" if len(user_message) > 60 else "")
            session = await self.create_session(db, title=title, provider=provider, model=model)

        session_id = session.id
        session.provider = provider
        session.model = model
        session.updated_at = datetime.now(timezone.utc)

        # Retrieve grounded context
        citations = retrieval_service.retrieve(user_message, top_k=5)

        # Build evidence block
        if citations:
            evidence_parts = []
            for c in citations:
                demo_note = " ⚠️ [DEMO FIXTURE — illustrative only, not a real podcast source]" if c.is_demo else ""
                evidence_parts.append(f"**{c.title}**{demo_note}\n> {c.excerpt}")
            evidence_block = "TRANSCRIPT EVIDENCE:\n\n" + "\n\n".join(evidence_parts)
        else:
            evidence_block = "TRANSCRIPT EVIDENCE: None available. The knowledge base has no relevant content for this query."

        # Get conversation history (last 8 messages for context)
        history = await self.get_messages(db, session_id)
        history_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history[-8:]
        ]

        # Build messages list
        messages = history_messages + [
            {
                "role": "user",
                "content": f"{user_message}\n\n---\n{evidence_block}",
            }
        ]

        # Save user message
        user_msg = Message(
            session_id=session_id,
            role="user",
            content=user_message,
        )
        db.add(user_msg)
        await db.flush()

        # Call LLM
        llm_response = await self._router.complete_with_fallback(
            provider,
            model,
            messages,
            system_prompt=GROUNDED_SYSTEM_PROMPT,
        )

        if llm_response.error:
            assistant_content = (
                f"⚠️ **Model Error**\n\n{llm_response.error}\n\n"
                f"*Provider: {provider} | Model: {model}*"
            )
        elif citations:
            assistant_content = append_source_references(
                with_provider_fallback_notice(llm_response), citations
            )
        else:
            assistant_content = append_source_references(
                with_provider_fallback_notice(llm_response), []
            )

        # Save assistant message
        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            provider=llm_response.provider,
            model=llm_response.model,
            sources_json=json.dumps([c.model_dump() for c in citations]),
        )
        db.add(assistant_msg)
        await db.flush()

        # Update session title if it's the first real exchange
        if session.title in ("New Chat", "") and len(history) == 0:
            session.title = user_message[:60] + ("…" if len(user_message) > 60 else "")
            await db.flush()

        return ChatResponse(
            session_id=session_id,
            message_id=assistant_msg.id,
            content=assistant_content,
            provider=llm_response.provider,
            model=llm_response.model,
            sources=citations,
        )


conversation_service = ConversationService()
