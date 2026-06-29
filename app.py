"""
Company Intelligence Report Generator — application entry point.

This file is intentionally thin: it just wires the user interface to the
pipeline and the database. All the real work lives in the modules.

Run it with:  streamlit run app.py
"""
import streamlit as st

from config.settings import KNOWLEDGE_FALLBACK, LLM, SEARCH
from core.pipeline import generate_report
from storage import database as db
from ui import report_view, sidebar, styles

st.set_page_config(
    page_title="Company Intelligence Report Generator",
    page_icon="🔎",
    layout="wide",
)
styles.inject()
db.init_db()

# Remember the report currently on screen between interactions.
if "report" not in st.session_state:
    st.session_state.report = None

page = sidebar.render()

# --------------------------------------------------------------------------- #
# New Report
# --------------------------------------------------------------------------- #
if page == "New Report":
    st.title("Company Intelligence Report Generator")
    st.write(
        "Enter a company website. The tool reads the site, researches public "
        "sources, and answers a fixed due-diligence questionnaire."
    )

    if not LLM.is_configured:
        st.warning("No LLM key is set — answers will be 'Unknown'. Add a key in .env.")
    if not SEARCH.is_configured:
        st.info("No web-search key set — research is limited to the company website.")
    if KNOWLEDGE_FALLBACK.enabled and KNOWLEDGE_FALLBACK.is_configured:
        st.info(
            "Claude fallback is ON — any question still Unknown after research "
            "will be filled in from the AI's general knowledge, clearly marked "
            "'AI Knowledge (Unverified)' with low confidence and no real source."
        )

    website = st.text_input("Company Website", placeholder="https://company.com")

    if st.button("Generate Report"):
        if not website.strip():
            st.error("Please enter a website.")
        else:
            bar = st.progress(0.0, text="Starting...")
            report = generate_report(
                website,
                lambda msg, frac: bar.progress(min(frac, 1.0), text=msg),
            )
            bar.progress(1.0, text="Finished.")
            report.id = db.save_report(report)
            st.session_state.report = report
            st.success("Report ready.")

    if st.session_state.report:
        st.divider()
        report_view.render(st.session_state.report)

# --------------------------------------------------------------------------- #
# Previous Reports
# --------------------------------------------------------------------------- #
elif page == "Previous Reports":
    st.title("Previous Reports")
    rows = db.list_reports()
    if not rows:
        st.info("No reports yet. Create one from 'New Report'.")
    for row in rows:
        label = (f"{row['company_name']} — {row['created_at'][:10]} "
                 f"({row['avg_confidence']}% avg)")
        if st.button(label, key=f"open_{row['id']}"):
            st.session_state.report = db.get_report(row["id"])

    if st.session_state.report:
        st.divider()
        report_view.render(st.session_state.report)

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
elif page == "Settings":
    st.title("Settings")
    st.write("Settings live in the `.env` file. Current status:")
    st.code(
        f"LLM provider:           {LLM.provider}\n"
        f"LLM configured:         {LLM.is_configured}\n"
        f"Search provider:       {SEARCH.provider}\n"
        f"Search configured:     {SEARCH.is_configured}\n"
        f"Claude fallback on:     {KNOWLEDGE_FALLBACK.enabled}\n"
        f"Claude fallback ready:  {KNOWLEDGE_FALLBACK.is_configured}"
    )
    st.caption("Edit .env and restart the app to change these.")