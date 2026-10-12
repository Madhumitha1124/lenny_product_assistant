# Product Requirements Document

## Primary user and problem

The primary user is a PM, founder, or growth operator who needs a grounded way to convert product and growth conversations into clear recommendations, essays, and artifact drafts. The central problem is fragmented knowledge, repetitive research, and a lack of structured writing support rooted in trustworthy evidence.

## User jobs and pain points

- Ask product and growth questions without leaving the product context
- Ground recommendations in transcript evidence instead of vague opinions
- Review source titles, excerpts, and references while distinguishing supported claims from general guidance
- Generate polished essays and artifacts from current discussion context
- Keep independent conversations organized and reusable
- Switch between a local Ollama model and configured cloud providers

## Success metrics

- A user can create a session and send a question in under one minute
- The app retrieves relevant indexed chunks and cites their source IDs and titles when evidence is available
- Unsupported answers clearly disclose that no relevant indexed evidence was found
- A message flow remains isolated by session
- Conversations and artifacts survive backend restarts using PostgreSQL
- A provider fallback, when used, is clearly labeled with the provider that generated the answer

## Assumptions

- PostgreSQL is the required application persistence backend and is installed natively for the primary Windows setup
- Docker Compose remains an optional startup path; Docker Desktop is not required for local development
- SQLite is used by isolated automated tests only, not as the default application database
- Ollama is the default local provider for the MVP
- Users supply only transcript/newsletter material they are authorized to store
- Built-in synthetic demo fixtures are never represented as real Lenny content

## Included and excluded scope

Included:
- session-based chat
- knowledge ingestion and source citation
- local and optional cloud provider selection with explicit local fallback
- Markdown and sandboxed HTML artifact generation and viewing
- Ship 30 generation flow

Excluded:
- heavy multi-agent orchestration
- advanced embedding pipeline optimization
- cloud billing and enterprise auth

## Main user flows

1. Open the app and start a chat session.
2. Ask a product or growth question.
3. Review the generated answer and cited sources.
4. Create or update an artifact.
5. Generate a Ship 30-style essay from the same discussion context.

## Acceptance criteria

- The app has a working home screen and session list.
- Chat API accepts session_id, message, provider, and model.
- Response includes citations and provider metadata.
- Invalid or empty messages are rejected.
- The app reports model availability without crashing when the provider is offline.
- A supplied but unknown session ID fails explicitly instead of silently creating a different conversation.

## Risks and trade-offs

- Limited local model capacity may reduce the fidelity of some long-form output.
- Vector retrieval quality depends on embedding similarity and the quality of user-supplied source material.
- Synthetic demo data is acceptable for UI validation but must never be disguised as real Lenny content.

## Implementation plan

1. Establish backend routes and PostgreSQL persistence.
2. Add session persistence and source ingestion.
3. Add provider routing and health checks.
4. Add frontend chat and session flows.
5. Add the responsive artifact viewer and Ship 30 workflow.
6. Add automated tests, operator documentation, and manual verification.
