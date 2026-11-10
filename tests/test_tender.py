import pandas as pd
import pytest

from ppa_italia.tender import rank_stability, score


OFFERS = pd.DataFrame(
    {"price": [72.0, 68.0, 70.0], "tenor": [10, 12, 7], "credit": [3, 5, 4]},
    index=["A", "B", "C"],
)
HIB = {"price": True, "tenor": True, "credit": True}


def test_score_and_stability():
    w = {"price": 0.6, "tenor": 0.2, "credit": 0.2}
    assert score(OFFERS, w, HIB).index[0] == "A"
    stab = rank_stability(OFFERS, w, HIB, n=2000)
    assert stab.sum() == pytest.approx(1.0)
    assert stab.index[0] == "A"


def test_dominant_offer_is_always_stable():
    df = pd.DataFrame({"price": [80.0, 60.0], "tenor": [12, 8]}, index=["best", "worse"])
    stab = rank_stability(df, {"price": 1, "tenor": 1}, {"price": True, "tenor": True}, n=500)
    assert stab["best"] == 1.0
