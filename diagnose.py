"""
Diagnostic tool.

This version focuses on ANSWERING ONE QUESTION: "why did this section come
back mostly Unknown?" It shows you the actual evidence text the app gathered
for a section — in plain English — so you can judge for yourself whether the
problem is bad evidence (most common) or the AI itself.

HOW TO USE
  python diagnose.py <website> [SECTION_ID]

  SECTION_ID is optional and defaults to S4 (Economic Intelligence).
  Pass a different one to check another section: S1, S2, S3, S5, S6, S7,
  S8, S9.

  Example:
    python diagnose.py https://wd40company.com S4
    python diagnose.py https://wd40company.com S5

  Copy everything it prints and send it back.
"""
import sys
import traceback

# Words that SHOULD show up somewhere in the evidence if it's actually
# relevant to economic-driver questions. This is just a quick sanity check
# for our own reading — the app itself doesn't use this list.
ECONOMIC_KEYWORDS = [
    "inflation", "interest rate", "commodity", "raw material",
    "construction", "government spending", "seasonal", "cyclical",
    "defensive", "recession", "gdp", "tariff",
]


def main(url: str, section_id: str) -> None:
    print("=" * 64)
    print(f"DIAGNOSING: {url}  (section: {section_id})")
    print("=" * 64)

    # ---- [0] Keys ----------------------------------------------------------
    from config.settings import LLM, SEARCH
    print("\n[0] KEYS / SETTINGS")
    print("  LLM key present   :", LLM.is_configured)
    print("  Search key present:", SEARCH.is_configured)
    if not LLM.is_configured:
        print("  NOTE: with no AI key, a real report would come back Unknown")
        print("        EVERYWHERE right now, not just this section. The checks")
        print("        below still work without it — they inspect the evidence")
        print("        the app would hand to the AI, which we can judge on its")
        print("        own merits.")

    # ---- [1] Company name ----------------------------------------------------
    from core.pipeline import _normalise_url
    url = _normalise_url(url)
    from ingestion.company_detector import detect_company_name
    name = detect_company_name(url)
    print("\n[1] COMPANY NAME:", repr(name))

    # ---- [2] Website scraping -------------------------------------------------
    from ingestion.page_discovery import discover_pages
    from ingestion.scraper import scrape
    print("\n[2] WEBSITE PAGES")
    pages = discover_pages(url)
    texts = {p: scrape(p) for p in pages}
    print("  pages read:", len(pages), "| total chars:", sum(len(t) for t in texts.values()))

    # ---- [3] Section info ------------------------------------------------------
    from config.questions import SECTIONS
    from config.sources import domains_for_section
    section = next((s for s in SECTIONS if s.id == section_id), None)
    if section is None:
        valid = ", ".join(s.id for s in SECTIONS)
        print(f"\n>>> Unknown section id '{section_id}'. Valid ids: {valid}")
        return

    print(f"\n[3] SECTION: {section.title} ({section.id})")
    print("  questions in this section:")
    for q in section.questions:
        print("   -", q.text)
    trusted = domains_for_section(section.id)
    print("  trusted domains checked for this section:",
          trusted or "(none specific to this section — general web only)")

    # ---- [4] Evidence actually gathered for this section ------------------------
    from research.evidence import (
        SECTION_QUERIES, build_section_evidence, build_website_evidence,
    )
    print(f"\n[4] EVIDENCE GATHERED FOR {section.id}")
    template = SECTION_QUERIES.get(section.id)
    print("  search query used:", template.format(company=name) if template else "(none — website text only)")
    website_ev = build_website_evidence(texts)
    ev = build_section_evidence(section.id, name, website_ev)
    print("  total evidence chunks:", len(ev.chunks))
    for i, (src, text) in enumerate(ev.chunks):
        print(f"\n  [{i}] {src.kind:18s} {src.url}")
        print("      preview:", text[:220].replace("\n", " "))

    # ---- [5] Keyword relevance check (only meaningful for S4) -------------------
    if section_id == "S4":
        combined = " ".join(text.lower() for _, text in ev.chunks)
        print("\n[5] DOES THE EVIDENCE ACTUALLY MENTION ECONOMIC-SENSITIVITY TERMS?")
        found = [k for k in ECONOMIC_KEYWORDS if k in combined]
        missing = [k for k in ECONOMIC_KEYWORDS if k not in combined]
        print("  found   :", found or "(none)")
        print("  missing :", missing)
        if not found:
            print("  >>> None of these terms appear anywhere in the evidence.")
            print("      The AI has nothing to work with for most of these")
            print("      questions, so it correctly says 'Unknown' rather than")
            print("      guessing. The fix is better evidence, not a different")
            print("      AI prompt — see the note at the end of this report.")

    # ---- [6] What would the fallback ('second-look') search find? ---------------
    from research.evidence import build_fallback_evidence
    print("\n[6] FALLBACK SEARCH (the 'second look' the app runs for Unknowns)")
    seen = {s.url for s in ev.sources}
    question_texts = [q.text for q in section.questions]
    fallback_ev = build_fallback_evidence(section.id, name, question_texts, seen)
    print("  extra chunks found:", len(fallback_ev.chunks))
    for i, (src, text) in enumerate(fallback_ev.chunks):
        print(f"\n  [{i}] {src.kind:18s} {src.url}")
        print("      preview:", text[:220].replace("\n", " "))
    if fallback_ev.is_empty():
        print("  >>> The fallback search ALSO found nothing new.")

    # ---- [7] Direct AI test on this evidence (only if a key is present) ---------
    from intelligence import llm_client
    print("\n[7] AI TEST ON THIS SECTION'S EVIDENCE")
    if not llm_client.is_available():
        print("  skipped — no AI key configured.")
    elif ev.is_empty():
        print("  skipped — no evidence to give the AI.")
    else:
        from intelligence.answerer import (
            _SYSTEM, _build_prompt, _format_evidence, _parse_json,
        )
        try:
            etext, _ = _format_evidence(ev)
            raw = llm_client.complete(_SYSTEM, _build_prompt(section, etext))
            print("  raw AI reply (first 500 chars):")
            print("   ", raw[:500].replace("\n", " "))
        except Exception:
            print("  >>> AI call failed:")
            traceback.print_exc()

    print("\n" + "=" * 64)
    if section_id == "S4":
        print("LIKELY FIX (if 'found' was empty above): the answer to most of")
        print("these questions normally lives in a public company's SEC 10-K")
        print("'Risk Factors' section, not on the company website or in generic")
        print("profile sites. We can add sec.gov to this section's trusted")
        print("sources and sharpen the search query to target that.")
    print("DONE. Copy everything above and send it back.")
    print("=" * 64)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose.py https://www.companywebsite.com [SECTION_ID]")
        print("  SECTION_ID defaults to S4 (Economic Intelligence).")
    else:
        section_arg = sys.argv[2] if len(sys.argv) > 2 else "S4"
        main(sys.argv[1], section_arg.upper())