"""
Diagnostic tool.

It runs each research stage on its own and prints what it produced, so we can
see exactly where things go wrong. Unlike the app, it does NOT hide errors.

HOW TO USE:
  1. Put this file inside the company-intel folder (next to app.py).
  2. In the VS Code terminal (with your virtual environment active), run:

        python diagnose.py https://www.thecompanyyoutried.com

  3. Copy everything it prints and send it back.
"""
import sys
import traceback


def main(url: str) -> None:
    print("=" * 64)
    print("DIAGNOSING:", url)
    print("=" * 64)

    # ---- [0] Keys ---------------------------------------------------------
    from config.settings import LLM, SEARCH
    print("\n[0] KEYS / SETTINGS")
    print("  LLM provider      :", LLM.provider)
    print("  LLM key present   :", LLM.is_configured)
    print("  LLM model         :", LLM.anthropic_model)
    print("  Search provider   :", SEARCH.provider)
    print("  Search key present:", SEARCH.is_configured)

    # ---- [1] Company name -------------------------------------------------
    from core.pipeline import _normalise_url
    url = _normalise_url(url)
    from ingestion.company_detector import detect_company_name
    print("\n[1] COMPANY NAME")
    name = detect_company_name(url)
    print("  detected:", repr(name))

    # ---- [2] Website scraping --------------------------------------------
    from ingestion.page_discovery import discover_pages
    from ingestion.scraper import scrape
    print("\n[2] WEBSITE PAGES + TEXT LENGTH")
    pages = discover_pages(url)
    texts, total = {}, 0
    for p in pages:
        t = scrape(p)
        texts[p] = t
        total += len(t)
        print(f"  {len(t):>6} chars   {p}")
    print("  TOTAL website text:", total, "chars")
    if total == 0:
        print("  >>> PROBLEM: the website gave no text. It is probably blocking")
        print("      the scraper or is built entirely in JavaScript.")

    # ---- [3] Public search ------------------------------------------------
    from research.web_search import search
    print("\n[3] PUBLIC SEARCH")
    results = search(f"{name} company profile headquarters")
    print("  results returned:", len(results))
    for r in results[:3]:
        print("   -", r.url)
    if SEARCH.is_configured and not results:
        print("  >>> Search key is set but returned nothing. Check the key is valid.")

    # ---- [4] Direct AI test ----------------------------------------------
    from intelligence import llm_client
    print("\n[4] AI CONNECTION TEST")
    if not llm_client.is_available():
        print("  >>> PROBLEM: no AI key. Every answer will be blank/Unknown.")
        print("      Add ANTHROPIC_API_KEY to your .env file and restart.")
    else:
        try:
            reply = llm_client.complete("Reply with exactly: OK", "Say OK")
            print("  AI replied:", repr(reply[:80]))
        except Exception:
            print("  >>> PROBLEM: the AI call failed. Real error below:")
            traceback.print_exc()

    # ---- [5] Section 1 answering -----------------------------------------
    from config.questions import SECTIONS
    from research.evidence import build_section_evidence, build_website_evidence
    from intelligence.answerer import (
        _SYSTEM, _build_prompt, _format_evidence, _parse_json,
    )
    print("\n[5] ANSWERING SECTION 1 (Company Identity)")
    website_ev = build_website_evidence(texts)
    ev = build_section_evidence("S1", name, website_ev)
    etext, _ = _format_evidence(ev)
    print("  evidence chunks gathered:", len(ev.chunks))
    if not etext:
        print("  >>> No evidence at all -> answers will be Unknown.")
    elif llm_client.is_available():
        try:
            raw = llm_client.complete(_SYSTEM, _build_prompt(SECTIONS[0], etext))
            print("  raw AI reply (first 400 chars):")
            print("    " + raw[:400].replace("\n", " "))
            parsed = _parse_json(raw)
            print("  parsed answers:", len(parsed))
        except Exception:
            print("  >>> PROBLEM: answering failed. Real error below:")
            traceback.print_exc()

    print("\n" + "=" * 64)
    print("DONE. Copy everything above and send it back.")
    print("=" * 64)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose.py https://www.companywebsite.com")
    else:
        main(sys.argv[1])