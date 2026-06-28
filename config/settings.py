"""
Central configuration.

Everything that varies by environment (API keys, model names, file paths)
lives here and is read once at import time. No other module should call
os.getenv directly — they import from here. That keeps configuration in a
single auditable place.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional; env can be set by the shell instead
    pass


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "reports.db"))
PDF_OUTPUT_DIR = Path(os.getenv("PDF_OUTPUT_DIR", DATA_DIR / "reports"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# LLM provider
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "anthropic").lower()
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    # Set this to a model you have access to. Check current model strings at
    # https://docs.claude.com/en/docs/about-claude/models
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1500"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    @property
    def is_configured(self) -> bool:
        if self.provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.provider == "openai":
            return bool(self.openai_api_key)
        return False


# --------------------------------------------------------------------------- #
# Web search provider
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SearchConfig:
    provider: str = os.getenv("SEARCH_PROVIDER", "tavily").lower()
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    max_results_per_query: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))

    @property
    def is_configured(self) -> bool:
        if self.provider == "tavily":
            return bool(self.tavily_api_key)
        return False


# --------------------------------------------------------------------------- #
# Scraping
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ScrapeConfig:
    user_agent: str = os.getenv(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (compatible; CompanyIntelBot/1.0; research)",
    )
    request_timeout: int = int(os.getenv("SCRAPE_TIMEOUT", "15"))
    max_pages: int = int(os.getenv("SCRAPE_MAX_PAGES", "12"))
    # Whether to fall back to a headless browser for JS-heavy sites.
    use_playwright_fallback: bool = (
        os.getenv("USE_PLAYWRIGHT", "false").lower() == "true"
    )


# --------------------------------------------------------------------------- #
# Claude "general knowledge" fallback (optional, OFF by default)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class KnowledgeFallbackConfig:
    """Settings for the optional Claude fallback.

    This reuses the SAME ANTHROPIC_API_KEY as the main LLM settings above —
    no separate key needed. It's kept as its own config block only so the
    on/off switch and model choice are separate from the main pipeline.
    """
    enabled: bool = os.getenv("CLAUDE_FALLBACK_ENABLED", "false").lower() == "true"
    model: str = os.getenv("CLAUDE_FALLBACK_MODEL", "claude-sonnet-4-6")

    @property
    def is_configured(self) -> bool:
        return bool(LLM.anthropic_api_key)


LLM = LLMConfig()
SEARCH = SearchConfig()
SCRAPE = ScrapeConfig()
KNOWLEDGE_FALLBACK = KnowledgeFallbackConfig()

# Authority weighting used by the confidence engine. Higher = more trusted.
# The official company website is intentionally the highest non-regulatory
# source, per the spec. Regulatory/government filings rank above it because
# they are independently verified.
SOURCE_AUTHORITY = {
    "official_website": 0.95,
    "sec": 1.0,
    "government": 1.0,
    "secretary_of_state": 1.0,
    "regulatory": 1.0,
    "legal": 0.95,          # court records (e.g. CourtListener, Justia)
    "lobbying": 0.9,        # federal filings (e.g. OpenSecrets, FEC)
    "patent": 0.9,          # patent offices (e.g. Google Patents, USPTO)
    "registry": 0.85,       # business registries (e.g. OpenCorporates)
    "sustainability": 0.75, # self-reported but cross-checked (e.g. CDP)
    "reuters": 0.85,
    "major_news": 0.8,
    "linkedin": 0.7,
    "news_article": 0.65,
    "web": 0.5,
    "ai_knowledge": 0.2,    # AI knowledge fallback — no real source, always low
    "unknown": 0.3,
}