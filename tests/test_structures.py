import numpy as np
import pytest

from ppa_italia.example import load_example
from ppa_italia.structures import Market, merchant_revenue, npv, offer_revenue
from tests.helpers import M0, _flat_sc, _offer


def test_merchant_and_pap_on_flat_prices():
    sc = _flat_sc()
    assert merchant_revenue(sc, M0)[0] == pytest.approx(50.0 * 8760)
    assert offer_revenue(_offer(), sc, M0)[0] == pytest.approx(60.0 * 8760)


def test_imbalance_and_goo_terms():
    m = Market(imbalance_cost=3.0, goo_value=1.0, margin=0.0)
    o = _offer(imbalance_on_buyer=False, goo_included=False)
    assert offer_revenue(o, _flat_sc(), m)[0] == pytest.approx((60 - 3 + 1) * 8760)


def test_zero_volume_in_negative_hours():
    sc = _flat_sc(); sc.prices[0, :10] = -5.0
    assert offer_revenue(_offer(zero_volume_negative=True), sc, M0)[0] == pytest.approx(60.0 * 8750)


def test_baseload_shape_risk():
    sc = _flat_sc(gen=0.0)  # no production at all
    o = _offer(structure="baseload", baseload_mw=1.0)
    assert offer_revenue(o, sc, M0)[0] == pytest.approx(60 * 8760 - 50 * 8760)


def test_floor_pays_max_of_spot_and_floor():
    sc = _flat_sc(); sc.prices[0, :4380] = 20.0
    o = _offer(structure="floor", price=40.0, floor_premium=2.0)
    assert offer_revenue(o, sc, M0)[0] == pytest.approx(40 * 4380 + 50 * 4380 - 2 * 8760)


def test_indexation_and_npv():
    o = _offer(indexation_pct=0.02, tenor_years=2)
    sc = _flat_sc()
    assert offer_revenue(o, sc, M0, year=1)[0] == pytest.approx(60 * 1.02 * 8760)
    m = Market(imbalance_cost=0, goo_value=0, margin=0, discount_rate=0.0)
    # 2 years PPA then 1 year merchant
    assert npv(o, sc, m, horizon=3)[0] == pytest.approx((60 + 61.2 + 50) * 8760)


def test_merchant_escalation_and_none_offer():
    m = Market(imbalance_cost=0, goo_value=0, margin=0, discount_rate=0.0, merchant_escalation_pct=0.1)
    sc = _flat_sc()
    assert merchant_revenue(sc, m, year=1)[0] == pytest.approx(55.0 * 8760)
    assert npv(None, sc, m, horizon=2)[0] == pytest.approx((50 + 55) * 8760)


@pytest.mark.parametrize("kw", [dict(tenor_years=0), dict(price=-1.0), dict(rating="ZZ"),
                                dict(structure="swap"), dict(penalty_severity=6),
                                dict(structure="baseload", baseload_mw=0.0),
                                dict(floor_premium=-1.0)])
def test_offer_validation(kw):
    with pytest.raises(ValueError):
        _offer(**kw)


def test_load_example_is_anchored_and_consistent():
    ex = load_example("SUD")
    assert [o.name for o in ex.offers] == ["A", "B", "C"]
    assert ex.horizon == max(o.tenor_years for o in ex.offers)
    p50_capture = float(np.percentile(ex.scenarios.capture_prices(), 50))
    a = ex.offers[0]
    assert a.price == pytest.approx(0.97 * p50_capture)


def test_floor_zero_volume_in_negative_hours():
    # 10 hours at -5, 4370 hours at 20 (floor 40 binds), 4380 hours at 50 (spot binds).
    sc = _flat_sc(); sc.prices[0, :10] = -5.0; sc.prices[0, 10:4380] = 20.0
    on = _offer(structure="floor", price=40.0, floor_premium=2.0, zero_volume_negative=True)
    off = _offer(structure="floor", price=40.0, floor_premium=2.0, zero_volume_negative=False)
    # Clause on: no volume (no floor top-up, no spot, no premium) in the 10 hours at p <= 0.
    assert offer_revenue(on, sc, M0)[0] == pytest.approx(40 * 4370 + 50 * 4380 - 2 * 8750)
    # Clause off: the floor also pays in the negative hours.
    assert offer_revenue(off, sc, M0)[0] == pytest.approx(40 * 4380 + 50 * 4380 - 2 * 8760)
