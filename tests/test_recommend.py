import pytest

from ppa_italia.credit import npv_net_of_credit
from ppa_italia.example import load_example
from ppa_italia.hedge import cvar, max_cvar
from ppa_italia.recommend import recommend
from ppa_italia.structures import npv


def test_recommend_on_example_is_consistent():
    ex = load_example("SUD")
    r = recommend(ex.offers, ex.scenarios, ex.market, ex.horizon)
    assert r.offer in {"A", "B", "C"}
    assert 0.0 <= r.share <= 1.0 and 0.0 <= r.win_share <= 1.0
    assert r.fragile == (r.win_share < 0.70)
    assert r.fair_low <= r.fair_mid
    assert abs(sum(r.multi_offer_shares.values())) <= 1.0 + 1e-9


def test_default_floor_halves_gap_and_gives_positive_share():
    ex = load_example("SUD")
    r = recommend(ex.offers, ex.scenarios, ex.market, ex.horizon)
    m, sc = ex.market, ex.scenarios
    npv_m = npv(None, sc, m, ex.horizon)
    winner = next(o for o in ex.offers if o.name == r.offer)
    # Hedge objective is NPV net of expected credit loss (spec 5.5 step 3).
    best = max_cvar(npv_net_of_credit(winner, sc, m, ex.horizon)[:, None], npv_m, m.cvar_alpha)
    merchant = cvar(npv_m, m.cvar_alpha)
    if best > merchant:
        assert 0.0 < r.share <= 1.0
    assert r.cvar_floor == pytest.approx(merchant + 0.5 * (best - merchant))


def test_explicit_merchant_cvar_floor_still_works():
    ex = load_example("SUD")
    floor = cvar(npv(None, ex.scenarios, ex.market, ex.horizon), ex.market.cvar_alpha)
    r = recommend(ex.offers, ex.scenarios, ex.market, ex.horizon, cvar_floor=floor)
    assert 0.0 <= r.share <= 1.0
    assert r.cvar_floor == pytest.approx(floor)


def test_recommend_share_uses_npv_net_of_credit():
    from ppa_italia.hedge import optimise_allocation
    ex = load_example("SUD")
    m, sc, h = ex.market, ex.scenarios, ex.horizon
    r = recommend(ex.offers, sc, m, h)
    winner = next(o for o in ex.offers if o.name == r.offer)
    single = optimise_allocation(npv_net_of_credit(winner, sc, m, h)[:, None], npv(None, sc, m, h),
                                 r.cvar_floor, m.cvar_alpha)
    assert r.share == pytest.approx(float(single.shares[0]), abs=1e-6)
