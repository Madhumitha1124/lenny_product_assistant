# Sanitized implementation log

This log summarizes the implementation and verification work for the assignment. It intentionally excludes credentials, local environment values, and private transcript content.

## Audit findings

- The project already had a FastAPI backend, React/Vite frontend, session and message models, provider adapters, ChromaDB retrieval, artifact APIs, a Ship 30 endpoint, PostgreSQL configuration, and assignment documentation.
- The knowledge base contained synthetic demo fixtures, not genuine Lenny's Podcast or Newsletter transcripts. No transcript was added or fabricated.
- A legacy SQLite schema required `knowledge_sources.created_at`, which the ORM did not previously populate. This prevented fixture sources from being indexed.
- The existing chat history query was scoped by session ID, but New Chat needed to create a persistent backend session immediately.
- PostgreSQL and cloud-provider configuration existed, but initial local credentials were unavailable.
- The application fallback `DATABASE_URL` was SQLite even though PostgreSQL is required, and setup documentation required Docker.
- The backend uses project-owned `ConversationService` and `ModelRouter` orchestration; no third-party agent framework is a dependency.

## Changes and corrections

- Repaired compatibility for legacy SQLite source tables and added additive PostgreSQL schema compatibility. Existing source records are reindexed when needed.
- Improved retrieval filtering and added deterministic source references and an explicit no-evidence disclosure. Synthetic fixture citations are labeled as demo content.
- Routed chat, artifact, and essay generation through explicit provider selection and the tested Ollama fallback path. Unsupported providers are rejected. Provider failures are not saved as successful artifacts.
- Increased the default Ollama request timeout to reduce premature failures while a local model is loading.
- Made New Chat create a backend session, tied to the selected provider/model. Updated session timestamps as chats are used.
- Removed the SQLite application fallback so `DATABASE_URL` must be explicitly configured; documented PostgreSQL and native Windows startup, with Compose optional.
- Changed chat behavior so an unknown supplied session ID is reported instead of silently creating a different conversation.
- Replaced silent conversation/model/message loading and deletion failures with visible UI errors; malformed stored citation JSON is logged instead of ignored silently.
- Added HTML artifact preview sanitization, a sandboxed iframe, restrictive content policy, and source-metadata escaping.
- Added regression tests for citations, unsupported questions, session isolation, retrieval relevance, provider fallback, HTML citation escaping, and database persistence.
- An early regression run exposed a test assertion that expected a Markdown title without its intentional Markdown escaping. The assertion was corrected to check the escaped title and demo-source label.
- An earlier baseline test assumed Ollama was offline although the local service was running. The test now simulates a connection failure so it remains deterministic.
- Initial frontend commands ran from the parent folder and could not find the frontend package manifest. Rerunning them from the frontend folder completed successfully.

## Verification results

- Backend: `36 passed, 1 skipped`. The skipped test is the optional live PostgreSQL persistence test, which requires `TEST_POSTGRES_URL`.
- Frontend: production TypeScript/Vite build passed.
- Frontend lint: final run passed with zero warnings and zero errors after removing two unused imports from `App.tsx`.
- Pylance: no errors in the edited Python or TypeScript files.
- Browser check: New Chat appeared immediately, remained in the backend session list after a page reload, and could be reopened. The artifact-generation modal opened and closed successfully.
- Earlier live API check: health returned `ok`; SQLite database and Ollama were available; the index reported three entries. Those entries are synthetic demo sources, not genuine Lenny content. After making `DATABASE_URL` explicit, the existing listener on port 8001 did not return a health response within 30 seconds; it is not evidence of a successful PostgreSQL startup.
- Dependency audit: npm reported one high and one moderate vulnerability in the existing Vite/esbuild development-tool dependency chain. The suggested fix requires a major Vite upgrade, so it was not applied as an unrelated, potentially breaking dependency change.
- Environment check initially found no `.env` or `psql` on PATH. PostgreSQL 18 was already installed as a Windows service. After user-authorized local recovery, a dedicated role/database and ignored `.env` were configured without printing the generated credential.

## Not live-verified / remaining steps

- PostgreSQL authentication succeeded, the backend restarted against PostgreSQL, health returned `database: ok`, and the frontend proxy returned the same health response. The focused PostgreSQL persistence test passed (`1 passed`). A temporary API-created session also remained in the session list after a backend restart and was then deleted.
- Docker Compose was not run; Docker is not installed in the environment. It is optional for native Windows development.
- An early PostgreSQL-backed health response reported seven indexed chunks; these correspond to synthetic/demo sources. No genuine Lenny transcripts were added.
- Real Anthropic/OpenAI requests require valid backend-only API keys and were not sent. Offline tests verify selection, explicit fallback, and provider metadata; they do not prove that external credentials work.
- The repository does not include genuine Lenny transcripts. Upload authorized source material before presenting the application as grounded in Lenny's content.
- The npm audit findings should be reviewed before exposing the Vite development server to untrusted networks. Reassess Vite/Node compatibility before taking the major-version upgrade suggested by npm.
- The user confirmed the existing project-owned agent orchestration is acceptable; no external agent framework was added.
- The assignment form URL was not supplied, so the documentation directs the user to use the exact URL from their course portal rather than inventing one.

## Final remaining-requirements pass (2026-10-11)

- Confirmed the project contains no authorized genuine Lenny transcript/article files. The existing upload API accepts UTF-8 `.txt`, `.md`, and `.markdown` up to 10 MB; it now rejects empty/oversized content, accepts case-insensitive extensions, avoids storing temporary file paths, and reuses matching content hashes.
- Added an automated upload-to-index-to-retrieval/citation test using an explicitly synthetic fixture and mocked embeddings/vector collection. Reuploading the same text preserves the original source ID. A separate live check uploaded a temporary synthetic file, indexed it with the real embedding/vector pipeline, retrieved the same source ID/title/excerpt, then removed that test source and its chunks. No genuine-source provenance is claimed.
- Increased the local Ollama timeout to 600 seconds after a measured 191-word response took 53.7 seconds. The Ship 30 action was triggered through the actual UI with `llama3.2:3b`; it returned HTTP 503 at the 600-second timeout. After downloading `llama3.2:1b`, a second live API attempt also timed out. No live essay or word count is claimed.
- Generated real HTML/CSS through the Ollama artifact API, fetched the persisted artifact, and opened it in the actual browser Artifact Viewer. The initial model output included Markdown code fences; the backend now removes enclosing HTML fences and a regression test covers the case. A second live artifact contained CSS, checkboxes, no scripts or external resources, and no remaining fences. The preview iframe had an empty sandbox, restrictive CSP, and `no-referrer`. Its citations explicitly identified the indexed synthetic demo fixtures.
- Inspected the preserved legacy SQLite database read-only: 6 sessions, 14 messages, 3 knowledge-source rows, 0 artifacts. Made the migration insert-only and repeatable: it skips existing primary keys without overwriting, reports skipped rows, and checks destination row counts. Isolated SQLite tests cover reruns, an already populated target, preserved IDs/rows, and legacy column mapping. The migration was not run against live PostgreSQL.
- `/api/models` listed only Ollama; cloud adapters and provider fallback are covered by mocked tests, but no real cloud credentials or billable requests were available or attempted.
- Final backend run: 41 passed, 1 optional PostgreSQL integration test skipped. Frontend production build passed and Oxlint reported zero warnings/errors. A prior focused PostgreSQL persistence test passed against the configured local database. The Ollama timeout error now suggests a faster model or a larger configured timeout.
