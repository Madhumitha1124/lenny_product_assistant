::: {align="center"}
🚀 Lenny Growth Assistant
Ask better product questions. Find source-backed insights. Turn ideas into useful content.
A full-stack AI research and writing assistant built with React +
Vite, FastAPI, PostgreSQL, ChromaDB, and Ollama.
Features · Quick start ·
Workflows · Tests ·
Troubleshooting
:::
---
> \[!IMPORTANT\] **Knowledge-base status:** this repository contains
> synthetic demo examples, not genuine Lenny's Podcast or Newsletter
> transcripts. Upload only content you are authorized to store before
> demonstrating real source grounding.
🗺️ Start here
---
If you want to...                   Jump to
---
Install and run locally without     Quick start
Docker
Understand the architecture         How it works
Add authorized source files         Add knowledge
sources
Try chat, Ship 30, and artifacts    Try it
Run automated checks                Tests
Fix common errors                   Troubleshooting
Prepare your assignment submission  Submission
checklist
✨ Features
💬 Separate chat sessions with persisted conversation history.
🔎 Retrieval-augmented answers using indexed text and available
source details.
✍️ Ship 30 for 30-style writing targeting approximately 1,250
words.
🧩 Markdown and HTML/CSS artifacts with an in-app viewer.
🖥️ Local model inference through Ollama for the demo.
☁️ Optional Anthropic and OpenAI configuration through backend
environment variables.
🧪 Automated tests and manual test instructions for validating
core flows.
Technology stack
---
Layer                               Technology
---
Frontend                            React, Vite
Backend API                         FastAPI
Session and source metadata         PostgreSQL
Vector index                        ChromaDB
Local LLM                           Ollama
Embeddings                          Sentence Transformers
(`all-MiniLM-L6-v2`, as configured)
Agent architecture note: the current backend coordinates retrieval,
prompt construction, provider selection, citations, and persistence
through its own `ConversationService` and `ModelRouter`. It does not
currently use the Anthropic Claude Agent SDK or Pi Coding Agent (nor
LangChain/PydanticAI). This is a gap relative to the assignment's named
agent-framework requirement.
🧱 How it works
``` mermaid
flowchart LR
    U[React UI] --> API[FastAPI]
    API --> C[Conversation Service]
    C --> R[Model Router]
    C --> RET[Retriever]
    RET --> V[(ChromaDB)]
    RET --> DB[(PostgreSQL sources)]
    C --> S[(PostgreSQL sessions/messages)]
    R --> O[Ollama]
    R -. optional .-> CLOUD[Anthropic / OpenAI]
    C --> ART[Artifact generation + sanitization]
    ART --> VIEW[Sandboxed Artifact Viewer]
```
A typical request goes from the browser to FastAPI. The backend loads
session context, retrieves relevant indexed text, builds a prompt, calls
the selected model, and returns the answer with available source
information. Artifact requests use the artifact generation and preview
workflow.
⚡ Quick start (Windows)
Prerequisites
Install: - Python 3.11 - Node.js
20+ - PostgreSQL 16 for
Windows - Ollama for
Windows
Docker is optional; these instructions use native Windows PostgreSQL.
1. Create a PostgreSQL role and database
Start the PostgreSQL Windows service. Open SQL Shell (psql) from the
Start menu and connect to host `127.0.0.1`, port `5432`, database
`postgres`, user `postgres`. Run:
``` sql
CREATE ROLE lenny WITH LOGIN PASSWORD 'change-me-local-only';
CREATE DATABASE lenny_assistant OWNER lenny;
```
If the `lenny` role already exists, set its password instead:
``` sql
ALTER ROLE lenny WITH PASSWORD 'your-local-password';
```
Exit with `\q`.
> \[!WARNING\] These are sample local credentials. Replace them with
> your own local password and never commit secrets.
2. Configure `.env`
Open PowerShell:
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```
Set the database URLs and local provider to match your setup:
``` dotenv
DATABASE_URL=postgresql+asyncpg://lenny:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/lenny_assistant
POSTGRES_DATABASE_URL=postgresql+asyncpg://lenny:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/lenny_assistant
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```
Replace the password placeholder. URL-encode special characters in the
password. The backend reads `.env`, not `.env.example`. Keep `.env`
private.
3. Install and run Ollama
``` powershell
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama list
```
Ollama must be running. If it is not already running as a Windows
application/service, open a separate terminal and run:
``` powershell
ollama serve
```
Do not start a second server if Ollama is already listening on port
`11434`.
> \[!TIP\] For a CPU-only demo, `llama3.2:1b` may respond faster than
> `llama3.2:3b`. Essay generation can still take several minutes; test
> the selected model before recording your demo.
4. Start the backend
Open a new PowerShell terminal:
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"

if (!(Test-Path .\backend\.venv\Scripts\python.exe)) {
    Set-Location .\backend
    py -3.11 -m venv .venv
    Set-Location ..
}

Set-Location .\backend
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
Keep the terminal open. The first startup may download the embedding
model. A database connection failure must be fixed before the backend
can operate correctly.
5. Start the frontend
Open another PowerShell terminal:
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\frontend"
npm ci
npm run dev
```
Open: - App: http://localhost:5173/ - API health:
http://localhost:8001/api/health - Interactive API docs:
http://localhost:8001/docs
Keep PostgreSQL, Ollama, the backend, and frontend running.
🧭 Try it
💬 Chat and sessions
Open the app and start a new chat.
Ask a specific product or growth question.
Ask a follow-up to check session context.
Start another chat and verify that its context is independent.
📚 Add knowledge sources
Uploads accept UTF-8 `.txt` or `.md` files through the ingestion API.
Upload only content you have permission to store.
Open http://localhost:8001/docs.
Expand `POST /api/ingest/upload` and select Try it out.
Choose the source file and provide its actual title and original
URL, if available.
Execute the request and note the source ID and indexed chunk count.
Check `GET /api/knowledge/sources`.
Ask a question answerable from the uploaded text. Check the source
title, ID, excerpt, and URL in the answer.
Limits: UTF-8 text, up to 10 MB. Identical content may reuse an
existing source ID. Do not invent source URLs or describe synthetic text
as genuine Lenny content.
✍️ Ship 30 for 30-style essay
Select a working Ollama model in the UI.
Click Ship 30.
Wait for generation; local models may take several minutes.
Check the hook, narrative progression, headings, selective bolding,
useful takeaway, and approximate 1,250-word target.
Verify that source-based claims are supported by retrieved material.
Confirm the essay is saved and opens in the Artifact Viewer.
If generation times out, test a short chat first, select `llama3.2:1b`,
and inspect the backend terminal before retrying.
🧩 Artifact Viewer
Ask the assistant to create a small Markdown document or HTML/CSS
page.
Open the Artifact Viewer and confirm it renders inside the app.
Inspect, copy, or download the artifact if those controls are
available.
Treat generated HTML as untrusted. The viewer is intended to use
sanitization and a sandboxed iframe; review the code before using it
with sensitive data.
🔧 Configuration
---
Variable                            Purpose
---
`DATABASE_URL`                      Main SQLAlchemy database URL
`POSTGRES_DATABASE_URL`             PostgreSQL URL used by
integration/migration workflows
`DEFAULT_LLM_PROVIDER`              Default provider; use `ollama` for
the local demo
`OLLAMA_BASE_URL`                   Ollama server URL
`OLLAMA_MODEL`                      Default local model
`OLLAMA_TIMEOUT`                    Timeout for supported model calls
`ANTHROPIC_API_KEY`                 Optional Anthropic key
`OPENAI_API_KEY`                    Optional OpenAI key
`CHROMA_PERSIST_DIR`                ChromaDB persistence directory
`EMBEDDING_MODEL`                   Sentence Transformers embedding
model
Use `.env.example` as the source of truth if variable names differ in
your checkout. Restart the backend after editing `.env`. Never put API
keys in `VITE_*` variables. Real cloud-provider calls have not been
verified here and require valid credentials.
🧪 Tests
Backend
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\backend"
& .\.venv\Scripts\python.exe -m pytest -q
```
Frontend build and lint
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\frontend"
npm run build
npm run lint
```
Optional PostgreSQL integration test
Use a disposable test database, not your only copy of important data. In
SQL Shell:
``` sql
CREATE DATABASE lenny_assistant_test OWNER lenny;
```
Then run in PowerShell:
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\backend"
$env:TEST_POSTGRES_URL = "postgresql+asyncpg://lenny:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/lenny_assistant_test"
& .\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TEST_POSTGRES_URL
```
See also: - `docs/manual-test-plan.md` -
`docs/final-requirements-audit.md` -
`docs/implementation-log.md`
🐳 Optional Docker Compose
Docker is not required for the native Windows workflow. If Docker
Desktop is working:
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```
Compose uses its own database service and maps PostgreSQL to host port
`5433`; the backend container reaches Windows-host Ollama using
`host.docker.internal`.
Stop with `Ctrl+C` or `docker compose stop`. `docker compose down`
preserves named volumes. Do not use `docker compose down -v` unless
you intend to delete the Compose database and vector index.
🛠 Troubleshooting
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}PostgreSQL connection fails`</strong>`{=html}
```{=html}
</summary>
```
Check that the Windows PostgreSQL service is running.
Verify the `lenny` role, `lenny_assistant` database, port, username,
and password.
URL-encode special characters in the database password.
Read the backend terminal for the actual connection error.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Ollama is unavailable or the model is
missing`</strong>`{=html}
```{=html}
</summary>
```
Run `ollama list`. If the model is missing, run
`ollama pull llama3.2:1b`. Make sure the Ollama service is available at
`http://127.0.0.1:11434`. Do not launch a second `ollama serve` if the
service is already running.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Ship 30 takes too long`</strong>`{=html}
```{=html}
</summary>
```
Test a short chat prompt first.
Select `llama3.2:1b` for potentially faster generation.
Check the backend terminal for the actual timeout/error.
Avoid repeatedly clicking while a request is still running.
Check essay quality and length; a successful HTTP response alone
does not prove the writing requirement is met.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}The frontend cannot reach FastAPI`</strong>`{=html}
```{=html}
</summary>
```
Confirm the backend is running on port `8001`, then open
http://localhost:8001/api/health and http://localhost:8001/docs. Inspect
the browser console and backend terminal for the error.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Answers do not show relevant
citations`</strong>`{=html}
```{=html}
</summary>
```
Confirm upload succeeded, check `GET /api/knowledge/sources`, and ask a
question directly answerable from the uploaded text. Synthetic demo
fixtures do not prove grounding in genuine Lenny material.
```{=html}
</details>
```
🔐 Security and data handling
Keep `.env`, credentials, local databases, private source files, and
model data out of Git.
Never expose secrets through frontend variables.
Upload only content you have permission to use.
Treat generated HTML as untrusted and keep it isolated in the
Artifact Viewer.
Back up both databases before any migration.
For production, use managed secrets, reviewed security settings, and
versioned database migrations.
🗃️ Optional SQLite history migration
This script is for recovering historical local SQLite data into
PostgreSQL; it is optional for the main demo. Back up both databases
first and verify `SQLITE_SOURCE_URL` and `POSTGRES_DATABASE_URL` in
`.env`.
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\backend"
& .\.venv\Scripts\python.exe .\scripts\migrate_sqlite_to_postgres.py
```
Review the script and output before running against important data.
Startup currently uses SQLAlchemy `create_all` plus additive
compatibility repairs, not a versioned Alembic migration system.
🎬 Submission checklist
[ ] App starts using documented instructions.
[ ] Ollama is running and the selected model responds.
[ ] Chat and independent sessions work.
[ ] Source-grounded answers show real source details.
[ ] Unsupported questions are not falsely attributed to transcripts.
[ ] Ship 30 essay generates and opens in the Artifact Viewer.
[ ] Markdown/HTML artifact preview works.
[ ] Backend tests, frontend build, and lint have been run and
results recorded.
[ ] README, PRD, `design.md`, `architecture.md`, tests, and agent
transcripts/logs are present.
[ ] `.env`, secrets, private transcripts, local databases, and model
data are excluded from Git.
[ ] A 2--3 minute YouTube demo with your camera enabled is
ready.
[ ] Public GitHub URL and demo video URL are ready.
[ ] Submission form confirms success.
Suggested demo flow (2--3 minutes)
Problem and product (15--20 sec): who it helps and what it does.
Local model (15--20 sec): show Ollama/provider selection.
Chat and sessions (20--30 sec): ask a question and show a
follow-up or new session.
Grounding (20--30 sec): ask about an authorized uploaded source
and show its citation.
Artifact Viewer (20--30 sec): create and preview a Markdown or
HTML artifact.
Ship 30 (20--30 sec): generate an essay and show the result.
Trade-off (15--20 sec): discuss local-model latency versus cloud
capability.
Keep your camera visible throughout. Do not show `.env`, credentials, or
private source text.
Publish to GitHub safely
From the project root:
``` powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"
git status
git check-ignore .env
```
If this is already a Git repository, inspect its current branch and
remote before pushing. If it is not, create a public repository on
GitHub, then:
``` powershell
git init
git add .
git status --short
git commit -m "Submit Lenny Growth Assistant"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```
Replace the example URL with your real repository. Before committing or
pushing, inspect the staged file list. Never push `.env`, secrets,
private transcripts, databases, or model data, and do not replace an
existing remote without checking it first.
Submit
Open the official Lenny Growth Assistant submission
form
Submit the public GitHub repository URL and YouTube demo link. Confirm
the form reports successful submission.
📌 Known limitations --- disclose honestly
Genuine Lenny transcripts are not bundled; included knowledge
examples are synthetic.
A live cloud-provider request has not been verified with real
credentials.
The backend uses an in-house service/router rather than the
assignment's named external agent SDK options.
Verify PostgreSQL integration in the target environment.
Local-model latency and output quality vary by machine and selected
model.
Database setup uses `create_all` and compatibility repairs rather
than versioned Alembic migrations.
---
::: {align="center"}
Built for practical product and growth research.
Verify the setup. Test the workflows. Protect your secrets. Document
the trade-offs.
:::
