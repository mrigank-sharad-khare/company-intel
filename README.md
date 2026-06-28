# Company Intelligence Report Generator

An internal-style research tool that takes a single company **website** and
produces a structured intelligence report answering a fixed due-diligence
questionnaire (9 sections, ~80 questions). It gathers evidence first, then
uses an LLM *only to interpret that evidence* — never to invent facts. Every
answer carries a confidence score, a status, and clickable sources, and the
whole report exports to an analyst working-paper PDF.

## Design at a glance

The system is a **research pipeline**, not a chatbot. The flow is strictly
evidence-first:

```
website
  -> detect company name
  -> discover & scrape key pages (about / leadership / sustainability / news)
  -> public web/filings/news search (per topic)
  -> bundle EVIDENCE per question
  -> LLM answers each question CONSTRAINED to that evidence  <-- AI runs last
  -> deterministic confidence score
  -> persist (SQLite)
  -> render (Streamlit) + export (ReportLab PDF)
```

The anti-hallucination guarantee is structural: the answerer is only ever
handed the evidence chunks that were actually collected, and is instructed to
return `Unknown` when the evidence doesn't support an answer.

## Folder structure

```
company-intel/
├── app.py                  # Streamlit entry point (thin)
├── config/
│   ├── settings.py         # env, keys, paths, source-authority weights
│   └── questions.py        # the 9-section question bank (source of truth)
├── core/
│   ├── models.py           # Source, Evidence, QuestionResult, Report
│   └── pipeline.py         # orchestrates the workflow
├── ingestion/
│   ├── company_detector.py # website -> company name
│   ├── page_discovery.py   # find about/leadership/etc. pages
│   └── scraper.py          # fetch + parse (requests/BS4, playwright fallback)
├── research/
│   ├── web_search.py       # pluggable search provider
│   └── evidence.py         # assemble evidence per question
├── intelligence/
│   ├── llm_client.py       # provider-agnostic LLM wrapper
│   ├── answerer.py         # evidence -> answer (JSON, schema-validated)
│   └── confidence.py       # deterministic scoring
├── storage/
│   └── database.py         # SQLite persistence
├── export/
│   └── pdf_report.py       # working-paper PDF with Analyst Notes column
└── ui/
    ├── styles.py           # corporate CSS
    ├── sidebar.py
    └── report_view.py
```

No module exceeds ~300 lines; each layer depends only on `core.models` and
`config`, never on the UI.

## Two external dependencies you should know about up front

1. **An LLM API key** (Anthropic by default). The tool interprets evidence
   with an LLM, so this is required for answering.
2. **A web-search API key** (Tavily by default). "Search the public internet /
   filings / government sources" cannot be done by scraping the company site
   alone. Without a search key the tool still runs, but evidence is limited to
   the company's own website and most non-website questions will return
   `Unknown` — which is the correct, honest behaviour.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium        # only if USE_PLAYWRIGHT=true
cp .env.example .env               # then fill in your keys
streamlit run app.py
```

## Build status

- [x] Foundation: config, question bank, domain models, SQLite storage
- [ ] Ingestion: company detection, page discovery, scraper
- [ ] Research: search provider + evidence assembly
- [ ] Intelligence: LLM client, answerer, confidence engine
- [ ] Orchestration: pipeline
- [ ] Export: working-paper PDF
- [ ] UI: Streamlit app, sidebar, report view, styles
