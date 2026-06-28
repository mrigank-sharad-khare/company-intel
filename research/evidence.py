"""
Evidence assembly.

For each section of the questionnaire we build a pool of evidence BEFORE the
AI is ever called. Evidence = the company's own website text + a couple of
targeted public web searches relevant to that section's topic.

The AI is later only allowed to use this evidence. That is the key reason it
cannot invent answers.
"""
from __future__ import annotations

from core.models import Evidence, Source
from research.web_search import search

# One focused search angle per section. {company} is filled in at run time.
SECTION_QUERIES = {
    "S1": "{company} company profile headquarters revenue employees",
    "S2": "{company} history founded founders",
    "S3": "{company} office locations countries operations",
    "S4": "{company} industry market demand economic drivers",
    "S5": "{company} lawsuit litigation investigation regulatory",
    "S6": "{company} sustainability environment net zero emissions",
    "S7": "{company} recall safety violation fraud complaint",
    "S8": "{company} CEO leadership executives board",
    "S9": "{company} business model competitors revenue growth",
}


def _classify(url: str) -> str:
    """Decide how trustworthy a source is, based on its web address."""
    u = url.lower()
    if "sec.gov" in u:
        return "sec"
    if ".gov" in u:
        return "government"
    if "reuters.com" in u:
        return "reuters"
    if "linkedin.com" in u:
        return "linkedin"
    return "news_article"


def build_website_evidence(pages: dict[str, str]) -> Evidence:
    """pages = {url: text}. Returns evidence drawn from the company's site."""
    ev = Evidence()
    for url, text in pages.items():
        if text:
            src = Source(title="Company Website", url=url, kind="official_website")
            ev.add(src, text[:4000])  # cap each page so no single one dominates
    return ev


def build_section_evidence(section_id: str, company: str,
                           website_ev: Evidence) -> Evidence:
    """Combine the shared website evidence with section-specific searches."""
    ev = Evidence()

    # 1. reuse the company website evidence
    for src, text in website_ev.chunks:
        ev.add(src, text)

    # 2. add a targeted public search for this section's topic
    template = SECTION_QUERIES.get(section_id)
    if template:
        for r in search(template.format(company=company)):
            if r.content:
                src = Source(
                    title=r.title or r.url,
                    url=r.url,
                    kind=_classify(r.url),
                    snippet=r.content[:200],
                )
                ev.add(src, r.content[:1500])

    return ev
