"""Ship 30 for 30 essay writing skill."""
from __future__ import annotations
import logging
from app.services.model_router import ModelRouter, with_provider_fallback_notice
from app.retrieval.retrieval_service import retrieval_service
from app.retrieval.source_references import append_source_references
from app.schemas.schemas import Ship30Response, SourceCitation
from app.models.artifact import Artifact
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SHIP30_SYSTEM_PROMPT = """You are an expert growth essayist trained in the Ship 30 for 30 writing methodology.
Your essays are direct, punchy, and idea-dense. You follow these writing principles:

STRUCTURE:
1. Start with a strong, specific hook (1-2 sentences) that makes the reader stop scrolling.
2. Promise (what the reader will learn).
3. Body: 3-5 concrete ideas, each with a short heading, 2-3 short paragraphs, and bullet points where useful.
4. Use selective **bold** for key phrases — not overused.
5. Close with a specific, memorable takeaway or call-to-action.

STYLE:
- Write in second person ("you") for immediacy.
- Short paragraphs (1-3 sentences max).
- No fluff, no filler sentences.
- Concrete examples over abstract principles.
- Target ~1,250 words.

GROUNDING:
- Ground factual claims in the provided transcript evidence.
- If evidence is limited, clearly state the limitation rather than fabricating support.
- Do NOT invent quotes or attribute false statements to Lenny Rachitsky or podcast guests.
- Include source references naturally in the text when evidence is cited.

OUTPUT FORMAT: Write the essay in Markdown. Use ## for section headings."""


class Ship30WritingSkill:
    def __init__(self):
        self._router = ModelRouter()

    async def generate_essay(
        self,
        db: AsyncSession,
        topic: str,
        provider: str = "ollama",
        model: str = "llama3.2:3b",
        session_id: str | None = None,
    ) -> Ship30Response:
        # Retrieve relevant knowledge
        citations = retrieval_service.retrieve(topic, top_k=6)

        evidence_block = ""
        if citations:
            evidence_parts = []
            for c in citations:
                demo_note = " [DEMO FIXTURE — not a real podcast source]" if c.is_demo else ""
                evidence_parts.append(
                    f"**Source: {c.title}**{demo_note}\n> {c.excerpt}"
                )
            evidence_block = "\n\n".join(evidence_parts)
        else:
            evidence_block = "No transcript evidence available for this topic."

        messages = [
            {
                "role": "user",
                "content": (
                    f"Write a Ship 30 for 30 essay (~1,250 words) on this topic:\n\n"
                    f"**{topic}**\n\n"
                    f"Use this transcript evidence to ground your claims:\n\n"
                    f"{evidence_block}\n\n"
                    f"If evidence is insufficient for a specific claim, acknowledge it rather than inventing support."
                ),
            }
        ]

        response = await self._router.complete_with_fallback(
            provider,
            model,
            messages,
            system_prompt=SHIP30_SYSTEM_PROMPT,
        )

        if response.error:
            raise RuntimeError(response.error)
        elif citations:
            content = append_source_references(
                with_provider_fallback_notice(response), citations
            )
        else:
            content = append_source_references(
                with_provider_fallback_notice(response), []
            )

        word_count = len(content.split())
        title = f"Ship 30 Essay: {topic[:60]}"

        # Persist as artifact
        artifact = Artifact(
            session_id=session_id,
            title=title,
            artifact_type="essay",
            legacy_type="essay",
            content=content,
        )
        db.add(artifact)
        await db.flush()

        return Ship30Response(
            artifact_id=artifact.id,
            title=title,
            content=content,
            word_count=word_count,
            sources=citations,
        )


ship30_skill = Ship30WritingSkill()
