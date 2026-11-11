"""Customer report PDF: language, page budget, disclaimers, headline variants."""
import io

import pandas as pd
import pytest
from pypdf import PdfReader

from ppa_italia.recommend import Recommendation
from ppa_italia.report import build_report
from ppa_italia.report_text import TEXT
from tests.helpers import _offer


def _text(pdf: bytes) -> tuple[int, str]:
    reader = PdfReader(io.BytesIO(pdf))
    text = " ".join(p.extract_text() for p in reader.pages)
    return len(reader.pages), " ".join(text.split())  # collapse wrapped lines


SUMMARY = pd.DataFrame({"capture_rate": [0.9, 0.8]}, index=[2024, 2025])


@pytest.mark.parametrize("lang,word", [("it", "Raccomandazione"), ("en", "Recommendation")])
def test_report_language_and_pages(lang, word):
    rec = Recommendation("A", 0.7, 55.0, 60.0, 52.0, 0.82, False, {"A": 0.7}, False, 0.0)
    pdf = build_report(rec, SUMMARY, "SUD", lang, is_synthetic=True)
    assert pdf[:4] == b"%PDF"
    pages, text = _text(pdf)
    assert pages <= 2 and word in text and "SYNTHETIC" in text.upper()


def test_text_keys_match_across_languages():
    assert TEXT["it"].keys() == TEXT["en"].keys()


def test_merchant_headline_and_nan_breakeven_and_fragile():
    rec = Recommendation("B", 0.0, 50.0, 58.0, float("nan"), 0.4, True,
                         {"A": 0.2, "B": 0.0}, True, -5.0)
    _, text = _text(build_report(rec, SUMMARY, "SUD", "en", is_synthetic=False))
    assert "Stay merchant for now; best offer if hedging: B." in text
    assert "n/a" in text and "SYNTHETIC" not in text.upper()
    assert "Not trading advice and not any company's pricing." in text


def test_sign_headline_italian_accents():
    rec = Recommendation("A", 0.7, 55.0, 60.0, 52.0, 0.82, False, {"A": 0.7}, False, 0.0)
    _, text = _text(build_report(rec, SUMMARY, "SUD", "it", is_synthetic=False))
    assert "Firmare l'offerta A per il 70% della produzione." in text
    assert "è" in text or "à" in text


def test_decimal_separator_follows_language():
    rec = Recommendation("A", 0.7, 55.5, 60.4, 52.0, 0.82, False, {"A": 0.7}, False, 0.0)
    _, it = _text(build_report(rec, SUMMARY, "SUD", "it", is_synthetic=False))
    _, en = _text(build_report(rec, SUMMARY, "SUD", "en", is_synthetic=False))
    assert "55,5" in it and "60,4" in it and "90,0" in it and "55.5" not in it
    assert "55.5" in en and "60.4" in en and "90.0" in en and "55,5" not in en


FLOOR = _offer(name="C", structure="floor", price=64.0, floor_premium=4.0, tenor_years=12,
               rating="BB", zero_volume_negative=True)
PAP = _offer(name="A", structure="pap", price=88.0, tenor_years=10, indexation_pct=0.02, rating="BBB")


def test_floor_report_is_structure_aware_en():
    rec = Recommendation("C", 0.4, 85.0, 87.0, 67.2, 0.82, False, {"C": 0.4}, False, 0.0)
    pages, text = _text(build_report(rec, SUMMARY, "SUD", "en", False, offer=FLOOR))
    assert pages <= 2
    assert "Fair pay-as-produced price range" in text
    assert "(floor level)" in text
    assert "keeps the upside" in text and "premium" in text
    assert "The floor at 64.0 EUR/MWh is below its own break-even of 67.2 EUR/MWh" in text
    assert "BB" in text and "below investment grade" in text
    assert "12 years" in text and "no indexation" in text


def test_floor_report_is_structure_aware_it():
    rec = Recommendation("C", 0.4, 85.0, 87.0, 67.2, 0.82, False, {"C": 0.4}, False, 0.0)
    pages, text = _text(build_report(rec, SUMMARY, "SUD", "it", False, offer=FLOOR))
    assert pages <= 2
    assert "Intervallo di prezzo equo pay-as-produced" in text
    assert "(livello del floor)" in text
    assert "Il floor a 64,0 EUR/MWh è sotto il proprio prezzo di pareggio di 67,2 EUR/MWh" in text
    assert "nell'82%" in text and "nel 82%" not in text
    assert "12 anni" in text


@pytest.mark.parametrize("lang,upside,beats", [
    ("en", "gives up the upside", "above the merchant break-even of 80.0 EUR/MWh"),
    ("it", "rinuncia al rialzo", "sopra il prezzo di pareggio merchant di 80,0 EUR/MWh"),
])
def test_pap_report_is_structure_aware(lang, upside, beats):
    rec = Recommendation("A", 0.6, 85.0, 87.0, 80.0, 0.75, False, {"A": 0.6}, False, 0.0)
    pages, text = _text(build_report(rec, SUMMARY, "SUD", lang, False, offer=PAP))
    assert pages <= 2 and upside in text and beats in text
    assert "(floor level)" not in text and "(livello del floor)" not in text


def test_options_table_is_multi_offer_mix_with_single_share_separate():
    rec = Recommendation("C", 0.44, 85.0, 87.0, 67.2, 0.82, False, {"A": 0.1, "C": 0.3}, True, 0.0)
    _, text = _text(build_report(rec, SUMMARY, "SUD", "en", False, offer=FLOOR))
    assert "multi-offer mix" in text
    assert "Recommended offer alone (C): 44% of production" in text
