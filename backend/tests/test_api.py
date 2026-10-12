"""Backend tests — uses in-memory SQLite, mocked LLM providers."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

# ── App bootstrap with test DB ─────────────────────────────────────────────────
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DEFAULT_LLM_PROVIDER"] = "ollama"
os.environ["CHROMA_PERSIST_DIR"] = ":memory:"  # Use ephemeral chroma

from app.main import app
from app.database.session import init_db, engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Fresh in-memory DB for every test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Health ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "database" in data
    assert "ollama" in data
    assert "version" in data


# ── Sessions ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/sessions", json={"title": "Test Session"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Session"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_sessions_empty(client):
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_and_list_sessions(client):
    await client.post("/api/sessions", json={"title": "Session A"})
    await client.post("/api/sessions", json={"title": "Session B"})
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_delete_session(client):
    create_resp = await client.post("/api/sessions", json={"title": "To Delete"})
    session_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/sessions/{session_id}")
    assert del_resp.status_code == 204
    # Session gone
    resp = await client.get("/api/sessions")
    assert all(s["id"] != session_id for s in resp.json())


@pytest.mark.asyncio
async def test_delete_nonexistent_session(client):
    resp = await client.delete("/api/sessions/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_messages_nonexistent_session(client):
    resp = await client.get("/api/sessions/bad-id/messages")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_rejects_unknown_session_without_creating_replacement(client):
    response = await client.post("/api/chat", json={
        "session_id": "missing-session",
        "message": "This must not become a different chat",
        "provider": "ollama",
        "model": "llama3.2:3b",
    })

    assert response.status_code == 422
    assert "Session missing-session not found" in response.json()["detail"]
    assert (await client.get("/api/sessions")).json() == []


@pytest.mark.asyncio
async def test_session_isolation(client):
    """Two sessions have independent message histories and provider context."""
    s1 = (await client.post("/api/sessions", json={"title": "S1"})).json()
    s2 = (await client.post("/api/sessions", json={"title": "S2"})).json()

    mock_resp = MagicMock()
    mock_resp.content = "Test answer"
    mock_resp.error = None
    mock_resp.provider = "ollama"
    mock_resp.model = "llama3.2:3b"
    mock_resp.fallback_from = None

    from app.services.conversation_service import conversation_service
    completion = AsyncMock(side_effect=[mock_resp, mock_resp])
    with patch.object(
        conversation_service._router,
        "complete_with_fallback",
        side_effect=completion,
    ):
        with patch("app.retrieval.retrieval_service.retrieval_service.retrieve", return_value=[]):
            await client.post("/api/chat", json={
                "session_id": s1["id"], "message": "Hello from S1",
                "provider": "ollama", "model": "llama3.2:3b"
            })
            await client.post("/api/chat", json={
                "session_id": s2["id"], "message": "Hello from S2",
                "provider": "ollama", "model": "llama3.2:3b"
            })

    msgs_s1 = (await client.get(f"/api/sessions/{s1['id']}/messages")).json()
    msgs_s2 = (await client.get(f"/api/sessions/{s2['id']}/messages")).json()
    assert [m["content"] for m in msgs_s1 if m["role"] == "user"] == ["Hello from S1"]
    assert [m["content"] for m in msgs_s2 if m["role"] == "user"] == ["Hello from S2"]
    second_call_messages = completion.await_args_list[1].args[2]
    assert all("Hello from S1" not in item["content"] for item in second_call_messages)


@pytest.mark.asyncio
async def test_chat_includes_verifiable_source_reference(client):
    from app.schemas.schemas import SourceCitation

    mock_resp = MagicMock(
        content="Retention is a useful signal.",
        error=None,
        provider="ollama",
        model="llama3.2:3b",
        fallback_from=None,
    )
    citation = SourceCitation(
        source_id="source-123",
        title="[DEMO] Retention Signals",
        excerpt="Users returning without prompting can indicate value.",
        is_demo=True,
    )

    from app.services.conversation_service import conversation_service
    with patch.object(
        conversation_service._router,
        "complete_with_fallback",
        AsyncMock(return_value=mock_resp),
    ):
        with patch(
            "app.retrieval.retrieval_service.retrieval_service.retrieve",
            return_value=[citation],
        ):
            response = await client.post("/api/chat", json={
                "message": "What does retention tell us?",
                "provider": "ollama",
                "model": "llama3.2:3b",
            })

    assert response.status_code == 200
    data = response.json()
    assert data["sources"][0]["source_id"] == "source-123"
    assert "### Sources" in data["content"]
    assert r"\[DEMO\] Retention Signals" in data["content"]
    assert "synthetic demo content, not a Lenny source" in data["content"]
    assert "synthetic demo content, not a Lenny source" in data["content"]


@pytest.mark.asyncio
async def test_chat_labels_answers_without_retrieved_evidence(client):
    mock_resp = MagicMock(
        content="A general product-management response.",
        error=None,
        provider="ollama",
        model="llama3.2:3b",
        fallback_from=None,
    )

    from app.services.conversation_service import conversation_service
    with patch.object(
        conversation_service._router,
        "complete_with_fallback",
        AsyncMock(return_value=mock_resp),
    ):
        with patch(
            "app.retrieval.retrieval_service.retrieval_service.retrieve",
            return_value=[],
        ):
            response = await client.post("/api/chat", json={
                "message": "A topic absent from the knowledge base",
                "provider": "ollama",
                "model": "llama3.2:3b",
            })

    assert response.status_code == 200
    assert "No relevant indexed source was found" in response.json()["content"]
    assert "not attributed to Lenny's material" in response.json()["content"]
    assert response.json()["sources"] == []


# ── Chat Validation ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_empty_message_rejected(client):
    resp = await client.post("/api/chat", json={
        "message": "   ", "provider": "ollama", "model": "llama3.2:3b"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_message_rejected(client):
    resp = await client.post("/api/chat", json={"provider": "ollama"})
    assert resp.status_code == 422


# ── Model Router ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_model_router_ollama():
    from app.services.model_router import ModelRouter, OllamaProvider
    router = ModelRouter()
    provider = router.get_provider("ollama", "llama3.2:3b")
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_name == "ollama"
    assert provider.model_name == "llama3.2:3b"


@pytest.mark.asyncio
async def test_ollama_timeout_suggests_long_generation_options():
    import httpx
    from app.services.model_router import OllamaProvider

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with patch("app.services.model_router.httpx.AsyncClient", return_value=mock_client):
        response = await OllamaProvider("llama3.2:3b").complete(
            [{"role": "user", "content": "Write a long essay"}]
        )

    assert response.error is not None
    assert "faster local model" in response.error
    assert "OLLAMA_TIMEOUT" in response.error


@pytest.mark.asyncio
async def test_model_router_anthropic_no_key():
    from app.services.model_router import ModelRouter, AnthropicProvider
    router = ModelRouter()
    provider = router.get_provider("anthropic", "claude-3-haiku-20240307")
    assert isinstance(provider, AnthropicProvider)
    available = await provider.is_available()
    assert available is False  # No key set in test env


@pytest.mark.asyncio
async def test_cloud_provider_falls_back_to_ollama_with_explicit_provider_metadata():
    from app.services.model_router import LLMResponse, ModelRouter

    cloud = MagicMock()
    cloud.provider_name = "anthropic"
    cloud.model_name = "claude-test"
    cloud.complete = AsyncMock(return_value=LLMResponse(
        "", "anthropic", "claude-test", error="API key not configured"
    ))
    local = MagicMock()
    local.provider_name = "ollama"
    local.model_name = "llama3.2:3b"
    local.is_available = AsyncMock(return_value=True)
    local.complete = AsyncMock(return_value=LLMResponse(
        "Local answer", "ollama", "llama3.2:3b"
    ))

    router = ModelRouter()
    with patch.object(router, "get_provider", return_value=cloud), patch(
        "app.services.model_router.OllamaProvider", return_value=local
    ):
        response = await router.complete_with_fallback(
            "anthropic", "claude-test", [{"role": "user", "content": "hello"}]
        )

    assert response.content == "Local answer"
    assert response.provider == "ollama"
    assert response.model == "llama3.2:3b"
    assert response.fallback_from == "anthropic/claude-test"


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected_instead_of_silently_using_ollama():
    from app.services.model_router import ModelRouter

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        ModelRouter().get_provider("unknown", "model")


def test_html_source_references_escape_untrusted_source_metadata():
    from app.retrieval.source_references import append_source_references
    from app.schemas.schemas import SourceCitation

    citation = SourceCitation(
        source_id="source-1",
        title='<script>alert("title")</script>',
        excerpt='<img src=x onerror="alert(1)">',
    )

    output = append_source_references(
        "<html><body><h1>Generated page</h1></body></html>",
        [citation],
        html_output=True,
    )

    assert "<script>" not in output
    assert "<img" not in output
    assert "&lt;script&gt;" in output
    assert "&lt;img" in output
    assert output.index("<section>") < output.index("</body>")


@pytest.mark.asyncio
async def test_ollama_unavailable_returns_error():
    from app.services.model_router import OllamaProvider
    provider = OllamaProvider(model="llama3.2:3b")
    import httpx
    with patch(
        "app.services.model_router.httpx.AsyncClient",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        response = await provider.complete([{"role": "user", "content": "hi"}])
    assert response.error is not None
    assert response.content == ""


# ── Retrieval with no sources ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retrieval_empty_collection():
    """Retrieval on empty collection returns empty list without crashing."""
    from app.retrieval.retrieval_service import RetrievalService
    svc = RetrievalService()
    # Fresh in-memory client avoids holding Windows file handles after the test.
    import chromadb
    from chromadb.config import Settings as CS
    import app.retrieval.retrieval_service as rs
    orig_client = rs._chroma_client
    orig_collection = rs._collection
    rs._chroma_client = chromadb.EphemeralClient(settings=CS(anonymized_telemetry=False))
    rs._collection = None
    try:
        results = svc.retrieve("product market fit", top_k=3)
        assert results == []
    finally:
        rs._chroma_client = orig_client
        rs._collection = orig_collection


def test_retrieval_skips_irrelevant_chunks_before_source_deduplication():
    from app.retrieval.retrieval_service import RetrievalService
    import app.retrieval.retrieval_service as rs

    class FakeModel:
        def encode(self, texts, show_progress_bar=False):
            return FakeEmbeddings()

    class FakeEmbeddings(list):
        def tolist(self):
            return list(self)

    class FakeCollection:
        def count(self):
            return 3

        def query(self, **kwargs):
            return {
                "documents": [["weak duplicate", "relevant chunk", "unrelated"]],
                "metadatas": [
                    [
                        {"source_id": "source-1", "title": "Transcript"},
                        {"source_id": "source-1", "title": "Transcript"},
                        {"source_id": "source-2", "title": "Other"},
                    ]
                ],
                "distances": [[0.8, 0.4, 0.9]],
            }

    with patch.object(rs, "_get_embedding_model", return_value=FakeModel()), patch.object(
        rs, "_get_collection", return_value=FakeCollection()
    ):
        results = RetrievalService().retrieve("a relevant query")

    assert len(results) == 1
    assert results[0].source_id == "source-1"
    assert results[0].excerpt == "relevant chunk"


# ── Artifact validation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_artifact_invalid_type(client):
    resp = await client.post("/api/artifacts", json={
        "prompt": "Generate something",
        "artifact_type": "invalid_type",
        "title": "Test"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_artifact_generation_uses_selected_provider_and_appends_sources(client):
    from app.artifacts.artifact_service import artifact_service
    from app.schemas.schemas import SourceCitation

    mock_resp = MagicMock(
        content="# Growth plan\n\nPrioritize retention.",
        error=None,
        provider="openai",
        model="gpt-4o-mini",
        fallback_from=None,
    )
    citation = SourceCitation(
        source_id="source-growth",
        title="Growth interview notes",
        excerpt="The team prioritized retention before paid acquisition.",
    )

    with patch.object(
        artifact_service._router,
        "complete_with_fallback",
        AsyncMock(return_value=mock_resp),
    ) as complete, patch(
        "app.retrieval.retrieval_service.retrieval_service.retrieve",
        return_value=[citation],
    ):
        response = await client.post("/api/artifacts", json={
            "prompt": "Create a growth plan",
            "artifact_type": "markdown",
            "title": "Growth plan",
            "provider": "openai",
            "model": "gpt-4o-mini",
        })

    assert response.status_code == 200
    assert complete.await_args.args[:2] == (
        "openai",
        "gpt-4o-mini",
    )
    assert "Growth interview notes" in response.json()["content"]
    assert "source-growth" in response.json()["content"]


@pytest.mark.asyncio
async def test_html_artifact_removes_model_code_fences_and_discloses_missing_evidence(client):
    from app.artifacts.artifact_service import artifact_service

    mock_resp = MagicMock(
        content="```html\n<!doctype html><html><body><h1>Welcome</h1></body></html>\n```",
        error=None,
        provider="ollama",
        model="llama3.2:3b",
        fallback_from=None,
    )
    with patch.object(
        artifact_service._router,
        "complete_with_fallback",
        AsyncMock(return_value=mock_resp),
    ), patch(
        "app.retrieval.retrieval_service.retrieval_service.retrieve",
        return_value=[],
    ):
        response = await client.post("/api/artifacts", json={
            "prompt": "Create a welcome page",
            "artifact_type": "html",
            "title": "Welcome",
            "provider": "ollama",
            "model": "llama3.2:3b",
        })

    assert response.status_code == 200
    content = response.json()["content"]
    assert "```" not in content
    assert "<h1>Welcome</h1>" in content
    assert "No relevant indexed source was found" in content


# ── Ship30 routing ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ship30_creates_artifact(client):
    from app.schemas.schemas import SourceCitation

    mock_resp = MagicMock()
    mock_resp.content = (
        "# Test Essay\n\nThis is a test essay about product growth.\n"
        * 110
    )
    mock_resp.error = None
    mock_resp.provider = "ollama"
    mock_resp.model = "llama3.2:3b"
    mock_resp.fallback_from = None
    citation = SourceCitation(
        source_id="ship30-source",
        title="Verified source",
        excerpt="Evidence used by the essay.",
    )

    from app.skills.ship30_skill import ship30_skill
    with patch.object(
        ship30_skill._router,
        "complete_with_fallback",
        AsyncMock(return_value=mock_resp),
    ):
        with patch(
            "app.retrieval.retrieval_service.retrieval_service.retrieve",
            return_value=[citation],
        ):
            resp = await client.post("/api/skills/ship30", json={
                "topic": "How to achieve product-market fit",
                "provider": "ollama",
                "model": "llama3.2:3b",
            })
    assert resp.status_code == 200
    data = resp.json()
    assert "artifact_id" in data
    assert "content" in data
    assert 1_000 <= data["word_count"] <= 1_600
    assert "Verified source" in data["content"]
    assert data["sources"][0]["source_id"] == "ship30-source"

    artifact = await client.get(f"/api/artifacts/{data['artifact_id']}")
    assert artifact.status_code == 200
    assert "ship30-source" in artifact.json()["content"]


# ── Source citation metadata ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_uploaded_markdown_is_indexed_deduplicated_and_retrievable(client):
    from app.retrieval import retrieval_service as retrieval_module
    from app.retrieval.retrieval_service import retrieval_service

    text = (
        "TEST-ONLY SOURCE — this is original fixture text, not Lenny material. "
        "The sample onboarding team asks new users to complete one meaningful "
        "setup action before exploring optional settings."
    )

    class FakeEmbeddings(list):
        def tolist(self):
            return list(self)

    class FakeEmbeddingModel:
        def encode(self, texts, show_progress_bar=False):
            return FakeEmbeddings([[1.0, 0.0] for _ in texts])

    class FakeCollection:
        def __init__(self):
            self.documents = {}
            self.metadatas = {}

        def upsert(self, ids, documents, metadatas, embeddings):
            for chunk_id, document, metadata in zip(ids, documents, metadatas):
                self.documents[chunk_id] = document
                self.metadatas[chunk_id] = metadata

        def count(self):
            return len(self.documents)

        def query(self, query_embeddings, n_results, include):
            chunk_ids = list(self.documents)[:n_results]
            return {
                "documents": [[self.documents[key] for key in chunk_ids]],
                "metadatas": [[self.metadatas[key] for key in chunk_ids]],
                "distances": [[0.1 for _ in chunk_ids]],
            }

    collection = FakeCollection()
    with patch.object(
        retrieval_module, "_get_embedding_model", return_value=FakeEmbeddingModel()
    ), patch.object(retrieval_module, "_get_collection", return_value=collection):
        response = await client.post(
            "/api/ingest/upload",
            files={"file": ("authorized-notes.MD", text.encode(), "text/markdown")},
            data={
                "title": "User-provided test notes",
                "author": "Test author",
                "source_type": "transcript",
                "is_demo": "true",
            },
        )

        assert response.status_code == 200
        first = response.json()
        assert first["chunks_indexed"] == 1

        repeated_response = await client.post(
            "/api/ingest/upload",
            files={"file": ("authorized-notes.MD", text.encode(), "text/markdown")},
            data={
                "title": "Duplicate title must not create another source",
                "source_type": "transcript",
                "is_demo": "true",
            },
        )
        assert repeated_response.status_code == 200
        assert repeated_response.json()["source_id"] == first["source_id"]
        assert len(collection.documents) == 1

        citations = retrieval_service.retrieve("new users setup action")
        assert len(citations) == 1
        assert citations[0].source_id == first["source_id"]
        assert citations[0].title == "User-provided test notes"
        assert citations[0].is_demo is True
        assert "meaningful setup action" in citations[0].excerpt

    sources = (await client.get("/api/knowledge/sources")).json()
    assert len(sources) == 1
    assert sources[0]["id"] == first["source_id"]


@pytest.mark.asyncio
async def test_upload_rejects_empty_and_oversized_text(client):
    empty = await client.post(
        "/api/ingest/upload",
        files={"file": ("empty.txt", b" \n\t", "text/plain")},
    )
    assert empty.status_code == 422
    assert empty.json()["detail"] == "Uploaded file is empty"

    oversized = await client.post(
        "/api/ingest/upload",
        files={
            "file": (
                "too-large.txt",
                b"a" * (10 * 1024 * 1024 + 1),
                "text/plain",
            )
        },
    )
    assert oversized.status_code == 413


@pytest.mark.asyncio
async def test_knowledge_sources_empty(client):
    resp = await client.get("/api/knowledge/sources")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_models_endpoint(client):
    resp = await client.get("/api/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert "default_provider" in data
