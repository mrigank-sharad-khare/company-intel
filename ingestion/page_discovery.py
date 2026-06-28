"""
Page discovery.

Given a company's homepage, look at its links and keep the ones pointing to
the pages we care about (about, leadership, sustainability, news, etc.).
We stay on the same website and cap how many pages we collect.
"""
from __future__ import annotations

from urllib.parse import urljoin

import tldextract
from bs4 import BeautifulSoup

from config.settings import SCRAPE
from ingestion.scraper import fetch_html

# A link is kept if any of these words appears in its URL or text.
KEYWORDS = [
    "about", "who-we-are", "our-story", "company",
    "leadership", "team", "management", "executive", "board",
    "sustainability", "esg", "environment", "responsibility",
    "news", "press", "media", "newsroom",
    "investor", "investors",
    "product", "service", "solution",
    "location",
]


def _same_domain(base: str, link: str) -> bool:
    return tldextract.extract(base).domain == tldextract.extract(link).domain


def discover_pages(homepage_url: str) -> list[str]:
    """Return the homepage plus a handful of relevant inner pages."""
    found: list[str] = [homepage_url]
    html = fetch_html(homepage_url)
    if not html:
        return found

    soup = BeautifulSoup(html, "lxml")
    seen = {homepage_url.rstrip("/")}

    for a in soup.find_all("a", href=True):
        full = urljoin(homepage_url, a["href"].strip())
        if not full.startswith("http") or not _same_domain(homepage_url, full):
            continue

        key = full.split("#")[0].rstrip("/")
        if key in seen:
            continue

        haystack = (a["href"] + " " + a.get_text(" ", strip=True)).lower()
        if any(word in haystack for word in KEYWORDS):
            seen.add(key)
            found.append(key)

        if len(found) >= SCRAPE.max_pages:
            break

    return found
