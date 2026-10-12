"""FastAPI application entry point."""
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.database.session import init_db
from app.api import health, sessions, chat, knowledge, models_artifacts

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await init_db()
    logger.info("Database initialized")

    # Auto-ingest demo fixtures on first run
    try:
        from app.ingestion.demo_fixtures import ingest_demo_fixtures
        await ingest_demo_fixtures()
        logger.info("Demo fixtures ready")
    except Exception as e:
        logger.warning(f"Demo fixture ingestion skipped: {e}")

    yield
    logger.info("Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered research and writing assistant for product managers and growth teams.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(models_artifacts.router)


@app.get("/api/docs", include_in_schema=False)
async def legacy_docs():
    """Keep the previous documentation URL working."""
    return RedirectResponse(url="/docs", status_code=307)


@app.get("/", tags=["system"])
async def root():
    return {"message": f"{settings.app_name} API", "version": settings.app_version, "docs": "/docs"}