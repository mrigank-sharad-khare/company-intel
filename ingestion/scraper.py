"""
Web scraper.

Two simple jobs:
  1. download a page's HTML
  2. turn that HTML into clean, readable text

It uses requests + BeautifulSoup (fast and simple). If a website is built
heavily with JavaScript and returns almost no text, it can optionally fall
back to a real headless browser (Playwright) — but only if you turned that
on in the .env file.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from config.settings import SCRAPE


def fetch_html(url: str) -> str:
    """Download a page's raw HTML. Returns '' (empty) on any failure."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": SCRAPE.user_agent},
            timeout=SCRAPE.request_timeout,
        )
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return ""


def extract_text(html: str) -> str:
    """Remove tags/scripts/menus and return human-readable text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())  # collapse repeated whitespace


def scrape(url: str) -> str:
    """Fetch a URL and return clean text (with optional browser fallback)."""
    text = extract_text(fetch_html(url))
    if len(text) < 200 and SCRAPE.use_playwright_fallback:
        text = _scrape_with_browser(url)
    return text


def _scrape_with_browser(url: str) -> str:
    """Headless-browser fallback. Imported lazily so the app still works
    even if Playwright is not installed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=SCRAPE.request_timeout * 1000)
            html = page.content()
            browser.close()
            return extract_text(html)
    except Exception:
        return ""
