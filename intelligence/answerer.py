"""
Answerer — the AI step.

It takes ONE section's questions plus the evidence gathered for that section,
and asks the LLM to answer each question using only that evidence. The model
must reply in JSON, which we parse into QuestionResult objects. The confidence
number is computed separately (confidence.py) so the AI can't invent it.

If there's no evidence or no LLM key, every answer becomes 'Unknown'. That is
the honest fallback the spec asks for.
"""
from __future__ import annotations

import json

from config.questions import Section
from core.models import AnswerStatus, Evidence, QuestionResult, Source
from intelligence import llm_client
from intelligence.confidence import score

_EVIDENCE_BUDGET = 12000  # max characters of evidence sent to the model

_SYSTEM = (
    "You are a meticulous due-diligence research analyst. You answer ONLY "
    "from the numbered EVIDENCE provided. You never use outside knowledge. "
    "If the evidence does not support an answer, you respond with 'Unknown'. "
    "You always return valid JSON and nothing else."
)


def answer_section(section: Section, evidence: Evidence) -> list[QuestionResult]:
    evidence_text, sources = _format_evidence(evidence)

    # No usable evidence or no LLM configured -> all Unknown.
    if not evidence_text or not llm_client.is_available():
        return [_unknown(section, q) for q in section.questions]

    try:
        raw = llm_client.complete(_SYSTEM, _build_prompt(section, evidence_text))
        items = _parse_json(raw)
    except Exception:
        return [_unknown(section, q) for q in section.questions]

    by_id = {it.get("id"): it for it in items if isinstance(it, dict)}
    return [
        _build_result(section, q, by_id[q.id], sources)
        if q.id in by_id else _unknown(section, q)
        for q in section.questions
    ]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _format_evidence(evidence: Evidence) -> tuple[str, list[Source]]:
    """Number each evidence chunk so the model can cite it by its index."""
    lines, sources, budget = [], [], _EVIDENCE_BUDGET
    for i, (src, text) in enumerate(evidence.chunks):
        snippet = text[:1500]
        if budget - len(snippet) <= 0:
            break
        budget -= len(snippet)
        lines.append(f"[{i}] SOURCE: {src.title} ({src.url})\n{snippet}")
        sources.append(src)
    return "\n\n".join(lines), sources


def _build_prompt(section: Section, evidence_text: str) -> str:
    questions = "\n".join(
        f'- id "{q.id}": {q.text}' + (f" (hint: {q.hint})" if q.hint else "")
        for q in section.questions
    )
    return (
        f"EVIDENCE:\n{evidence_text}\n\n"
        f"QUESTIONS (section: {section.title}):\n{questions}\n\n"
        "For EACH question return an object with these keys:\n"
        '  "id": the question id,\n'
        '  "answer": a short factual answer, or "Unknown",\n'
        '  "status": one of "Verified", "Estimated", "Unknown", "Needs Review",\n'
        '  "sources": list of the evidence numbers you used, e.g. [0, 2],\n'
        '  "reasoning": one short sentence.\n'
        "Return a JSON array of these objects and nothing else."
    )


def _build_result(section, q, item, all_sources) -> QuestionResult:
    answer = str(item.get("answer", "Unknown")).strip() or "Unknown"

    try:
        status = AnswerStatus(item.get("status", "Unknown"))
    except ValueError:
        status = AnswerStatus.NEEDS_REVIEW
    if answer.lower() == "unknown":
        status = AnswerStatus.UNKNOWN

    # Resolve the evidence numbers the model cited into real sources.
    used, seen = [], set()
    for idx in item.get("sources", []):
        if isinstance(idx, int) and 0 <= idx < len(all_sources):
            s = all_sources[idx]
            if s.url not in seen:
                seen.add(s.url)
                used.append(s)

    return QuestionResult(
        question_id=q.id,
        question_text=q.text,
        section_id=section.id,
        section_title=section.title,
        answer=answer,
        status=status,
        confidence=score(status, used),
        sources=used,
        reasoning=str(item.get("reasoning", "")).strip(),
    )


def _unknown(section, q) -> QuestionResult:
    return QuestionResult(
        question_id=q.id,
        question_text=q.text,
        section_id=section.id,
        section_title=section.title,
        answer="Unknown",
        status=AnswerStatus.UNKNOWN,
        confidence=0,
        sources=[],
        reasoning="",
    )


def _parse_json(raw: str):
    """Pull the JSON array out of the reply, tolerating any stray text."""
    raw = raw.strip()
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)
