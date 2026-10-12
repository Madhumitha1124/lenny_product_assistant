"""Retrieval service using ChromaDB for vector similarity search."""
from __future__ import annotations
import logging
import re
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.schemas.schemas import SourceCitation

logger = logging.getLogger(__name__)
settings = get_settings()

_chroma_client: chromadb.ClientAPI | None = None
_embedding_model: SentenceTransformer | None = None
_collection: chromadb.Collection | None = None


def _get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_chroma_client()
        _collection = client.get_or_create_collection(
            name="lenny_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


class RetrievalService:
    def ingest_text(
        self,
        text: str,
        source_id: str,
        metadata: dict[str, Any],
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> int:
        """Chunk and embed text, store in ChromaDB. Returns number of chunks added."""
        chunk_size = chunk_size or settings.chunk_size
        overlap = overlap or settings.chunk_overlap
        chunks = _chunk_text(text, chunk_size, overlap)
        if not chunks:
            return 0

        model = _get_embedding_model()
        collection = _get_collection()

        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        ids, docs, metas, embeds = [], [], [], []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{source_id}__chunk_{idx}"
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append({**metadata, "chunk_index": idx, "source_id": source_id})
            embeds.append(embedding)

        # Upsert to handle refreshes
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
        logger.info(f"Ingested {len(chunks)} chunks for source_id={source_id}")
        return len(chunks)

    def retrieve(self, query: str, top_k: int | None = None) -> list[SourceCitation]:
        """Retrieve top-k relevant chunks for a query."""
        top_k = top_k or settings.retrieval_top_k
        collection = _get_collection()

        count = collection.count()
        if count == 0:
            return []

        model = _get_embedding_model()
        query_embedding = model.encode([query], show_progress_bar=False).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        citations = []
        seen_sources: set[str] = set()
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Ignore weak matches before marking a source seen so a later,
            # better chunk from the same source can still be cited.
            if dist > 0.7:
                continue

            source_id = meta.get("source_id", "unknown")
            # Deduplicate by source for concise citations (keep best chunk)
            if source_id in seen_sources:
                continue
            seen_sources.add(source_id)

            citations.append(
                SourceCitation(
                    source_id=source_id,
                    title=meta.get("title", "Unknown Source"),
                    author=meta.get("author"),
                    source_url=meta.get("source_url"),
                    excerpt=doc[:400] + ("…" if len(doc) > 400 else ""),
                    is_demo=meta.get("is_demo", False),
                )
            )
        return citations

    def delete_source(self, source_id: str) -> int:
        """Remove all chunks for a given source_id from the vector index."""
        collection = _get_collection()
        results = collection.get(where={"source_id": source_id})
        ids_to_delete = results["ids"]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def source_exists(self, content_hash: str) -> bool:
        """Check if a document with this hash was already ingested."""
        collection = _get_collection()
        results = collection.get(where={"content_hash": content_hash}, limit=1)
        return len(results["ids"]) > 0

    def count(self) -> int:
        return _get_collection().count()


retrieval_service = RetrievalService()
