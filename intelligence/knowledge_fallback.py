"""
Claude knowledge fallback.

READ THIS BEFORE TURNING IT ON.

Every other part of this app answers ONLY from evidence it actually found —
the company's website, search results, trusted government/legal sources.
That's what makes a "Verified" or "Estimated" answer trustworthy enough for
due-diligence use, and it's why the app says "Unknown" instead of guessing
when it can't find something.

This module is different ON PURPOSE. For any question still "Unknown" after
the normal research (including its second-look retry), it asks Claude
directly — no evidence attached, straight from its own training knowledge.
That answer can be wrong, outdated, or simply made up, because there is
nothing to check it against. So every answer this produces is always
labelled "AI Knowledge (Unverified)", given a low fixed confidence score,
and shown with no real source link — just a note that it's unsourced.

This is OFF by default (CLAUDE_FALLBACK_ENABLED=false in .env). Turn it on
only once you're comfortable with that trade-off: more filled-in answers,
in exchange for some of them being untraceable guesses.
"""
from __future__ import annotations

from config.settings import KNOWLEDGE_FALLBACK
from core.models import AnswerStatus, QuestionResult, Source

# Always low and fixed — this is NOT calculated from sources, because there
# is no real source. It exists only so the answer isn't shown as 0% (which
# would look identical to "found nothing") while staying clearly low-trust.
UNVERIFIED_CONFIDENCE = 20

_SYSTEM = (
    "You are answering from general knowledge only — no documents have been "
    "provided. Answer in 1 to 3 short sentences. If you genuinely don't know "
    "or aren't reasonably confident, reply with exactly: Unknown. Do not "
    "pad an uncertain guess to sound more confident than it is."
)


def fill_unknowns_from_claude(company: str,
                              results: list[QuestionResult]) -> list[QuestionResult]:
    """For any result still marked Unknown, ask Claude directly and fill it
    in (clearly labelled as unverified). Does nothing if the fallback is
    turned off or not configured. Returns a new list."""
    if not KNOWLEDGE_FALLBACK.enabled or not KNOWLEDGE_FALLBACK.is_configured:
        return results

    return [
        _ask_claude(company, r) if r.status == AnswerStatus.UNKNOWN else r
        for r in results
    ]


def _ask_claude(company: str, r: QuestionResult) -> QuestionResult:
    from intelligence.llm_client import complete_claude_knowledge

    try:
        reply = complete_claude_knowledge(
            _SYSTEM, f"Company: {company}\nQuestion: {r.question_text}"
        ).strip()
    except Exception:
        return r  # any failure -> leave it Unknown, never crash the report

    if not reply or reply.lower().startswith("unknown"):
        return r  # Claude also doesn't know -> Unknown stands, honestly

    return QuestionResult(
        question_id=r.question_id,
        question_text=r.question_text,
        section_id=r.section_id,
        section_title=r.section_title,
        answer=reply,
        status=AnswerStatus.AI_KNOWLEDGE,
        confidence=UNVERIFIED_CONFIDENCE,
        sources=[Source(
            title="Claude — general knowledge (no specific source)",
            url="",
            kind="ai_knowledge",
        )],
        reasoning="Answered from the AI's general knowledge, not a found "
                  "source. Treat as a lead to verify, not a fact.",
    )