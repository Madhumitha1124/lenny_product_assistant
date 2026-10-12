"""Models, Artifacts, and Ship30 API routers."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.services.model_router import ModelRouter
from app.artifacts.artifact_service import artifact_service
from app.skills.ship30_skill import ship30_skill
from app.models.artifact import Artifact
from app.schemas.schemas import (
    ModelsResponse, ModelInfo,
    ArtifactCreate, ArtifactResponse,
    Ship30Request, Ship30Response,
)
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api", tags=["models", "artifacts", "skills"])
_model_router = ModelRouter()
logger = logging.getLogger(__name__)


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """List all available LLM models and their availability status."""
    raw_models = await _model_router.get_available_models()
    models = [ModelInfo(**m) for m in raw_models]
    return ModelsResponse(
        models=models,
        default_provider=settings.default_llm_provider,
        default_model=settings.ollama_model,
    )


@router.post("/artifacts", response_model=ArtifactResponse)
async def create_artifact(body: ArtifactCreate, db: AsyncSession = Depends(get_db)):
    """Generate a new artifact (Markdown, HTML, PRD, etc.)."""
    try:
        return await artifact_service.generate(
            db=db,
            prompt=body.prompt,
            artifact_type=body.artifact_type,
            title=body.title,
            session_id=body.session_id,
            provider=body.provider,
            model=body.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.warning(
            "artifact_provider_failed",
            extra={"provider": body.provider, "exception_type": type(e).__name__},
        )
        raise HTTPException(status_code=503, detail=f"Artifact generation unavailable: {e}")
    except Exception as e:
        logger.error(
            "artifact_generation_failed",
            extra={"provider": body.provider, "exception_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Artifact generation failed")


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve an artifact by ID."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    return ArtifactResponse.model_validate(artifact)


@router.post("/skills/ship30", response_model=Ship30Response)
async def generate_ship30_essay(body: Ship30Request, db: AsyncSession = Depends(get_db)):
    """Generate a Ship 30 for 30 style essay on the given topic."""
    try:
        return await ship30_skill.generate_essay(
            db=db,
            topic=body.topic,
            provider=body.provider,
            model=body.model,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.warning(
            "ship30_provider_failed",
            extra={"provider": body.provider, "exception_type": type(e).__name__},
        )
        raise HTTPException(status_code=503, detail=f"Essay generation unavailable: {e}")
    except Exception as e:
        logger.error(
            "ship30_generation_failed",
            extra={"provider": body.provider, "exception_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Essay generation failed")
