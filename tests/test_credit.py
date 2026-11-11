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
