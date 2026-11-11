# Methodology

Indicative models on public data. Not trading advice; not any company's pricing. Every number in the app comes from a tested function in `src/ppa_italia/`. The current run uses a **synthetic placeholder price series** until the ENTSO-E token is available; all results below are labelled accordingly in the app.

## 1. Capture price and capture rate (`value.py`)

For hourly prices *p_h* (EUR/MWh) and generation *g_h* (MWh):

- Baseload price = mean(*p_h*)
- Capture price = sum(*p_h g_h*) / sum(*g_h*)
- Capture rate = capture price / baseload price
- Negative-price exposure = hours with *p_h* <= 0 (zero and negative), and the share of yearly generation produced in them.

**15-minute prices.** Since 1 Oct 2025 the day-ahead market clears in 15-minute steps. Prices are averaged to hourly (`data/entsoe.py: to_hourly`) to match hourly generation profiles. This smooths intra-hour price shape. *Limitation:* slightly understates intra-hour volatility; acceptable for indicative valuation.

**Short data gaps.** `scripts/build_prices.py` fills gaps of up to 6 consecutive missing hours by linear interpolation on a complete hourly UTC index (`fill_short_gaps`) and prints the hours filled per zone and year. Longer gaps stay missing, and incomplete years are not used as scenarios. *Limitation:* interpolation hides short real price spikes.

## 2. Solar profile (`data/pvgis.py`, `scripts/build_puglia_profile.py`)

- Site: Tavoliere plain near Foggia, 41.46 N 15.55 E (SUD zone). Fictional 20 MWp park.
- PVGIS v5.3, PVGIS-SARAH3 radiation, crystalline silicon, fixed mounting at PVGIS-optimal angles (36 degrees, azimuth -5), 14% system losses. Weather years 2005-2023 (19 years). PVGIS (c) European Union.
- Result (2026-11-10 run): P50 29,335 MWh/yr, P90 28,308 MWh/yr (P90 is the value exceeded in 90% of years), mean specific yield 1,468 kWh/kWp, inter-annual variability 3.0%.
- Check: specific yield inside the 1,400-1,600 kWh/kWp plausibility range for a fixed-tilt Puglia plant.
- *Limitations:* no curtailment, no degradation (about 0.4-0.5%/yr typical), no availability losses beyond the 14% lump. The true judge would be metered data.

## 3. Price scenarios: "historical shape, current level" (`scenarios.py`)

- Each complete historical price year (8,760 hours) keeps its hourly shape, which carries the cannibalisation signal.
- Each year is multiplied so its baseload mean equals a **reference level**. Default: the zone's trailing 12-month baseload mean (`trailing_baseload`). The level is a stated assumption, shown on screen and adjustable.
- The 2022 crisis therefore contributes its shape, not its level. Zero and negative hours stay at or below zero because the scaling is multiplicative.
- **Scenarios** are every pairing of a rescaled price year with a weather year (re-stamped by hour of year), for example 5 price years x 19 weather years.
- *Limitations:* pairing different years breaks the same-hour sun-price link and understates cannibalisation in sunny years. The shape of past years may not represent future shape as solar capacity grows. Using one flat level ignores any forward curve.
- **Typical weather year for price-year statistics** (`profile_on_years`): where a single production profile is needed per calendar price year (for example the yearly capture-rate chart on Home), the median-energy weather year is stamped onto each price year, with 29 Feb repeating 28 Feb. *Limitation:* this hides weather variability in those charts only; the scenario set itself uses all weather years.

## 4. PPA structures: revenue formulas (`structures.py`)

Hourly revenue to the seller, per contract year *t*, with spot *p_h* escalated by the merchant escalation, price *P* escalated by the offer's indexation, and generation *g_h*:

| Structure | Revenue |
|---|---|
| Pay-as-produced (`pap`) | P x sum(g_h); with the negative-price clause, hours with p_h <= 0 carry zero volume |
| Baseload (`baseload`) | P x B x 8,760 + sum(p_h (g_h - B)); B is the contracted baseload MW. The second term is the shape risk |
| Floor (`floor`) | sum(max(p_h, P) g_h) - premium x sum(g_h) |

Adjustments: if imbalance stays with the seller, the imbalance cost per MWh is deducted; if GoOs are not included in the offer, the GoO value per MWh is added. Merchant revenue is sum(p_h g_h) minus imbalance cost plus GoO value.

NPV over the horizon (the longest tenor) discounts year-end revenue at the stated rate; after an offer's tenor the plant earns merchant revenue. Offers with different tenors are therefore compared on the same horizon.

*Limitations:* the negative-price clause is applied to pay-as-produced offers only; the floor and baseload formulas do not use it. Escalation of the merchant level is a single stated assumption (default 0%/yr real). No degradation, curtailment or basis between the contract and the physical node.

## 5. Credit expected loss (`credit.py`)

Expected loss = PD(rating) x LGD x exposure, accumulated over the tenor. Exposure at year *t* is the mean over scenarios of the positive part of the present value of the remaining years' (offer - merchant) revenue, because the seller only loses if the contract is worth more than selling at spot. Loss in year *t* is weighted by the marginal default probability (1 - PD)^t PD, times LGD, discounted to today.

- PD by rating: a small table of long-run one-year default rates (AAA 0%, AA 0.02%, A 0.05%, BBB 0.15%, BB 0.60%, B 3.00%), attributed in the code to the S&P annual default study. **The exact edition and values are not yet verified against the source** and must be checked by the author.
- LGD 60%: stated assumption (unsecured corporate).
- *Limitations:* constant PD per rating, no rating migration, no collateral modelled, no correlation between buyer default and price level.

## 6. Tender MCDA and Dirichlet robustness (`tender.py`)

- Criteria: mean NPV, P10 NPV, expected credit loss, tenor, indexation, imbalance on buyer, penalty severity. Min-max normalisation (direction-aware), weighted sum with default weights 0.30, 0.20, 0.15, 0.10, 0.05, 0.10, 0.10.
- **Robustness:** 5,000 weight vectors drawn from a Dirichlet distribution centred on the chosen weights (concentration 20). The robustness figure is each offer's share of first places. Below 70% the recommendation is labelled **fragile**.
- *Limitations:* the weights are the author's judgment, not elicited from a customer. Min-max normalisation makes scores depend on which offers are in the table. Penalty severity is a 1-5 score, not a modelled cost.

## 7. Hedge LP with a CVaR floor (`hedge.py`)

Variables: share x_j of production under each offer (x_j >= 0, sum <= 1; the rest is merchant). Scenario revenue R_s = m_s + sum_j x_j (o_sj - m_s) where o_sj and m_s are scenario NPVs net of credit loss. Maximise mean R_s subject to CVaR of the worst tail >= floor, using the Rockafellar-Uryasev linearisation (variables eta and shortfalls u_s >= eta - R_s; CVaR = eta - (1/K) sum u_s). **K = ceil(alpha n)** scenarios form the tail, alpha = 10%. Solver: `scipy.optimize.linprog`.

- **Default floor (`recommend.py`):** merchant CVaR + 0.5 x (max achievable CVaR - merchant CVaR), where the maximum is the best CVaR the winning offer can deliver. A stated, adjustable assumption: it asks the hedge to close half the gap between the all-merchant downside and the best downside available.
- The single-offer share sizes how much production goes under the MCDA winner; the full multi-offer LP is shown for comparison, and the app says when it disagrees.
- *Limitations:* the tail comes from a limited number of historical-shape scenarios (about 100), so CVaR is noisy; scenarios are equally weighted; no transaction costs; shares are static for the whole tenor.

## 8. Fair price range and breakeven (`pricing.py`, `hedge.py`)

- **Fair pay-as-produced price (mid)** = P50 capture price - imbalance cost - margin + GoO value (if transferred). The **low end** is the mid minus the gap between the P50 and P10 capture price (a risk discount from the scenario spread). Inputs: imbalance cost, margin and GoO value are placeholders until Task 12 sourcing is done (see `examples/puglia/assumptions.toml`).
- **Breakeven** (`merchant_breakeven_price`): the offer price at which the offer's mean NPV equals the mean NPV of staying merchant, found by root-finding on (0, 1000] EUR/MWh. For a floor offer it is the floor level. If no such price exists the app shows "n/a".
- *Limitations:* the range is built on an assumed margin and a scenario spread, not on observed deal prices. See `docs/benchmarks.md` for the only dated external comparison found so far.

## 9. Backtest (`pricing.py`)

"Sign at last year's capture price": the prediction for year *t* is the capture price of year *t-1*; the error against the realised value is published next to the price range. *Limitation:* a naive one-step forecast on a few years of data; status "pending real data".
