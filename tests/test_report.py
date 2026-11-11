"""Customer report PDF: language, page budget, disclaimers, headline variants."""
import io

import pandas as pd
import pytest
from pypdf import PdfReader

from ppa_italia.recommend import Recommendation
from ppa_italia.report import build_report
from ppa_italia.report_text import TEXT


def _text(pdf: bytes) -> tuple[int, str]:
    reader = PdfReader(io.BytesIO(pdf))
    return len(reader.pages), " ".join(p.extract_text() for p in reader.pages)


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
