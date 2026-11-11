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


def _fractional_tail_case():
    m = np.random.default_rng(0).normal(100, 30, 95)    # alpha*n = 9.5, fractional
    return m, cvar(m, 0.10)


def test_all_merchant_feasible_at_own_cvar_when_tail_fractional():
    m, floor = _fractional_tail_case()
    worse = (m - 10.0)[:, None]                          # worse than merchant everywhere
    r = optimise_allocation(worse, m, floor, alpha=0.10)
    assert r.status == "optimal" and r.shares[0] == pytest.approx(0.0, abs=1e-6)


def test_flat_ppa_not_used_at_merchant_cvar_when_tail_fractional():
    m, floor = _fractional_tail_case()
    flat = np.full((95, 1), m.mean() - 5.0)              # mean below merchant
    r = optimise_allocation(flat, m, floor, alpha=0.10)
    assert r.status == "optimal" and r.shares[0] == pytest.approx(0.0, abs=1e-6)
