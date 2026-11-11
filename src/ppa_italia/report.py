"""Two-page customer report PDF (Italian or English), built with fpdf2."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import pandas as pd
from fpdf import FPDF

from ppa_italia.recommend import Recommendation
from ppa_italia.report_text import TEXT

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
MERCHANT_THRESHOLD = 0.01  # below this share the advice is to stay merchant


def _fmt(x: float, na: str, nd: int = 1, lang: str = "en") -> str:
    """Format a number with nd decimals (comma for Italian, dot for English), or `na` if NaN."""
    if x is None or math.isnan(x):
        return na
    s = f"{x:.{nd}f}"
    return s.replace(".", ",") if lang == "it" else s


def _heading_body(pdf: FPDF, block: str) -> None:
    """Render 'Heading\\nbody': a bold heading line, then wrapped body text."""
    head, _, body = block.partition("\n")
    pdf.set_font("DejaVu", "B", 12)
    pdf.multi_cell(0, 7, head, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    if body:
        pdf.multi_cell(0, 5.5, body, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _table(pdf: FPDF, header: tuple[str, str], rows: list[tuple[str, str]]) -> None:
    """Draw a simple two-column table."""
    pdf.set_font("DejaVu", "B", 10)
    for cell in header:
        pdf.cell(60, 6, cell, border=1)
    pdf.ln()
    pdf.set_font("DejaVu", "", 10)
    for a, b in rows:
        pdf.cell(60, 6, a, border=1)
        pdf.cell(60, 6, b, border=1)
        pdf.ln()
    pdf.ln(2)


def build_report(
    rec: Recommendation,
    summary: pd.DataFrame,
    zone: str,
    lang: Literal["it", "en"],
    is_synthetic: bool,
) -> bytes:
    """Build the customer PDF (at most 2 pages) and return its bytes."""
    t = TEXT[lang]
    na = t["na"]
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 16)
    pdf.multi_cell(0, 9, t["title"].format(zone=zone), new_x="LMARGIN", new_y="NEXT")
    if is_synthetic:
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(180, 0, 0)
        pdf.multi_cell(0, 6, t["synthetic_banner"], new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # 1. Situation: capture-rate trend
    cr = summary["capture_rate"].dropna()
    latest = float(cr.iloc[-1]) * 100 if len(cr) else float("nan")
    _heading_body(pdf, t["situation"].format(zone=zone, capture_rate=_fmt(latest, na, 0, lang)))
    _table(pdf, (t["capture_trend"], "%"),
           [(str(y), _fmt(float(v) * 100, na, 1, lang)) for y, v in cr.items()])

    # 2. Options: LP shares per offer, plus the recommended offer
    shares = dict(rec.multi_offer_shares)
    shares.setdefault(rec.offer, rec.share)
    _heading_body(pdf, t["options"].format(offer=rec.offer))
    _table(pdf, (t["col_offer"], t["col_share"]),
           [(name, f"{s * 100:.0f}%") for name, s in shares.items()])

    # 3. Recommendation headline + merchant break-even (distinct from the fair range)
    key = "recommendation_merchant" if rec.share < MERCHANT_THRESHOLD else "recommendation"
    _heading_body(pdf, t[key].format(
        offer=rec.offer, share_pct=f"{rec.share * 100:.0f}",
        fair_low=_fmt(rec.fair_low, na, 1, lang), fair_mid=_fmt(rec.fair_mid, na, 1, lang)))
    pdf.multi_cell(0, 5.5, t["breakeven"].format(
        offer=rec.offer, breakeven=_fmt(rec.breakeven, na, 1, lang)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 4. Risks, including the red-team paragraph
    red = t["red_team_fragile" if rec.fragile else "red_team_robust"].format(
        win_pct=f"{rec.win_share * 100:.0f}")
    if rec.disagrees:
        red += t["red_team_disagrees"]
    _heading_body(pdf, t["risks"])
    pdf.multi_cell(0, 5.5, red, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 5. Disclaimer
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 4.5, t["disclaimer"], new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
