"""
The pipeline.

This ties every step together in the exact order the spec asks for:

  detect company -> read website -> gather evidence -> AI answers each
  question -> confidence score -> done.

It reports progress through a callback so the user interface can show
"Reading website...", "Searching public sources...", etc. It deliberately
does NOT import Streamlit, so it can also be run from a plain script or a test.

SECOND-LOOK RETRY
  After the first pass, any question still marked "Unknown" gets ONE more,
  more specific search — using its own wording instead of the generic
  per-section query — and is checked again against the trusted source list
  in config/sources.py. This only runs for questions that are still blank,
  so it doesn't spend extra search credits on anything that already worked.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from config.questions import SECTIONS
from core.models import AnswerStatus, Evidence, Report
from ingestion.company_detector import detect_company_name
from ingestion.page_discovery import discover_pages
from ingestion.scraper import scrape
from intelligence.answerer import answer_section
from research.evidence import (
    build_fallback_evidence, build_section_evidence, build_website_evidence,
)

# A progress callback receives (message, fraction_complete) where fraction is 0..1.
Progress = Callable[[str, float], None]


def _noop(message: str, fraction: float) -> None:
    pass


def generate_report(website: str, progress: Progress = _noop) -> Report:
    website = _normalise_url(website)

    progress("Detecting company...", 0.05)
    company = detect_company_name(website)

    progress("Reading website...", 0.15)
    pages = {url: scrape(url) for url in discover_pages(website)}
    website_ev = build_website_evidence(pages)

    report = Report(company_name=company, website=website)

    total = len(SECTIONS)
    for i, section in enumerate(SECTIONS):
        progress(
            f"Searching public sources & generating intelligence — {section.title}...",
            0.2 + 0.7 * (i / total),
        )
        evidence = build_section_evidence(section.id, company, website_ev)
        results = answer_section(section, evidence)
        results = _retry_unknowns(section, company, evidence, results)
        report.results.extend(results)

    progress("Finishing up...", 0.97)
    return report


def _retry_unknowns(section, company: str, evidence: Evidence, results: list):
    """Give any still-Unknown questions in this section one more, more
    specific look before accepting Unknown as the final answer."""
    unknown = [r for r in results if r.status == AnswerStatus.UNKNOWN]
    if not unknown:
        return results

    seen_urls = {s.url for s in evidence.sources}
    question_texts = [r.question_text for r in unknown]
    fallback_ev = build_fallback_evidence(section.id, company, question_texts, seen_urls)
    if fallback_ev.is_empty():
        return results  # nothing new found — Unknown stands, which is honest

    combined = Evidence(chunks=evidence.chunks + fallback_ev.chunks)
    unknown_ids = {r.question_id for r in unknown}
    retry_section = replace(
        section, questions=tuple(q for q in section.questions if q.id in unknown_ids)
    )
    retry_results = {r.question_id: r for r in answer_section(retry_section, combined)}

    return [retry_results.get(r.question_id, r) for r in results]


def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url