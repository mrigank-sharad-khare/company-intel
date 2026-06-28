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
from config.sources import domains_for_section, kind_for_domain
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
    """Decide how trustworthy a source is, based on its web address.
    Checks our curated trusted-source list first, then falls back to
    simple guesses for anything not on that list."""
    trusted = kind_for_domain(url)
    if trusted:
        return trusted
    u = url.lower()
    if "sec.gov" in u:
        return "sec"
    if ".gov" in u:
        return "government"
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
    seen_urls: set[str] = set()

    # 1. reuse the company website evidence
    for src, text in website_ev.chunks:
        ev.add(src, text)
        seen_urls.add(src.url)

    template = SECTION_QUERIES.get(section_id)
    if not template:
        return ev
    query = template.format(company=company)

    # 2. a general public search for this section's topic
    _add_search_results(ev, search(query), seen_urls)

    # 3. an EXTRA search restricted to our trusted primary sources for this
    #    section (court records, regulators, etc.), if any apply here.
    domains = domains_for_section(section_id)
    if domains:
        _add_search_results(ev, search(query, domains=domains), seen_urls)

    return ev


def _add_search_results(ev: Evidence, results, seen_urls: set[str]) -> None:
    for r in results:
        if not r.content or r.url in seen_urls:
            continue
        seen_urls.add(r.url)
        src = Source(
            title=r.title or r.url,
            url=r.url,
            kind=_classify(r.url),
            snippet=r.content[:200],
        )
        ev.add(src, r.content[:1500])


def build_fallback_evidence(section_id: str, company: str,
                            question_texts: list[str],
                            seen_urls: set[str]) -> Evidence:
    """A second, more specific search for questions that are still
    unanswered after the first pass.

    Instead of the generic one-line-per-section query, this uses the actual
    wording of the unanswered questions, then checks both the general web
    and (if any apply to this section) our trusted primary sources again.
    Only called for questions still marked Unknown, so it doesn't spend
    extra search credits on things that already worked.
    """
    ev = Evidence()
    if not question_texts:
        return ev

    # Keep the query a sane length — a handful of question topics is enough.
    query = company + " " + " ".join(question_texts[:5])

    _add_search_results(ev, search(query), seen_urls)

    domains = domains_for_section(section_id)
    if domains:
        _add_search_results(ev, search(query, domains=domains), seen_urls)

    return ev