"""Artifact generation service."""
from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_router import ModelRouter, with_provider_fallback_notice
from app.retrieval.retrieval_service import retrieval_service
from app.retrieval.source_references import append_source_references
from app.models.artifact import Artifact
from app.schemas.schemas import ArtifactResponse

logger = logging.getLogger(__name__)

ARTIFACT_SYSTEM_PROMPTS = {
    "markdown": "You are a technical writer. Generate well-structured Markdown documents with clear headings, bullet points, and concise prose.",
    "html": "You are a frontend developer. Generate clean, self-contained HTML/CSS. Use inline styles only. No external dependencies. The output will be sandboxed.",
    "prd": "You are a senior product manager. Generate a detailed Product Requirements Document in Markdown with sections: Overview, Problem, Goals, User Stories, Acceptance Criteria, Out of Scope, Timeline.",
    "landing_page": "You are a conversion copywriter and frontend developer. Generate a beautiful, complete HTML landing page with inline CSS. Make it visually impressive with a hero, features, and CTA section.",
    "growth_plan": "You are a growth strategist. Generate a 90-day growth experiment plan in Markdown with hypothesis, metrics, tactics, and expected outcomes.",
    "strategy": "You are a strategy consultant. Generate a structured strategy document in Markdown with situation analysis, options, recommendation, and implementation steps.",
    "essay": "You are an expert essayist. Generate a compelling long-form essay in Markdown.",
}
GROUNDING_INSTRUCTIONS = (
    "Use only the supplied knowledge-base evidence for claims attributed to sources. "
    "If no evidence supports a claim, label it as general perspective and do not attribute "
    "it to Lenny's Podcast or Newsletter. Never invent source titles, quotes, or references."
)


def _strip_html_code_fence(content: str) -> str:
    lines = content.strip().splitlines()
    if (
        len(lines) >= 3
        and lines[0].strip().lower() in {"```", "```html"}
        and lines[-1].strip() == "```"
    ):
        return "\n".join(lines[1:-1]).strip()
    return content


class ArtifactService:
    def __init__(self):
        self._router = ModelRouter()

    async def generate(
        self,
        db: AsyncSession,
        prompt: str,
        artifact_type: str,
        title: str,
        session_id: str | None,
        provider: str = "ollama",
        model: str = "llama3.2:3b",
    ) -> ArtifactResponse:
        # Retrieve relevant context
        citations = retrieval_service.retrieve(prompt, top_k=4)
        evidence = ""
        if citations:
            evidence = "\n\nRelevant knowledge base context:\n" + "\n".join(
                f"- {c.title}: {c.excerpt[:200]}" for c in citations
            )

        system_prompt = (
            f"{ARTIFACT_SYSTEM_PROMPTS.get(artifact_type, ARTIFACT_SYSTEM_PROMPTS['markdown'])}\n\n"
            f"{GROUNDING_INSTRUCTIONS}"
        )
        messages = [{"role": "user", "content": f"{prompt}{evidence}"}]

        response = await self._router.complete_with_fallback(
            provider,
            model,
            messages,
            system_prompt=system_prompt,
        )

        if response.error:
            raise RuntimeError(response.error)
        if artifact_type in {"html", "landing_page"}:
            response.content = _strip_html_code_fence(response.content)
        content = with_provider_fallback_notice(response)
        content = append_source_references(
            content,
            citations,
            html_output=artifact_type in {"html", "landing_page"},
        )

        artifact = Artifact(
            session_id=session_id,
            title=title,
            artifact_type=artifact_type,
            legacy_type=artifact_type,
            content=content,
        )
        db.add(artifact)
        await db.flush()

        return ArtifactResponse.model_validate(artifact)


artifact_service = ArtifactService()
