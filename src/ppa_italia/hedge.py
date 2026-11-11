"""Hedge allocation: how much of a merchant plant to sell under each PPA offer.

The optimiser is a Rockafellar-Uryasev linear programme: maximise expected
revenue subject to a floor on the CVaR (mean of the worst alpha share of
scenarios). Also contains the merchant break-even price of an offer.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import brentq, linprog

from ppa_italia.scenarios import ScenarioSet
from ppa_italia.structures import Market, Offer, npv


@dataclass
class HedgeResult:
    """Optimal PPA shares (one per offer) with the resulting expected value and CVaR."""

    shares: np.ndarray
    expected: float
    cvar: float
    status: Literal["optimal", "infeasible"]


def cvar(values: np.ndarray, alpha: float = 0.10) -> float:
    """Lower-tail CVaR: mean of the worst ceil(alpha * n) values."""
    v = np.sort(np.asarray(values, dtype=float))
    k = max(1, math.ceil(alpha * len(v)))
    return float(v[:k].mean())


def _build_lp(npv_offers: np.ndarray, npv_merchant: np.ndarray, alpha: float):
    """Constraint matrices shared by both LPs.

    Variable layout (length k + 1 + n):
        z = [ x_0 .. x_{k-1} | eta | u_0 .. u_{n-1} ]
        x_j  share of the plant sold under offer j, in [0, 1]
        eta  value-at-risk level (free)
        u_s  shortfall of scenario s below eta, u_s >= 0

    Revenue in scenario s:  R_s = m_s + sum_j x_j * d_sj,  with d_sj = o_sj - m_s.

    Rows of A_ub z <= b_ub:
        row 0      sum_j x_j <= 1                      (shares cannot exceed the plant)
        rows 1..n  eta - R_s - u_s <= 0                (u_s >= eta - R_s), i.e.
                   -sum_j d_sj x_j + eta - u_s <= m_s
    The CVaR row  eta - (1/(alpha n)) sum_s u_s >= floor  is added by the caller
    because its right-hand side (the floor) differs between the two LPs.
    """
    n, k = npv_offers.shape
    d = npv_offers - npv_merchant[:, None]            # (n, k) gain of offer j over merchant in s

    a_ub = np.zeros((1 + n, k + 1 + n))
    b_ub = np.zeros(1 + n)
    a_ub[0, :k] = 1.0                                  # row 0: sum x <= 1
    b_ub[0] = 1.0
    a_ub[1:, :k] = -d                                  # rows 1..n: -d x + eta - u <= m
    a_ub[1:, k] = 1.0
    a_ub[1:, k + 1:] = -np.eye(n)
    b_ub[1:] = npv_merchant

    cvar_row = np.zeros(k + 1 + n)                     # (1/(alpha n)) sum u - eta  (<= -floor)
    cvar_row[k] = -1.0
    cvar_row[k + 1:] = 1.0 / (alpha * n)

    bounds = [(0.0, 1.0)] * k + [(None, None)] + [(0.0, None)] * n
    return a_ub, b_ub, cvar_row, bounds


def optimise_allocation(npv_offers: np.ndarray, npv_merchant: np.ndarray,
                        cvar_floor: float, alpha: float = 0.10) -> HedgeResult:
    """Maximise expected revenue subject to CVaR_alpha(R) >= cvar_floor.

    npv_offers has shape (n scenarios, k offers); npv_merchant has shape (n,).
    """
    npv_offers = np.asarray(npv_offers, dtype=float)
    npv_merchant = np.asarray(npv_merchant, dtype=float)
    n, k = npv_offers.shape
    a_ub, b_ub, cvar_row, bounds = _build_lp(npv_offers, npv_merchant, alpha)

    # CVaR floor row:  (1/(alpha n)) sum u - eta <= -cvar_floor
    a_ub = np.vstack([a_ub, cvar_row])
    b_ub = np.append(b_ub, -cvar_floor)

    # Objective: maximise mean R = mean(m) + sum_j x_j mean_s(d_sj); linprog minimises.
    c = np.zeros(k + 1 + n)
    c[:k] = -(npv_offers - npv_merchant[:, None]).mean(axis=0)

    res = linprog(c, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if res.status != 0:
        return HedgeResult(np.zeros(k), float("nan"), float("nan"), "infeasible")

    shares = np.clip(res.x[:k], 0.0, 1.0)
    revenue = npv_merchant + (npv_offers - npv_merchant[:, None]) @ shares
    return HedgeResult(shares, float(revenue.mean()), cvar(revenue, alpha), "optimal")


def _max_cvar(npv_offers: np.ndarray, npv_merchant: np.ndarray, alpha: float) -> float:
    """Highest CVaR any allocation can reach (maximise eta - (1/(alpha n)) sum u)."""
    n, k = npv_offers.shape
    a_ub, b_ub, cvar_row, bounds = _build_lp(npv_offers, npv_merchant, alpha)
    res = linprog(cvar_row, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs")  # min -CVaR
    return float(-res.fun)


def frontier(npv_offers: np.ndarray, npv_merchant: np.ndarray,
             n_points: int = 20, alpha: float = 0.10) -> pd.DataFrame:
    """Expected value versus CVaR floor, from all-merchant risk to the lowest-risk mix."""
    npv_offers = np.asarray(npv_offers, dtype=float)
    npv_merchant = np.asarray(npv_merchant, dtype=float)
    k = npv_offers.shape[1]
    floor_min = cvar(npv_merchant, alpha)
    floor_max = max(_max_cvar(npv_offers, npv_merchant, alpha), floor_min)

    rows = []
    for floor in np.linspace(floor_min, floor_max, n_points):
        r = optimise_allocation(npv_offers, npv_merchant, float(floor), alpha)
        if r.status != "optimal":
            continue                                   # e.g. top point lost to solver tolerance
        row = {"cvar_floor": float(floor),
               # Rounded so solver noise (~1e-9) cannot break monotonicity.
               "expected": round(r.expected, 6), "cvar": r.cvar}
        row.update({f"share_{j}": r.shares[j] for j in range(k)})
        rows.append(row)
    return pd.DataFrame(rows)


def merchant_breakeven_price(o: Offer, sc: ScenarioSet, m: Market, horizon: int) -> float:
    """Offer price at which mean NPV of the offer equals mean NPV of staying merchant."""
    merchant_mean = float(npv(None, sc, m, horizon).mean())

    def gap(price: float) -> float:
        return float(npv(dataclasses.replace(o, price=price), sc, m, horizon).mean()) - merchant_mean

    lo, hi = 1e-6, 1000.0                              # Offer requires price > 0
    if gap(lo) * gap(hi) > 0:
        raise ValueError("no break-even price in (0, 1000] €/MWh")
    return float(brentq(gap, lo, hi, xtol=1e-10))
