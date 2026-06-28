"""
The pipeline.

This ties every step together in the exact order the spec asks for:

  detect company -> read website -> gather evidence -> AI answers each
  question -> confidence score -> done.

It reports progress through a callback so the user interface can show
"Reading website...", "Searching public sources...", etc. It deliberately
does NOT import Streamlit, so it can also be run from a plain script or a test.
"""
from __future__ import annotations

from typing import Callable

from config.questions import SECTIONS
from core.models import Report
from ingestion.company_detector import detect_company_name
from ingestion.page_discovery import discover_pages
from ingestion.scraper import scrape
from intelligence.answerer import answer_section
from research.evidence import build_section_evidence, build_website_evidence

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
        report.results.extend(answer_section(section, evidence))

    progress("Finishing up...", 0.97)
    return report


def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url
