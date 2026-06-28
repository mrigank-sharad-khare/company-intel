"""
PDF export.

Produces an analyst "working paper": the left ~68% of every page holds the
questions, answers, confidence and sources; the right ~30% is left blank with
a vertical separator and an "Analyst Notes" heading, so an analyst can write
by hand during a meeting. It looks like an investment-firm working document,
not a marketing brochure.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, PageTemplate, Paragraph, Spacer,
)

from core.models import AnswerStatus, Report

PAGE_W, PAGE_H = letter
MARGIN = 0.6 * inch
SEP_X = PAGE_W * 0.68            # x position of the notes separator line
BLUE = colors.HexColor("#1a4f8b")

_STATUS_COLOR = {
    AnswerStatus.VERIFIED: colors.HexColor("#1a7f37"),
    AnswerStatus.ESTIMATED: colors.HexColor("#9a6700"),
    AnswerStatus.NEEDS_REVIEW: colors.HexColor("#9a6700"),
    AnswerStatus.AI_KNOWLEDGE: colors.HexColor("#c0392b"),
    AnswerStatus.UNKNOWN: colors.HexColor("#6e7781"),
}

# ---- paragraph styles ----------------------------------------------------- #
_SECTION = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=12,
                          textColor=BLUE, spaceBefore=10, spaceAfter=4)
_QUESTION = ParagraphStyle("question", fontName="Helvetica-Bold", fontSize=9.5,
                           textColor=colors.HexColor("#222222"), spaceBefore=6)
_ANSWER = ParagraphStyle("answer", fontName="Helvetica", fontSize=9.5,
                         leading=13, spaceAfter=2)
_META = ParagraphStyle("meta", fontName="Helvetica", fontSize=8,
                       textColor=colors.grey, spaceAfter=1)


def build_pdf(report: Report, output_path: str) -> str:
    doc = BaseDocTemplate(
        output_path, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 24, bottomMargin=MARGIN,
    )
    doc.company_name = report.company_name

    content_frame = Frame(
        MARGIN, MARGIN,
        SEP_X - MARGIN - 10,                 # width stops before the notes column
        PAGE_H - 2 * MARGIN - 28,
        id="content",
    )
    doc.addPageTemplates([
        PageTemplate(id="main", frames=[content_frame], onPage=_decorate)
    ])
    doc.build(_build_story(report))
    return output_path


# --------------------------------------------------------------------------- #
# Page furniture (header, footer, notes column) drawn on every page
# --------------------------------------------------------------------------- #
def _decorate(canvas, doc):
    canvas.saveState()

    # Header line + titles
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, PAGE_H - MARGIN + 4, doc.company_name)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 4,
                           "CONFIDENTIAL — ANALYST WORKING PAPER")
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(1)
    canvas.line(MARGIN, PAGE_H - MARGIN, PAGE_W - MARGIN, PAGE_H - MARGIN)

    # Vertical separator + "Analyst Notes" heading (right column stays blank)
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.setLineWidth(0.8)
    canvas.line(SEP_X, MARGIN, SEP_X, PAGE_H - MARGIN - 4)
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(SEP_X + 10, PAGE_H - MARGIN - 16, "Analyst Notes")

    # Footer page number
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(PAGE_W - MARGIN, MARGIN - 14, f"Page {doc.page}")

    canvas.restoreState()


# --------------------------------------------------------------------------- #
# Content (left column)
# --------------------------------------------------------------------------- #
def _build_story(report: Report):
    story = [
        Paragraph("Company Intelligence Report", _SECTION),
        Paragraph(f"{report.website} &nbsp;•&nbsp; generated {report.created_at[:10]}"
                  f" &nbsp;•&nbsp; average confidence {report.average_confidence}%",
                  _META),
        Spacer(1, 6),
    ]

    for title, results in report.results_by_section().items():
        story.append(Paragraph(title, _SECTION))
        for r in results:
            story.extend(_question_block(r))
    return story


def _question_block(r):
    color = _STATUS_COLOR.get(r.status, colors.grey)
    block = [
        Paragraph(_escape(r.question_text), _QUESTION),
        Paragraph(_escape(r.answer), _ANSWER),
        Paragraph(
            f'<font color="#{color.hexval()[2:]}"><b>{r.status.value}</b></font>'
            f' &nbsp; · &nbsp; Confidence: {r.confidence}%',
            _META,
        ),
    ]
    if r.sources:
        links = " &nbsp;·&nbsp; ".join(_source_label(s) for s in r.sources)
        block.append(Paragraph("Sources: " + links, _META))
    block.append(HRFlowable(width="100%", thickness=0.4,
                            color=colors.HexColor("#e5e5e5"),
                            spaceBefore=4, spaceAfter=2))
    return block


def _source_label(s) -> str:
    # The ChatGPT fallback has no real URL to link to — show plain text instead.
    if not s.url:
        return _escape(s.title)
    return f'<a href="{_escape(s.url)}" color="#1a4f8b">{_escape(s.title)}</a>'


def _escape(text: str) -> str:
    return (str(text).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))