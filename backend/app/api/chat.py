"""Chat API router."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.conversation_service import conversation_service
from app.schemas.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message and receive a grounded response with source citations."""
    try:
        return await conversation_service.chat(
            db=db,
            session_id=body.session_id,
            user_message=body.message,
            provider=body.provider,
            model=body.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(
            "chat_processing_failed",
            extra={
                "exception_type": type(e).__name__,
                "session_id": body.session_id,
                "provider": body.provider,
            },
        )
        raise HTTPException(status_code=500, detail="Internal server error during chat processing")
