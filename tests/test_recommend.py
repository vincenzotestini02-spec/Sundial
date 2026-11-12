from dataclasses import replace

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


def _parts(ex, m, r):
    npv_m = npv(None, ex.scenarios, m, ex.horizon)
    winner = next(o for o in ex.offers if o.name == r.offer)
    best = max_cvar(npv_net_of_credit(winner, ex.scenarios, m, ex.horizon)[:, None], npv_m, m.cvar_alpha)
    return npv_m, best


def test_default_floor_is_share_of_mean_merchant_npv_when_achievable():
    ex = load_example("SUD")
    m = replace(ex.market, cvar_floor_share_of_mean=0.0)  # target 0: always achievable
    r = recommend(ex.offers, ex.scenarios, m, ex.horizon)
    npv_m, best = _parts(ex, m, r)
    assert not r.floor_capped and r.cvar_floor == pytest.approx(0.0)
    m = replace(ex.market, cvar_floor_share_of_mean=0.85)
    r = recommend(ex.offers, ex.scenarios, m, ex.horizon)
    npv_m, best = _parts(ex, m, r)
    target = 0.85 * npv_m.mean()
    if target <= best:
        assert not r.floor_capped and r.cvar_floor == pytest.approx(target)
    else:
        assert r.floor_capped and r.cvar_floor == pytest.approx(best)


def test_floor_capped_at_best_achievable_cvar():
    ex = load_example("SUD")
    m = replace(ex.market, cvar_floor_share_of_mean=50.0)  # absurd target
    r = recommend(ex.offers, ex.scenarios, m, ex.horizon)
    _, best = _parts(ex, m, r)
    assert r.floor_capped and r.cvar_floor == pytest.approx(best)


def test_merchant_cvar_above_floor_gives_zero_share():
    ex = load_example("SUD")
    m = replace(ex.market, cvar_floor_share_of_mean=-5.0)  # floor far below merchant CVaR
    r = recommend(ex.offers, ex.scenarios, m, ex.horizon)
    assert not r.floor_capped and r.share == pytest.approx(0.0, abs=1e-9)


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
    # abs 1e-4: at the cap the recommendation solves 1e-6 (relative) inside the boundary
    assert r.share == pytest.approx(float(single.shares[0]), abs=1e-4)


def test_infeasible_single_offer_lp_raises_clear_error(monkeypatch):
    """If the hedge LP is infeasible the recommendation must fail loudly, not report share 0."""
    from ppa_italia import recommend as rec_mod
    from ppa_italia.hedge import HedgeResult

    ex = load_example("SUD")
    bad = HedgeResult(__import__("numpy").zeros(1), float("nan"), float("nan"), "infeasible")
    monkeypatch.setattr(rec_mod, "optimise_allocation", lambda *a, **k: bad)
    with pytest.raises(RuntimeError, match="infeasible"):
        recommend(ex.offers, ex.scenarios, ex.market, ex.horizon)


def test_capped_floor_solves_just_inside_the_boundary(monkeypatch):
    """At the CVaR cap the LP is given a floor a hair below the best CVaR, so it stays feasible."""
    from ppa_italia import recommend as rec_mod

    ex = load_example("SUD")
    m = replace(ex.market, cvar_floor_share_of_mean=50.0)  # absurd target: capped
    seen = []
    real = rec_mod.optimise_allocation
    monkeypatch.setattr(rec_mod, "optimise_allocation",
                        lambda o, mm, floor, a=0.1: (seen.append(floor), real(o, mm, floor, a))[1])
    r = recommend(ex.offers, ex.scenarios, m, ex.horizon)
    assert r.floor_capped and seen[0] < r.cvar_floor
    assert seen[0] == pytest.approx(r.cvar_floor, rel=1e-5)
