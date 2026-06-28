"""
Company-name detection.

The user only gives a website, so we guess the company name from the page's
own information, from most reliable to least:
  1. the <meta property="og:site_name"> tag   (most reliable)
  2. the <title> tag, cleaned up
  3. the domain name itself                    (last resort)
"""
from __future__ import annotations

import re

import tldextract
from bs4 import BeautifulSoup

from ingestion.scraper import fetch_html

# Common junk that websites append to their <title> and that isn't the name.
_TITLE_NOISE = re.compile(
    r"\s*[|\-–—:]\s*(home|official site|welcome.*|homepage).*$", re.IGNORECASE
)


def detect_company_name(url: str) -> str:
    html = fetch_html(url)
    if html:
        soup = BeautifulSoup(html, "lxml")

        # 1. og:site_name
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if og and og.get("content"):
            return og["content"].strip()

        # 2. <title>, cleaned
        if soup.title and soup.title.string:
            title = _TITLE_NOISE.sub("", soup.title.string).strip()
            title = re.split(r"\s*[|\-–—]\s*", title)[0].strip()
            if title:
                return title

    # 3. domain fallback: "acme.com" -> "Acme"
    domain = tldextract.extract(url).domain
    return domain.capitalize() if domain else "Unknown Company"
