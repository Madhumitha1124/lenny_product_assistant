# Lenny Growth Assistant

A full-stack research and writing assistant with React/Vite, FastAPI, PostgreSQL, ChromaDB, and Ollama. It provides isolated chat sessions, source-grounded answers, optional cloud LLMs, Markdown/HTML artifacts, and a Ship 30 for 30 essay workflow.

## Requirements

- Windows 10/11
- Python 3.11
- Node.js 20+ and npm
- PostgreSQL 16 (native Windows installation; Docker is optional)
- Ollama and the `llama3.2:3b` model for local inference

The backend uses its own `ConversationService` and `ModelRouter` rather than a third-party agent framework. These coordinate retrieval, prompt construction, provider selection, citations, and persistence. The project does not currently include LangChain, PydanticAI, or another external agent framework.

## Windows setup (no Docker required)

### 1. Install and prepare PostgreSQL

Install PostgreSQL 16 for Windows using the official PostgreSQL installer. Keep the PostgreSQL Windows service running. During installation, remember the password for the built-in `postgres` administrator.

Open PowerShell and connect to the local server:

```powershell
psql -U postgres -h 127.0.0.1 -p 5432 -d postgres
```

If `psql` is not on PATH, open **SQL Shell (psql)** from the Start menu and connect to host `127.0.0.1`, port `5432`, database `postgres`, user `postgres`. At the `postgres=#` prompt, create the local application role and database:

```sql
CREATE ROLE lenny WITH LOGIN PASSWORD 'change-me-local-only';
CREATE DATABASE lenny_assistant OWNER lenny;
\q
```

These are development-only sample credentials. You can change the password, but update `DATABASE_URL` and `POSTGRES_DATABASE_URL` in `.env` to match. If the role already exists, change its password with `ALTER ROLE lenny WITH PASSWORD 'your-local-password';` rather than creating it again.

### 2. Configure the app

From PowerShell, go to the project root and copy the template. `.env.example` is documentation/template input only; the backend reads `.env`, not `.env.example`.

```powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
$securePassword = Read-Host "Enter the password you set for PostgreSQL role lenny" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $encodedPassword = [Uri]::EscapeDataString($password)
    $envPath = Join-Path (Get-Location) ".env"
    $envLines = [System.Collections.Generic.List[string]]::new()
    $envLines.AddRange([string[]][System.IO.File]::ReadAllLines($envPath))
    for ($i = 0; $i -lt $envLines.Count; $i++) {
        if ($envLines[$i].StartsWith("DATABASE_URL=")) {
            $envLines[$i] = "DATABASE_URL=postgresql+asyncpg://lenny:$encodedPassword@127.0.0.1:5432/lenny_assistant"
        } elseif ($envLines[$i].StartsWith("POSTGRES_DATABASE_URL=")) {
            $envLines[$i] = "POSTGRES_DATABASE_URL=postgresql+asyncpg://lenny:$encodedPassword@127.0.0.1:5432/lenny_assistant"
        }
    }
    [System.IO.File]::WriteAllLines($envPath, $envLines, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "PostgreSQL connection URLs saved to .env. The password was not displayed."
} finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    $password = $null
    $encodedPassword = $null
    $securePassword.Dispose()
}
```

The example file targets native PostgreSQL at `127.0.0.1:5432`. Enter the same password you set with `\password lenny` when prompted; it stays hidden and is written only to the ignored local `.env` file. Keep real cloud keys only in `.env`; never use `VITE_` prefixes for secrets.

### 3. Install and start Ollama

Install Ollama for Windows, open it so its local service is running, and pull the demo model:

```powershell
ollama pull llama3.2:3b
ollama list
```

If Ollama is not already running as a Windows service/application, start it in a separate terminal with `ollama serve`. Do not start a second Ollama server if one is already listening on port 11434.

### 4. Start the backend

Open a new PowerShell terminal:

```powershell
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

On first startup, Python may download the Sentence Transformers embedding model. The API initializes tables in PostgreSQL and ChromaDB. If PostgreSQL is unavailable or its login is wrong, the backend reports a startup connection error; check the Windows PostgreSQL service and `.env` values.

### 5. Start the frontend

Open another PowerShell terminal:

```powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\frontend"
npm ci
npm run dev
```

Open the frontend at http://localhost:5173/. API health is at http://localhost:8001/api/health and interactive API docs at http://localhost:8001/docs. Keep the backend, frontend, PostgreSQL, and Ollama running while using the app.

## Optional Docker Compose startup

Docker is not required for local development. If Docker Desktop is installed, Compose can run PostgreSQL, the backend, and frontend while Ollama remains on the Windows host. The Compose backend uses the database service hostname and maps PostgreSQL to host port `5433`.

```powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```

Stop with `Ctrl+C` or `docker compose stop`. `docker compose down` preserves named data volumes. Do not run `docker compose down -v` unless you intend to delete the Compose database and vector index.

## Features and source data

- **Chat and sessions:** each chat has its own persisted session and message history.
- **RAG:** TXT/Markdown sources are chunked and embedded locally; ChromaDB stores vectors and PostgreSQL stores source metadata/content.
- **Citations:** responses include traceable source IDs, titles, and excerpts. The source panel also shows an available URL.
- **Unsupported topics:** when no relevant indexed source is retrieved, the assistant labels the answer as general perspective rather than attributing it to Lenny.
- **Providers:** Ollama is the default. Anthropic and OpenAI are optional backend-configured providers. If a cloud call fails, the app tries Ollama only if its model is available and labels the actual provider. If fallback cannot complete, the response reports the error.
- **Artifacts:** Markdown and HTML/CSS output can be previewed, inspected, copied, and downloaded. HTML preview is sanitized and isolated in a sandboxed iframe.
- **Ship 30:** the action generates an approximately 1,250-word essay, saves it as an artifact, and opens it in the Artifact Viewer.

The repository does **not** include genuine Lenny's Podcast or Newsletter transcripts. Its bundled examples are synthetic demo fixtures and are marked as such. To test real source grounding, upload only transcript/newsletter content you are authorized to store using `POST /api/ingest/upload`. Supply an accurate title and the original source URL when available; do not label synthetic or unrelated content as a Lenny source.

Beginner-friendly upload steps:

1. Start the backend and open http://localhost:8001/docs in your browser.
2. Expand **POST `/api/ingest/upload`**, select **Try it out**, then choose your authorized `.txt` or `.md` file.
3. Enter its actual title and, if known, author and original URL. Leave `is_demo` set to `false` only for genuine, authorized source material. Do not invent a URL.
4. Select **Execute**. A successful response includes the source ID and indexed chunk count.
5. Confirm the source appears under **GET `/api/knowledge/sources`**. Ask a question that can be answered from the uploaded text and check the response's source title, ID, excerpt, and original URL.

Uploads must be UTF-8 text and at most 10 MB. Re-uploading identical content reuses its source ID instead of creating a duplicate.

## Provider configuration

- Default local provider: `ollama` / `llama3.2:3b`
- `llama3.2:1b` is also installed locally and can be selected after **Refresh models**, but its live Ship 30 request timed out too. A cloud provider or faster hardware/model may be needed for the long essay; verify the actual word count instead of assuming it meets the target.
- Optional Anthropic: set `ANTHROPIC_API_KEY` in `.env`
- Optional OpenAI: set `OPENAI_API_KEY` in `.env`

Long local generations can take several minutes on a small machine; the default `OLLAMA_TIMEOUT` is 600 seconds. Restart the backend after changing `.env`. Keys are read by the backend only and are not sent to the browser. Offline tests mock cloud calls; a real cloud request requires a valid key and has not been verified here.

## Tests and checks

```powershell
# Backend tests
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\backend"
& .\.venv\Scripts\python.exe -m pytest -q

# Frontend type-check, production bundle, and lint
Set-Location ..\frontend
npm run build
npm run lint
```

To run the optional PostgreSQL integration test, first create a dedicated disposable database (do not point this test at your only copy of important data). In the PostgreSQL SQL Shell, run `CREATE DATABASE lenny_assistant_test OWNER lenny;`. Then in PowerShell:

```powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\backend"
$env:TEST_POSTGRES_URL = "postgresql+asyncpg://lenny:change-me-local-only@127.0.0.1:5432/lenny_assistant_test"
& .\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TEST_POSTGRES_URL
```

Replace the sample password if you changed it in `.env`. The integration test inserts a uniquely identified session/message and deletes only those rows.

For hands-on steps, see [docs/manual-test-plan.md](./docs/manual-test-plan.md). The requirements checklist is in [docs/final-requirements-audit.md](./docs/final-requirements-audit.md); audit outcomes and corrections are in [docs/implementation-log.md](./docs/implementation-log.md).

## Migrate existing SQLite data

The preserved local SQLite database currently contains 6 sessions and 14 messages (plus 3 knowledge-source rows and no artifacts). Migration is optional historical-data recovery; the existing PostgreSQL application database remains the active database. The script is repeatable: it inserts missing IDs, leaves existing PostgreSQL rows untouched, reports rows already present, and validates per-table row counts. Back up the SQLite file and PostgreSQL database before running it. Set `SQLITE_SOURCE_URL` and `POSTGRES_DATABASE_URL` in `.env`, then:

```powershell
Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant\backend"
& .\.venv\Scripts\python.exe .\scripts\migrate_sqlite_to_postgres.py
```

Startup uses SQLAlchemy `create_all` plus additive compatibility repairs; this is not a versioned Alembic migration system. For deployments, use versioned migrations and managed secrets.

## Demo video, GitHub, and submission

1. Record a 2–3 minute walkthrough with a screen recorder such as OBS or the Windows camera/recording tools. Turn on your webcam and keep your camera visible in a corner for the entire recording.
2. Show the app starting, Ollama/model selection, a new independent chat, a source-backed question (after uploading authorized material), an unsupported question, one Markdown or HTML artifact, and Ship 30. Do not display `.env`, API keys, database passwords, or private transcript text.
3. Review the recording before sharing it. The project does not create or claim a demo video for you.
4. To publish, open PowerShell in the project root and check whether this folder is already a Git repository before initializing one:

   ```powershell
   Set-Location "C:\Users\Madhumitha S\Desktop\Lenny's podcast ai\lenny-growth-assistant"
   git status
   git check-ignore .env
   ```

   If `git status` says this is not a repository, create a new public repository on GitHub's website, then initialize and push this project (replace the example account/repository):

   ```powershell
   git init
   git add .
   git status --short
   git commit -m "Submit Lenny Growth Assistant"
   git branch -M main
   git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
   git push -u origin main
   ```

   Before `git add .` and before pushing, inspect staged file names and confirm `.env`, secrets, private transcripts, local databases, and generated model data are not included. `.env` is listed in `.gitignore`. If this is already a repository, do not run `git init` or replace its remote; review its existing branch/remote and follow your usual push flow. Inspect the public repository for secrets before sharing its URL. Do not publish transcripts unless you have permission.
5. Submit the public repository URL and demo-video link using the exact form linked from your assignment/course page. That form URL was not included in the project requirements supplied here, so no submission link is guessed or fabricated. Confirm the form reports a successful submission.
#   l e n n y _ p r o d u c t _ a s s i s t a n t  
 #   l e n n y _ p r o d u c t _ a s s i s t a n t  
 #   l e n n y _ p r o d u c t _ a s s i s t a n t  
 "# lenny_product_assistant" 
