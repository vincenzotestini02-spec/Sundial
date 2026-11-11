import numpy as np
import pytest

from ppa_italia.hedge import cvar, frontier, merchant_breakeven_price, optimise_allocation
from tests.helpers import M0, _flat_sc, _offer

M = np.array([100.0, 50.0, 0.0, 150.0])        # merchant: high mean, bad tail
O = np.array([[70.0], [70.0], [70.0], [70.0]])  # PPA: flat, mean below merchant's 75


def test_no_floor_goes_all_merchant_when_merchant_mean_higher():
    r = optimise_allocation(O, M, cvar_floor=-1e9, alpha=0.25)
    assert r.status == "optimal" and r.shares[0] == pytest.approx(0.0, abs=1e-6)


def test_high_floor_forces_full_hedge():
    r = optimise_allocation(O, M, cvar_floor=70.0, alpha=0.25)
    assert r.shares[0] == pytest.approx(1.0, abs=1e-6) and r.cvar == pytest.approx(70.0)


def test_impossible_floor_is_infeasible():
    assert optimise_allocation(O, M, cvar_floor=1e6, alpha=0.25).status == "infeasible"


def test_cvar_helper():
    assert cvar(np.array([0.0, 10, 20, 30]), alpha=0.5) == pytest.approx(5.0)


def test_breakeven_equals_flat_spot():
    sc = _flat_sc(50.0)
    assert merchant_breakeven_price(_offer(), sc, M0, horizon=10) == pytest.approx(50.0, rel=1e-6)


def test_frontier_is_monotone():
    f = frontier(O, M, n_points=5, alpha=0.25)
    assert f["expected"].is_monotonic_decreasing
