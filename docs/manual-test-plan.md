# Manual Test Plan

## Frontend checks

- Open the app and confirm the welcome screen loads.
- Click **New Chat** and verify a new session ID appears in the sidebar before sending a message.
- Ask a prompt from the suggestion list and confirm the response renders in markdown.
- Create two sessions, send different messages, switch between them, and verify their messages/context never cross.
- Refresh the browser and open each conversation to verify its persisted history loads.
- Select a configured cloud model and verify the selected provider/model is visible in the header.
- Generate a Markdown artifact and an HTML artifact; verify preview, source, copy, and download actions.
- Resize below 900px and verify the artifact viewer opens as a dismissible overlay.
- Generate an HTML artifact containing a script tag and an external resource; confirm the preview does not execute the script or load external content.
- Generate a Ship 30 essay and verify it opens in the artifact viewer with source references when matching evidence exists.
- Check the returned word count; the requested target is approximately 1,250 words. Small CPU-only local models can time out or return much shorter content, so record the actual result rather than assuming the target was met.

## Local model demo checks

- Start Ollama locally.
- Run `ollama pull llama3.2:3b`.
- Confirm `/api/models` reports the local model as available.
- Upload an authorized `.txt` or `.md` transcript through `/docs` (`POST /api/ingest/upload`).
- Confirm an uppercase `.MD` extension works, while empty, non-UTF-8, unsupported, and over-10-MB files are rejected with a clear status/error.
- Upload identical text twice and verify the second response returns the original source ID instead of creating another source.
- Confirm `/api/knowledge/sources` reports the document and a nonzero chunk count.
- Ask a question supported by the uploaded content; verify the answer and source panel include the correct source title, ID, and excerpt.
- Ask about a topic absent from the content; verify the response labels itself as general guidance and includes no source citations.
- Stop Ollama and verify the API reports the unavailable service; restart it before further local-model testing.

## Regression checks

- Empty messages are blocked.
- Unsupported provider names are rejected instead of silently switching models.
- A cloud provider error falls back only to an available Ollama model and clearly states which model generated the response.
- PostgreSQL-backed sessions, messages, timestamps, and artifacts remain after restarting the backend or Compose stack.
- Submit a chat request with a nonexistent `session_id`; verify it returns an explicit validation error and does not silently create another session.
- Run backend tests with `Set-Location .\backend; & .\.venv\Scripts\python.exe -m pytest -q`.
- To run the PostgreSQL integration test, set `$env:TEST_POSTGRES_URL` to an isolated test database before running pytest.
- Run frontend checks with `Set-Location .\frontend; npm run build; npm run lint`.

## Recording and submission

- Record a 2–3 minute app walkthrough with the webcam visible throughout. Show provider selection, a new session, a grounded answer from authorized uploaded material, an unsupported question, an artifact, and Ship 30. Do not expose credentials or private source content.
- Publish the repository as public only after confirming `.env` is ignored and no secrets or unauthorized transcripts are tracked.
- Submit the repository and video links through the exact assignment form provided by the course. Use the assignment portal URL; it is not supplied in this repository.
