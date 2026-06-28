"""
Domain models.

These dataclasses are the vocabulary the whole application speaks. The
pipeline produces them, the database serialises them, and the UI/PDF render
them. Keeping them framework-free (no Streamlit, no SQL here) means every
layer can depend on them without circular imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AnswerStatus(str, Enum):
    VERIFIED = "Verified"
    ESTIMATED = "Estimated"
    UNKNOWN = "Unknown"
    NEEDS_REVIEW = "Needs Review"


@dataclass
class Source:
    """A single citation backing an answer."""
    title: str
    url: str
    kind: str = "web"  # keys into config.SOURCE_AUTHORITY
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Source":
        return cls(
            title=d.get("title", ""),
            url=d.get("url", ""),
            kind=d.get("kind", "web"),
            snippet=d.get("snippet", ""),
        )


@dataclass
class Evidence:
    """Raw material gathered *before* the LLM is invoked.

    `chunks` are (source, text) pairs. The answerer is only allowed to use
    these chunks — this is the structural guard against hallucination.
    """
    chunks: list[tuple[Source, str]] = field(default_factory=list)

    def add(self, source: Source, text: str) -> None:
        if text and text.strip():
            self.chunks.append((source, text.strip()))

    @property
    def sources(self) -> list[Source]:
        return [s for s, _ in self.chunks]

    def is_empty(self) -> bool:
        return len(self.chunks) == 0


@dataclass
class QuestionResult:
    question_id: str
    question_text: str
    section_id: str
    section_title: str
    answer: str = "Unknown"
    status: AnswerStatus = AnswerStatus.UNKNOWN
    confidence: int = 0  # 0-100
    sources: list[Source] = field(default_factory=list)
    reasoning: str = ""  # why the model answered this way (analyst transparency)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "answer": self.answer,
            "status": self.status.value,
            "confidence": self.confidence,
            "sources": [s.to_dict() for s in self.sources],
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QuestionResult":
        return cls(
            question_id=d["question_id"],
            question_text=d["question_text"],
            section_id=d["section_id"],
            section_title=d["section_title"],
            answer=d.get("answer", "Unknown"),
            status=AnswerStatus(d.get("status", "Unknown")),
            confidence=int(d.get("confidence", 0)),
            sources=[Source.from_dict(s) for s in d.get("sources", [])],
            reasoning=d.get("reasoning", ""),
        )


@dataclass
class Report:
    company_name: str
    website: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    results: list[QuestionResult] = field(default_factory=list)
    pdf_path: str = ""
    id: int | None = None  # assigned by the database on save

    def results_by_section(self) -> dict[str, list[QuestionResult]]:
        grouped: dict[str, list[QuestionResult]] = {}
        for r in self.results:
            grouped.setdefault(r.section_title, []).append(r)
        return grouped

    @property
    def average_confidence(self) -> int:
        scored = [r.confidence for r in self.results if r.status != AnswerStatus.UNKNOWN]
        return round(sum(scored) / len(scored)) if scored else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_name": self.company_name,
            "website": self.website,
            "created_at": self.created_at,
            "pdf_path": self.pdf_path,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Report":
        return cls(
            id=d.get("id"),
            company_name=d["company_name"],
            website=d["website"],
            created_at=d.get("created_at", ""),
            pdf_path=d.get("pdf_path", ""),
            results=[QuestionResult.from_dict(r) for r in d.get("results", [])],
        )
