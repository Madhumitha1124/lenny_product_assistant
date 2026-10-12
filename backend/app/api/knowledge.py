"""Knowledge ingestion and sources API router."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.ingestion.ingestion_service import ingestion_service
from app.models.knowledge_source import KnowledgeSource
from app.schemas.schemas import IngestRequest, IngestResponse, KnowledgeSourceResponse

router = APIRouter(prefix="/api", tags=["knowledge"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/ingest", response_model=IngestResponse)
async def ingest_file_path(body: IngestRequest, db: AsyncSession = Depends(get_db)):
    """Ingest a transcript file by local path."""
    if not body.file_path:
        raise HTTPException(status_code=422, detail="file_path is required")
    try:
        source = await ingestion_service.ingest_file(
            db=db,
            file_path=body.file_path,
            title=body.title,
            author=body.author,
            source_url=body.source_url,
            source_type=body.source_type,
            is_demo=body.is_demo,
        )
        return IngestResponse(
            source_id=source.id,
            title=source.title,
            chunks_indexed=source.chunk_count,
            message=f"Successfully ingested '{source.title}' with {source.chunk_count} chunks.",
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)[:200]}")


@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    title: str = Form(default="Uploaded Source"),
    author: str = Form(default=""),
    source_url: str = Form(default=""),
    source_type: str = Form(default="transcript"),
    is_demo: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Upload a TXT/MD file for ingestion."""
    filename = file.filename or ""
    suffix = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
    if suffix not in {"txt", "md", "markdown"}:
        raise HTTPException(
            status_code=422,
            detail="Only .txt, .md, and .markdown files are supported",
        )

    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded files must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller",
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=422,
                detail="Uploaded text files must use UTF-8 encoding",
            ) from e
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="Uploaded file is empty",
            )

        source = await ingestion_service.ingest_text_direct(
            db=db,
            text=text,
            title=title, author=author or None,
            source_url=source_url or None,
            source_type=source_type, is_demo=is_demo,
        )
        return IngestResponse(
            source_id=source.id, title=source.title,
            chunks_indexed=source.chunk_count,
            message=f"Uploaded and ingested '{source.title}' ({source.chunk_count} chunks).",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/knowledge/sources", response_model=list[KnowledgeSourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all ingested knowledge sources."""
    result = await db.execute(
        select(KnowledgeSource).order_by(KnowledgeSource.ingested_at.desc())
    )
    return [KnowledgeSourceResponse.model_validate(s) for s in result.scalars().all()]
