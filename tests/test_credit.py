import pytest

from ppa_italia.credit import expected_credit_loss
from ppa_italia.structures import Market
from tests.helpers import _offer, _flat_sc, M0


def test_no_loss_when_ppa_is_below_market():
    # offer price < spot -> PPA has negative value to the seller -> no credit exposure
    assert expected_credit_loss(_offer(price=40.0), _flat_sc(50.0), M0) == 0.0


def test_loss_scales_with_rating():
    lo = expected_credit_loss(_offer(price=70.0, rating="A"), _flat_sc(50.0), M0)
    hi = expected_credit_loss(_offer(price=70.0, rating="BB"), _flat_sc(50.0), M0)
    assert 0 < lo < hi


def test_one_year_hand_computed():
    m = Market(imbalance_cost=0, goo_value=0, margin=0, discount_rate=0.0, lgd=0.5)
    el = expected_credit_loss(_offer(price=60.0, tenor_years=1, rating="B"), _flat_sc(50.0), m)
    assert el == pytest.approx(0.03 * 0.5 * (10 * 8760))


def test_two_year_discounting_matches_year_end_npv():
    # Revenue of year k is booked at the end of year k, so each year's gap is discounted
    # (1+r)^(k+1) in total, as in npv(). Default in year t loses years t..T-1.
    r, g = 0.10, 10 * 8760
    m = Market(imbalance_cost=0, goo_value=0, margin=0, discount_rate=r, lgd=0.5)
    el = expected_credit_loss(_offer(price=60.0, tenor_years=2, rating="B"), _flat_sc(50.0), m)
    pd_ = 0.03
    expected = 0.5 * (pd_ * (g / 1.1 + g / 1.1 ** 2) + (1 - pd_) * pd_ * (g / 1.1 ** 2))
    assert el == pytest.approx(expected)


def test_npv_net_of_credit_is_npv_minus_el():
    from ppa_italia.credit import npv_net_of_credit
    from ppa_italia.structures import npv
    sc, o = _flat_sc(50.0, n=3), _offer(price=70.0, rating="BB", tenor_years=3)
    net = npv_net_of_credit(o, sc, M0, horizon=5)
    assert net == pytest.approx(npv(o, sc, M0, 5) - expected_credit_loss(o, sc, M0))
    assert npv_net_of_credit(None, sc, M0, 5) == pytest.approx(npv(None, sc, M0, 5))
