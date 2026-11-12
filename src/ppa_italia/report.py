"""Two-page customer report PDF (Italian or English), built with fpdf2."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import pandas as pd
from fpdf import FPDF

from ppa_italia.recommend import Recommendation
from ppa_italia.report_text import TEXT
from ppa_italia.structures import Offer

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
MERCHANT_THRESHOLD = 0.01  # below this share the advice is to stay merchant
INVESTMENT_GRADE = ("AAA", "AA", "A", "BBB")


def _fmt(x: float, na: str, nd: int = 1, lang: str = "en") -> str:
    """Format a number with nd decimals (comma for Italian, dot for English), or `na` if NaN."""
    if x is None or math.isnan(x):
        return na
    s = f"{x:.{nd}f}"
    return s.replace(".", ",") if lang == "it" else s


def _vowel_sound(number: str) -> bool:
    """True when an Italian number word starts with a vowel: 1 (uno), 11 (undici), 8.. (otto/ottanta)."""
    digits = number.split(",")[0].split(".")[0]
    return digits in ("1", "11") or digits.startswith("8")


def _articles(lang: str, share_pct: str, win_pct: str, capture_rate: str, index_pct: str) -> dict[str, str]:
    """Italian article fields with elision before a vowel ('il 70%' but 'l'80%'); empty for English."""
    if lang != "it":
        return {"il_share": "", "nel_win": "", "al_capture": "", "al_index": ""}
    return {
        "il_share": "l'" if _vowel_sound(share_pct) else "il ",
        "nel_win": "nell'" if _vowel_sound(win_pct) else "nel ",
        "al_capture": "all'" if _vowel_sound(capture_rate) else "al ",
        "al_index": "all'" if _vowel_sound(index_pct) else "al ",
    }


def _risk_and_red_team(t: dict[str, str], rec: Recommendation, offer: Offer | None,
                       fields: dict[str, str]) -> tuple[str, str]:
    """Structure-aware risk text and a red-team paragraph built from the offer's data."""
    risk = t["risks"]
    red = t["red_team_fragile" if rec.fragile else "red_team_robust"]
    if offer is not None:
        risk += t[f"risk_{offer.structure}"]
        if not math.isnan(rec.breakeven):
            kind = "floor" if offer.structure == "floor" else "fixed"
            side = "below" if offer.price < rec.breakeven else "above"
            red += t[f"red_{kind}_{side}"]
        red += t["red_rating_ig" if offer.rating in INVESTMENT_GRADE else "red_rating_sub_ig"]
        red += t["red_tenor_indexed" if offer.indexation_pct > 0 else "red_tenor_flat"]
    if rec.disagrees:
        red += t["red_team_disagrees"]
    return risk.format(**fields), red.format(**fields)


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
    offer: Offer | None = None,
    avg_mw: float | None = None,
) -> bytes:
    """Build the customer PDF (at most 2 pages) and return its bytes.

    `offer` is the recommended Offer; when given, the risk section and the red team
    depend on its structure, price, rating, tenor and indexation. For a baseload
    offer, `avg_mw` (average plant output) lets the text state the block as a share of output.
    """
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

    cr = summary["capture_rate"].dropna()
    latest = float(cr.iloc[-1]) * 100 if len(cr) else float("nan")
    fields = {
        "zone": zone,
        "offer": rec.offer,
        "share_pct": f"{rec.share * 100:.0f}",
        "win_pct": f"{rec.win_share * 100:.0f}",
        "capture_rate": _fmt(latest, na, 0, lang),
        "fair_low": _fmt(rec.fair_low, na, 1, lang),
        "fair_mid": _fmt(rec.fair_mid, na, 1, lang),
        "breakeven": _fmt(rec.breakeven, na, 1, lang),
        "floor_label": t["floor_label"] if offer is not None and offer.structure == "floor" else "",
        "price": _fmt(offer.price, na, 1, lang) if offer is not None else na,
        "rating": offer.rating if offer is not None else na,
        "tenor": str(offer.tenor_years) if offer is not None else na,
        "index_pct": _fmt(offer.indexation_pct * 100, na, 1, lang) if offer is not None else na,
    }
    fields.update(_articles(lang, fields["share_pct"], fields["win_pct"],
                            fields["capture_rate"], fields["index_pct"]))
    is_block = offer is not None and offer.structure == "baseload" and offer.baseload_mw > 0 and bool(avg_mw)
    if is_block:
        fields["block_mw"] = _fmt(offer.baseload_mw, na, 1, lang)
        fields["block_pct"] = f"{offer.baseload_mw / avg_mw * 100:.0f}"
        fields["volume"] = t["volume_full" if rec.share >= 0.995 else "volume_part"].format(**fields)

    # 1. Situation: capture-rate trend
    _heading_body(pdf, t["situation"].format(**fields))
    _table(pdf, (t["capture_trend"], "%"),
           [(str(y), _fmt(float(v) * 100, na, 1, lang)) for y, v in cr.items()])

    # 2. Options: the multi-offer mix from the LP, then the winner's single-offer share
    _heading_body(pdf, t["options"].format(**fields))
    _table(pdf, (t["col_offer"], t["col_share"]),
           [(name, f"{s * 100:.0f}%") for name, s in rec.multi_offer_shares.items()])
    single_key = "options_single_block" if is_block and rec.share >= MERCHANT_THRESHOLD else "options_single"
    pdf.multi_cell(0, 5.5, t[single_key].format(**fields), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 3. Recommendation headline + merchant break-even (distinct from the fair range)
    key = "recommendation_merchant" if rec.share < MERCHANT_THRESHOLD else (
        "recommendation_block" if is_block else "recommendation")
    _heading_body(pdf, t[key].format(**fields))
    pdf.multi_cell(0, 5.5, t["breakeven"].format(**fields), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 4. Risks (structure-aware) and the red-team paragraph built from the offer's data
    risk, red = _risk_and_red_team(t, rec, offer, fields)
    _heading_body(pdf, risk)
    pdf.multi_cell(0, 5.5, red, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 5. Disclaimer
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 4.5, t["disclaimer"], new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
