# Architecture

## System architecture

The app uses a React/Vite frontend and a FastAPI backend. The frontend calls JSON endpoints through the Vite proxy. The backend uses SQLAlchemy async sessions for durable application data, ChromaDB for vectors, and a provider router for Ollama and optional cloud models.

## API contracts

Core endpoints include `/api/health`, `/api/models`, `/api/sessions`, `/api/chat`, `/api/ingest`, `/api/knowledge/sources`, `/api/skills/ship30`, and artifact endpoints. Requests and responses use Pydantic models so invalid inputs fail early and consistently.

## Database schema and migration

The application requires `DATABASE_URL`; the documented/default configuration is PostgreSQL with `asyncpg`. The primary Windows setup uses a native PostgreSQL service; Docker Compose is optional and stores PostgreSQL files in a named volume. SQLite with `aiosqlite` is selected explicitly by isolated tests and is not the application default. Startup applies additive schema compatibility changes without dropping existing fields. The explicit SQLite-to-PostgreSQL helper inserts recognized rows whose primary keys are missing and leaves existing PostgreSQL rows untouched, so a rerun does not duplicate or overwrite records. It validates destination row counts after each table copy.

Schema initialization currently uses `create_all` and additive compatibility upgrades; the copy helper is not a versioned Alembic migration system. Back up both databases before migrating and review the copied/already-present counts. Existing matching IDs are preserved as-is.

## Ingestion and retrieval flow

Authorized UTF-8 TXT/Markdown uploads up to 10 MB are recorded in PostgreSQL and split into overlapping text chunks. Sentence Transformers embeds the chunks and ChromaDB stores them in a persistent Compose volume. Retrieval ranks cosine-distance matches, discards low-relevance chunks, and returns source IDs, titles, optional URLs, and excerpts. Content hashes prevent duplicate source records when the same text is uploaded again. Existing database content is re-indexed on startup to repair an interrupted or missing vector index. Built-in demo documents are synthetic and explicitly marked.

Chat and Ship 30 workflows send retrieved evidence to the selected provider. The application independently appends source references to generated content; when no evidence is retrieved it adds a disclosure that the response is general guidance and not attributed to Lenny's material. No real Lenny transcript data is bundled with the project.

## Agent routing and skill boundaries

The backend `ConversationService` assembles retrieved evidence, isolated session history, and the grounded system prompt; `ModelRouter` selects Ollama, Anthropic, or OpenAI. This is project-owned orchestration, not a third-party agent framework integration. API keys are read from backend environment variables only. If a configured cloud call fails, the router attempts the configured Ollama model when available and records the actual provider in the response; fallback use is disclosed in generated content. Unknown providers are rejected. Ship 30 is a dedicated essay workflow that retrieves evidence and persists the generated essay as an artifact.

## Model switching

The default provider is configured through `DEFAULT_LLM_PROVIDER` and the app checks provider readiness before routing a request. The app displays a provider/model indicator in the UI and does not silently switch providers without returning a clear status.

## Artifact security

Generated HTML is sanitized with DOMPurify and rendered in an iframe sandbox with an opaque origin, no scripts, no forms, and a restrictive Content Security Policy. HTML is never injected into the application document. Markdown, code/source view, copy, and download actions remain available in the artifact panel.

## Deployment topology

The optional Compose setup runs PostgreSQL, FastAPI, and Vite. Compose waits for PostgreSQL's health check before starting the backend, persists PostgreSQL and ChromaDB in named volumes, and routes browser API traffic through Vite to FastAPI. Ollama runs on the host and is reached by the backend container via `host.docker.internal`. The primary Windows development flow runs FastAPI and Vite directly against a native PostgreSQL service.

## Known limitations

- Retrieval quality depends on the relevance of authorized sources supplied by the user.
- Live cloud-provider calls require valid API keys and billing; automated tests mock provider network calls.
- PostgreSQL integration tests require an explicitly configured `TEST_POSTGRES_URL`.
- Demo fixtures are synthetic and should not be mistaken for genuine Lenny transcripts.
