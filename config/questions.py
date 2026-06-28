"""
The research questionnaire.

This is the single source of truth for *what* the tool investigates. The
pipeline iterates over these questions; the PDF and UI render them. Adding,
removing, or rewording a question happens only here — nothing else hard-codes
question text.

Each question carries a stable `id` so that stored answers in the database
remain linked even if wording is later refined.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str            # stable identifier, e.g. "S1.company_name"
    text: str          # the human-readable question / field label
    hint: str = ""     # guidance passed to the LLM about what a good answer is


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    questions: tuple[Question, ...]


def _q(sid: str, key: str, text: str, hint: str = "") -> Question:
    return Question(id=f"{sid}.{key}", text=text, hint=hint)


SECTIONS: tuple[Section, ...] = (
    Section(
        id="S1",
        title="Company Identity",
        questions=(
            _q("S1", "company_name", "Company Name"),
            _q("S1", "website", "Website"),
            _q("S1", "industry", "Industry"),
            _q("S1", "sub_industry", "Sub-Industry"),
            _q("S1", "headquarters", "Headquarters"),
            _q("S1", "founded", "Founded", "A year. Prefer an official source."),
            _q("S1", "ownership_type",
               "Ownership Type",
               "Public, private, PE-owned, subsidiary, etc."),
            _q("S1", "parent_company", "Parent Company"),
            _q("S1", "employees",
               "Estimated Employees",
               "Give a band (e.g. 500-1,000) when an exact figure is unknown."),
            _q("S1", "revenue_band",
               "Estimated Revenue Band",
               "A band (e.g. $50M-$100M). Mark Estimated unless filings confirm."),
            _q("S1", "primary_products", "Primary Products"),
            _q("S1", "primary_services", "Primary Services"),
        ),
    ),
    Section(
        id="S2",
        title="Historical Intelligence",
        questions=(
            _q("S2", "founders", "Who founded the company?"),
            _q("S2", "founded_when", "When was it founded?"),
            _q("S2", "founded_why", "Why was it founded?"),
            _q("S2", "original_problem",
               "What original problem was it trying to solve?"),
            _q("S2", "problem_still_exists",
               "Does that problem still exist today?"),
            _q("S2", "model_changed",
               "Has the company changed its business model?"),
            _q("S2", "milestones", "Major milestones"),
            _q("S2", "acquisitions", "Major acquisitions"),
            _q("S2", "expansions", "Major expansions"),
            _q("S2", "pivots", "Major pivots"),
        ),
    ),
    Section(
        id="S3",
        title="Geographical Intelligence",
        questions=(
            _q("S3", "hq_location", "Where is headquarters?"),
            _q("S3", "offices", "Office locations"),
            _q("S3", "manufacturing", "Manufacturing locations"),
            _q("S3", "countries_served", "Countries served"),
            _q("S3", "customer_locations", "Primary customer locations"),
            _q("S3", "distribution", "Distribution regions"),
            _q("S3", "concentration_risk", "Regional concentration risks"),
        ),
    ),
    Section(
        id="S4",
        title="Economic Intelligence",
        questions=(
            _q("S4", "demand_drivers", "What industries generate demand?"),
            _q("S4", "cyclical", "Is demand cyclical?"),
            _q("S4", "defensive", "Is demand defensive?"),
            _q("S4", "inflation", "Does inflation help or hurt?"),
            _q("S4", "interest_rates",
               "Does interest rate movement affect the business?"),
            _q("S4", "commodities",
               "Does commodity pricing affect the business?"),
            _q("S4", "construction",
               "Does construction activity affect the business?"),
            _q("S4", "gov_spending",
               "Does government spending affect demand?"),
            _q("S4", "seasonality", "Seasonality"),
            _q("S4", "economic_risks", "Major economic risks"),
        ),
    ),
    Section(
        id="S5",
        title="Political and Legal Intelligence",
        questions=(
            _q("S5", "gov_contracts", "Government contracts"),
            _q("S5", "investigations", "Government investigations"),
            _q("S5", "active_litigation", "Active litigation"),
            _q("S5", "past_litigation", "Past litigation"),
            _q("S5", "regulatory", "Regulatory concerns"),
            _q("S5", "trade_restrictions", "Trade restrictions"),
            _q("S5", "tariffs", "Tariff exposure"),
            _q("S5", "foreign_ownership",
               "Foreign ownership restrictions"),
            _q("S5", "donations",
               "Political donations (if publicly available)"),
            _q("S5", "lobbying",
               "Lobbying activity (if publicly available)"),
        ),
    ),
    Section(
        id="S6",
        title="Environmental Intelligence",
        questions=(
            _q("S6", "commitments", "Environmental commitments"),
            _q("S6", "net_zero", "Net-zero pledge"),
            _q("S6", "sustainability", "Sustainability initiatives"),
            _q("S6", "epa", "EPA issues (if available)"),
            _q("S6", "env_lawsuits", "Environmental lawsuits"),
            _q("S6", "carbon", "Carbon reduction initiatives"),
            _q("S6", "waste", "Waste management"),
            _q("S6", "renewables", "Renewable energy usage"),
            _q("S6", "certifications", "Environmental certifications"),
        ),
    ),
    Section(
        id="S7",
        title="Ethical Intelligence",
        questions=(
            _q("S7", "discrimination", "Discrimination lawsuits"),
            _q("S7", "fraud", "Fraud allegations"),
            _q("S7", "recalls", "Product recalls"),
            _q("S7", "worker_safety", "Worker safety incidents"),
            _q("S7", "osha", "OSHA violations (if available)"),
            _q("S7", "data_privacy", "Data privacy incidents"),
            _q("S7", "complaints", "Consumer complaints"),
            _q("S7", "supply_chain", "Supply-chain concerns"),
            _q("S7", "whistleblower", "Whistleblower cases"),
            _q("S7", "governance", "Corporate governance concerns"),
        ),
    ),
    Section(
        id="S8",
        title="Leadership Intelligence",
        questions=(
            _q("S8", "ceo", "CEO"),
            _q("S8", "ceo_bio", "CEO biography"),
            _q("S8", "ceo_prev", "Previous companies"),
            _q("S8", "ceo_education", "Education"),
            _q("S8", "ceo_tenure", "Years with company"),
            _q("S8", "ceo_linkedin", "LinkedIn profile"),
            _q("S8", "board", "Board members"),
            _q("S8", "exec_team", "Executive team"),
            _q("S8", "stability", "Leadership stability"),
        ),
    ),
    Section(
        id="S9",
        title="Business Intelligence",
        questions=(
            _q("S9", "revenue_band", "Revenue band"),
            _q("S9", "employee_band", "Employee band"),
            _q("S9", "customer_industries", "Customer industries"),
            _q("S9", "business_model", "Business model"),
            _q("S9", "recurring", "Recurring revenue"),
            _q("S9", "advantages", "Competitive advantages"),
            _q("S9", "disadvantages", "Competitive disadvantages"),
            _q("S9", "competitors", "Major competitors"),
            _q("S9", "acquisition_history", "Acquisition history"),
            _q("S9", "growth", "Growth opportunities"),
        ),
    ),
)


def all_questions() -> list[Question]:
    return [q for section in SECTIONS for q in section.questions]


def question_count() -> int:
    return sum(len(s.questions) for s in SECTIONS)
