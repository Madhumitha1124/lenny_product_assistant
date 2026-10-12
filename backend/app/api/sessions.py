"""Sessions API router."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.database.session import get_db
from app.services.conversation_service import conversation_service
from app.schemas.schemas import SessionCreate, SessionResponse, MessageResponse, SourceCitation

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    sessions = await conversation_service.list_sessions(db)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = await conversation_service.create_session(db, title=body.title, provider=body.provider, model=body.model)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await conversation_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    messages = await conversation_service.get_messages(db, session_id)
    result = []
    for m in messages:
        sources = []
        if m.sources_json:
            try:
                raw = json.loads(m.sources_json)
                sources = [SourceCitation(**s) for s in raw]
            except (TypeError, ValueError):
                logger.warning(
                    "invalid_message_sources_json",
                    extra={"message_id": m.id, "session_id": session_id},
                )
        result.append(MessageResponse(
            id=m.id, session_id=m.session_id, role=m.role, content=m.content,
            provider=m.provider, model=m.model, sources=sources,
            artifact_id=m.artifact_id, created_at=m.created_at,
        ))
    return result


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await conversation_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
