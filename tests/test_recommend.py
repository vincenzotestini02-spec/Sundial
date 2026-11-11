from ppa_italia.example import load_example
from ppa_italia.recommend import recommend


def test_recommend_on_example_is_consistent():
    ex = load_example("SUD")
    r = recommend(ex.offers, ex.scenarios, ex.market, ex.horizon)
    assert r.offer in {"A", "B", "C"}
    assert 0.0 <= r.share <= 1.0 and 0.0 <= r.win_share <= 1.0
    assert r.fragile == (r.win_share < 0.70)
    assert r.fair_low <= r.fair_mid
    assert abs(sum(r.multi_offer_shares.values())) <= 1.0 + 1e-9
