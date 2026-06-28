"""
Report view.

Renders a finished Report on screen: one collapsible section per part of the
questionnaire, and inside each, every question with its answer, status,
confidence and clickable sources. Also offers a PDF download.
"""
import streamlit as st

from config.settings import PDF_OUTPUT_DIR
from core.models import AnswerStatus, Report
from export.pdf_report import build_pdf
from storage import database as db

_STATUS_COLOR = {
    AnswerStatus.VERIFIED: "#1a7f37",
    AnswerStatus.ESTIMATED: "#9a6700",
    AnswerStatus.NEEDS_REVIEW: "#9a6700",
    AnswerStatus.UNKNOWN: "#6e7781",
}


def render(report: Report) -> None:
    st.header(report.company_name)
    st.caption(
        f"{report.website}  •  generated {report.created_at[:10]}  "
        f"•  average confidence {report.average_confidence}%"
    )

    _export(report)

    for title, results in report.results_by_section().items():
        with st.expander(title, expanded=False):
            for r in results:
                _question(r)


def _question(r) -> None:
    st.markdown(f"**{r.question_text}**")
    st.write(r.answer)
    color = _STATUS_COLOR.get(r.status, "#6e7781")
    st.markdown(
        f"<span style='color:{color};font-weight:600'>{r.status.value}</span>"
        f" &nbsp;·&nbsp; Confidence: {r.confidence}%",
        unsafe_allow_html=True,
    )
    if r.sources:
        st.caption("Sources: " + " · ".join(f"[{s.title}]({s.url})" for s in r.sources))
    if r.reasoning:
        st.caption(f"_{r.reasoning}_")
    st.divider()


def _export(report: Report) -> None:
    if st.button("Build PDF"):
        safe = "".join(c for c in report.company_name if c.isalnum() or c in " _-").strip()
        path = str(PDF_OUTPUT_DIR / f"{safe or 'report'}_{report.id or 'new'}.pdf")
        build_pdf(report, path)
        report.pdf_path = path
        if report.id:
            db.save_report(report)
        with open(path, "rb") as f:
            st.download_button(
                "Download PDF", f, file_name=path.split("/")[-1],
                mime="application/pdf",
            )
