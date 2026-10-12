"""Format source references that the application can verify independently of model output."""
import html
import re
from app.schemas.schemas import SourceCitation


def append_source_references(
    content: str,
    sources: list[SourceCitation],
    *,
    html_output: bool = False,
) -> str:
    if not sources:
        notice = (
            "**Knowledge base:** No relevant indexed source was found. "
            "The response below is general information, not attributed to Lenny's material."
        )
        if html_output:
            safe_notice = html.escape(notice.strip("*"))
            section = f"<section><p><strong>{safe_notice}</strong></p></section>"
            return _append_html_section(content, section)
        return f"{notice}\n\n{content}"

    if html_output:
        items = []
        for source in sources:
            title = html.escape(source.title)
            source_id = html.escape(source.source_id)
            excerpt = html.escape(source.excerpt)
            demo_note = " (synthetic demo content; not a Lenny source)" if source.is_demo else ""
            items.append(
                f"<li><strong>{title}</strong> (<code>{source_id}</code>{demo_note})"
                f"<p>{excerpt}</p></li>"
            )
        return _append_html_section(content, f"<section><h2>Sources</h2><ul>{''.join(items)}</ul></section>")

    references = ["### Sources"]
    for source in sources:
        title = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", source.title)
        excerpt = re.sub(r"\s+", " ", source.excerpt).strip()
        demo_note = " — synthetic demo content, not a Lenny source" if source.is_demo else ""
        references.append(
            f"- **{title}** (`{source.source_id}`{demo_note}): {excerpt}"
        )
    return f"{content.rstrip()}\n\n" + "\n".join(references)


def _append_html_section(content: str, section: str) -> str:
    match = re.search(r"</body\s*>", content, flags=re.IGNORECASE)
    if match:
        return f"{content[:match.start()]}{section}{content[match.start():]}"
    return f"{content.rstrip()}{section}"
