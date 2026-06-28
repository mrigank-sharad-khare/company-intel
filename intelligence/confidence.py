"""
Confidence scoring (deterministic).

The AI does NOT pick the confidence number — that would just be another
guess. Instead we calculate it from things we can actually measure:
  - the status the AI assigned (Verified / Estimated / Unknown / Needs Review)
  - how authoritative the best supporting source is (official site, SEC, ...)
  - how many sources backed the answer
"""
from __future__ import annotations

from config.settings import SOURCE_AUTHORITY
from core.models import AnswerStatus, Source


def score(status: AnswerStatus, sources: list[Source]) -> int:
    if status == AnswerStatus.UNKNOWN or not sources:
        return 0

    # The most authoritative source sets the base score.
    best = max(
        SOURCE_AUTHORITY.get(s.kind, SOURCE_AUTHORITY["unknown"]) for s in sources
    )
    base = best * 100

    # Extra sources add a little (corroboration), capped at +12.
    corroboration = min(len(sources) - 1, 3) * 4
    value = base + corroboration

    # Soft caps: an estimate or a flagged answer can't score like a fact.
    if status == AnswerStatus.ESTIMATED:
        value = min(value, 70)
    if status == AnswerStatus.NEEDS_REVIEW:
        value = min(value, 55)

    return max(0, min(100, round(value)))
