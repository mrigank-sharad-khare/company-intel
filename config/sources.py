"""
Trusted public sources.

These are the specific, authoritative websites we want the app to check
directly — court records, government regulators, etc. — instead of relying
only on a general web search, which can surface SEO blogs instead of the
real record.

HOW THIS WORKS
  For a section listed below, the app runs ONE EXTRA search restricted to
  just these domains, on top of its normal general search. So we still get
  broad news coverage AND a direct check of the primary source.

TO ADD A NEW TRUSTED SOURCE
  Add one line below:   "domain.com": ("kind_label", ["SECTION_ID", ...])
    - domain.com  = the website, without https:// or www.
    - kind_label  = how trustworthy this type of source is. Must match a
                    key in config/settings.py -> SOURCE_AUTHORITY.
    - section ids = which question sections (S1, S5, S6, ...) this source
                    is relevant for. Use [] to apply it to every section.

NOTE: "Secretary of State" isn't included because every US state has its
own separate website (50 different domains) — there's no single one to add.
General search will still surface the right state's page when relevant.
Google News / Yahoo News are link-aggregators, not article hosts, so they
don't work well as a domain filter — Reuters and AP (the actual publishers)
cover that ground instead.
"""
from __future__ import annotations

TRUSTED_SOURCES: dict[str, tuple[str, list[str]]] = {
    # --- Legal / court records ------------------------------------------
    "courtlistener.com":   ("legal",          ["S5"]),
    "law.justia.com":      ("legal",          ["S5"]),
    "scholar.google.com":  ("legal",          ["S5"]),

    # --- Government regulators ------------------------------------------
    "ftc.gov":             ("government",     ["S5"]),
    "justice.gov":         ("government",     ["S5"]),
    "sec.gov":             ("sec",            ["S1", "S5"]),
    "consumerfinance.gov": ("government",     ["S5"]),
    "fda.gov":             ("government",     ["S7"]),   # recalls
    "epa.gov":             ("government",     ["S6"]),
    "osha.gov":            ("government",     ["S7"]),
    "cpsc.gov":            ("government",     ["S7"]),   # recalls

    # --- Patents ----------------------------------------------------------
    "patents.google.com":  ("patent",         ["S9"]),
    "uspto.gov":            ("government",    ["S9"]),

    # --- Sustainability ---------------------------------------------------
    "cdp.net":              ("sustainability",["S6"]),

    # --- Lobbying / political donations ------------------------------------
    "opensecrets.org":      ("lobbying",      ["S5"]),
    "lobbyview.org":        ("lobbying",      ["S5"]),
    "fec.gov":              ("government",    ["S5"]),

    # --- Business registry --------------------------------------------------
    "opencorporates.com":   ("registry",      ["S1"]),

    # --- Trusted news (applies to every section, []) -------------------------
    "reuters.com":          ("reuters",       []),
    "apnews.com":           ("major_news",    []),
}


def domains_for_section(section_id: str) -> list[str]:
    """All trusted domains relevant to one section, plus the
    general-purpose news sources that apply everywhere ([])."""
    return [
        domain for domain, (_, sections) in TRUSTED_SOURCES.items()
        if section_id in sections or not sections
    ]


def kind_for_domain(url: str) -> str | None:
    """How trustworthy a URL's domain is, or None if it's not on the list."""
    for domain, (kind, _sections) in TRUSTED_SOURCES.items():
        if domain in url:
            return kind
    return None