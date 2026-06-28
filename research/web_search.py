"""
Public web search (pluggable).

This powers the "search the public internet / filings / news" steps. The
default provider is Tavily. If no search key is configured, search simply
returns nothing and the tool relies on the company website alone — it never
crashes.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import SEARCH


@dataclass
class SearchResult:
    title: str
    url: str
    content: str


def search(query: str, domains: list[str] | None = None) -> list[SearchResult]:
    if SEARCH.provider == "tavily" and SEARCH.tavily_api_key:
        return _tavily_search(query, domains)
    return []  # no provider configured -> empty, handled gracefully upstream


def _tavily_search(query: str, domains: list[str] | None = None) -> list[SearchResult]:
    try:
        from tavily import TavilyClient
    except ImportError:
        return []
    try:
        client = TavilyClient(api_key=SEARCH.tavily_api_key)
        kwargs = {"include_domains": domains} if domains else {}
        resp = client.search(
            query=query,
            max_results=SEARCH.max_results_per_query,
            search_depth="basic",
            **kwargs,
        )
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
            )
            for r in resp.get("results", [])
        ]
    except Exception:
        return []