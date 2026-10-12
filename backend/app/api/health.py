"""Health check endpoint."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from app.database.session import get_db
from app.retrieval.retrieval_service import retrieval_service
from app.core.config import get_settings
from app.schemas.schemas import HealthResponse

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["system"])
@router.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Report application and dependency health."""
    # Database
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(
            "database_health_check_failed",
            extra={"exception_type": type(exc).__name__},
        )
        db_status = "error: database unavailable"

    # Ollama
    ollama_status = "unavailable"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                ollama_status = f"ok ({len(models)} models)"
            else:
                ollama_status = f"error: HTTP {resp.status_code}"
    except httpx.ConnectError:
        ollama_status = "not running (run: ollama serve)"
    except Exception as e:
        ollama_status = f"error: {str(e)[:60]}"

    # Knowledge sources count
    kb_count = 0
    try:
        kb_count = retrieval_service.count()
    except Exception as e:
        logger.error(
            "knowledge_index_health_check_failed",
            extra={"exception_type": type(e).__name__},
        )
        kb_count = None

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=settings.app_version,
        database=db_status,
        ollama=ollama_status,
        knowledge_sources=kb_count,
    )
