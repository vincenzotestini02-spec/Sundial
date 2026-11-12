import shutil

import pandas as pd
import pytest

from ppa_italia.data import store
from ppa_italia.example import load_example
from ppa_italia.imbalance import imbalance_cost
from ppa_italia.pricing import fair_floor_premium
from ppa_italia.scenarios import trailing_baseload
from ppa_italia.zones import ZONES
from tests.helpers import _flat_sc, _offer


def test_imbalance_cost_hand_computed():
    idx = pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC")
    prices = pd.Series([50, 50, 50, 50.0], idx)
    imb = pd.Series([60, 40, 50, 50.0], idx)
    shape = pd.Series([1, 1, 0, 0.0], idx)
    assert imbalance_cost(imb, prices, shape, error_share=0.1, months=1200) == pytest.approx(0.1 * 10)


def test_imbalance_cost_uses_only_last_complete_months():
    idx = pd.date_range("2024-01-01", "2024-03-15 23:00", freq="h", tz="UTC")
    prices = pd.Series(50.0, idx)
    imb = pd.Series(50.0, idx)
    imb[imb.index.month == 1] = 70.0  # January: deviation 20
    imb[imb.index.month == 2] = 60.0  # February: deviation 10
    imb[imb.index.month == 3] = 500.0  # partial March is ignored
    shape = pd.Series(1.0, idx)
    # months=1 -> February only (last complete month)
    assert imbalance_cost(imb, prices, shape, error_share=1.0, months=1) == pytest.approx(10.0)


def test_fair_floor_premium_zero_above_floor_and_hand_case():
    assert fair_floor_premium(_offer(structure="floor", price=40.0), _flat_sc(50.0)) == 0.0
    sc = _flat_sc(50.0)
    sc.prices[0, :4380] = 20.0
    assert fair_floor_premium(_offer(structure="floor", price=40.0, zero_volume_negative=False), sc) == pytest.approx(10.0)


def test_fair_floor_premium_respects_zero_volume_clause():
    sc = _flat_sc(50.0)
    sc.prices[0, :10] = -5.0
    o = _offer(structure="floor", price=40.0, zero_volume_negative=True)
    assert fair_floor_premium(o, sc) == 0.0


@pytest.mark.parametrize("zone", ZONES)
def test_load_example_is_coherent_for_every_zone(zone, monkeypatch):
    monkeypatch.delenv("SUNDIAL_FORCE_SYNTHETIC", raising=False)
    ex = load_example(zone)
    assert ex.zone == zone and not ex.is_synthetic
    assert ex.scenarios.reference_level == pytest.approx(trailing_baseload(store.load_prices(zone)[0]))
    c = [o for o in ex.offers if o.structure == "floor"][0]
    assert c.floor_premium == pytest.approx(1.2 * fair_floor_premium(c, ex.scenarios))
    assert ex.imbalance_source == "computed" and ex.market.imbalance_cost > 0
    assert ex.status.imbalance and ex.status.zone_solar and ex.fallback_years == []


def test_missing_imbalance_uses_labelled_placeholder(tmp_path, monkeypatch):
    monkeypatch.delenv("SUNDIAL_FORCE_SYNTHETIC", raising=False)
    for f in store.data_dir().iterdir():
        if f.is_file() and f.name != "imbalance_SUD.parquet":
            shutil.copy(f, tmp_path / f.name)
    monkeypatch.setenv("SUNDIAL_DATA_DIR", str(tmp_path))
    ex = load_example("SUD")
    assert ex.imbalance_source == "placeholder"
    assert ex.market.imbalance_cost == 3.0
    assert not ex.status.imbalance
