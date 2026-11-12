# Methodology

Indicative models on public data. Not trading advice; not any company's pricing. Every number in the app comes from a tested function in `src/ppa_italia/`. The shipped run uses real ENTSO-E day-ahead prices, zonal solar generation and imbalance prices for the seven Italian bidding zones. A zone without real price files falls back to a labelled synthetic series.

## 1. Capture price and capture rate (`value.py`)

For hourly prices *p_h* (EUR/MWh) and generation *g_h* (MWh):

- Baseload price = mean(*p_h*)
- Capture price = sum(*p_h g_h*) / sum(*g_h*)
- Capture rate = capture price / baseload price
- Negative-price exposure = hours with *p_h* <= 0 (zero and negative), and the share of yearly generation produced in them.

**15-minute prices.** Since 1 Oct 2025 the day-ahead market clears in 15-minute steps. Prices are averaged to hourly (`data/entsoe.py: to_hourly`) to match hourly generation profiles. This smooths intra-hour price shape. *Limitation:* slightly understates intra-hour volatility; acceptable for indicative valuation.

**Short data gaps.** `scripts/build_data.py` (File Library or API, `--source`) fills gaps of up to 6 consecutive missing hours by linear interpolation on a complete hourly UTC index (`fill_short_gaps`) and prints the hours filled per zone and year. Longer gaps stay missing, and incomplete years are not used as scenarios. *Limitation:* interpolation hides short real price spikes.

## 2. Region, zone and solar profile (`zones.py`, `data/pvgis.py`)

- **Region to zone** (`REGION_TO_ZONE`): the sidebar selects one of 20 regions and the app uses the region's bidding zone (NORD, CNOR, CSUD, SUD, CALA, SICI, SARD). The mapping follows the zone configuration in force since 1 January 2021 (Calabria is its own zone; Umbria is in CSUD). Sources: the GME zone table (https://www.mercatoelettrico.org/portals/0/Documents/it-IT/20231018_ME_Zone.pdf) and Terna, "Le nuove zone del mercato elettrico" (https://lightbox.terna.it/it/insight/riorganizzazione-zone-mercato-elettrico). Every region lies wholly in one zone; Trentino-Alto Adige is one region.
- **Representative site per zone** (`ZONE_SITE`): Mantova (NORD), Grosseto (CNOR), Viterbo (CSUD), Foggia (SUD), Crotone (CALA), Catania (SICI), Sassari (SARD). A typical utility-scale solar area of each zone; the park is a fictional 20 MWp plant.
- PVGIS v5.3, PVGIS-SARAH3 radiation, crystalline silicon, fixed mounting at PVGIS-optimal angles, 14% system losses. Weather years 2005-2023 (19 years), per site. PVGIS (c) European Union.
- SUD (Foggia): P50 29,335 MWh/yr, P90 28,308 MWh/yr (P90 is the value exceeded in 90% of years), mean specific yield 1,467 kWh/kWp, inter-annual variability 2.9%.
- Check: specific yield inside the 1,400-1,600 kWh/kWp plausibility range for a fixed-tilt Puglia plant.
- *Limitations:* no curtailment, no degradation (about 0.4-0.5%/yr typical), no availability losses beyond the 14% lump. The true judge would be metered data.

## 3. Price scenarios: "historical shape, current level" (`scenarios.py`)

- Each complete historical price year (8,760 hours) keeps its hourly shape, which carries the cannibalisation signal.
- Each year is multiplied so its baseload mean equals a **reference level**: the zone's trailing 12-month baseload mean (`trailing_baseload`; 148.1 EUR/MWh in SUD). The 2022 crisis therefore contributes its shape, not its level. Zero and negative hours stay at or below zero because the scaling is multiplicative.
- **Same-year pairing** (`build_scenarios_same_year`): the hourly solar shape of the *same calendar year* in the zone (ENTSO-E actual solar generation, normalised) is scaled to the energy of each PVGIS weather year of the site. Within a scenario, sun and price therefore come from the same hours, which keeps the sun-price link and the cannibalisation. Weather years differ only in total energy. Years where the zonal solar series has any missing hour after gap filling count as incomplete and use the PVGIS site shape instead; in the shipped data this affects SARD 2022-2025.
- **Price-level band:** history gives a shape, not a level. Every (price year, weather year) pair is repeated at 70%, 100% and 130% of the reference level (`price_level_band` = 0.30 in `examples/default/assumptions.toml`). The band is a stated, adjustable assumption, not a forecast; without it the scenarios have no price-level risk and no hedge is worth taking. Result: 5 price years (2021-2025) x 19 weather years x 3 levels = 285 scenarios, equally weighted.
- *Limitations:* the zonal fleet shape is applied to one site (fleet average, not that site's own shape). The shape of past years may not represent the future shape as solar capacity grows. One flat level ignores any forward curve. The three levels and the 19 weather years are not independent draws, so the tail still rests on only 5 price-year shapes.
- **Typical weather year for price-year statistics** (`profile_on_years`): where a single production profile is needed per calendar price year (for example the yearly capture-rate chart on Home), the median-energy weather year of the site is stamped onto each price year, with 29 Feb repeating 28 Feb. The yearly capture rates in the app and README are computed this way. *Limitation:* this hides weather variability in those charts only; the scenario set uses all weather years.

## 4. PPA structures: revenue formulas (`structures.py`)

Hourly revenue to the seller, per contract year *t*, with spot *p_h* escalated by the merchant escalation, price *P* escalated by the offer's indexation, and generation *g_h*:

| Structure | Revenue |
|---|---|
| Pay-as-produced (`pap`) | P x sum(g_h); with the negative-price clause, hours with p_h <= 0 carry zero volume |
| Baseload (`baseload`) | P x B x 8,760 + sum(p_h (g_h - B)); B is the contracted baseload MW. The second term is the shape risk |
| Floor (`floor`) | sum(max(p_h, P) v_h) - premium x sum(v_h), with contracted volume v_h = g_h; with the negative-price clause, v_h = 0 in hours with p_h <= 0 (no floor top-up, no spot revenue, no premium) |

Adjustments: if imbalance stays with the seller, the zone's imbalance cost (section 8) per MWh is deducted; if GoOs are not included in the offer, the GoO value per MWh is added. Merchant revenue is sum(p_h g_h) minus imbalance cost plus GoO value. Offers that move imbalance to the buyer carry a **balancing fee** of 110% of the zone's imbalance cost (`balancing_fee_pct_of_cost` in `examples/default/offers.csv`; an example assumption, since a buyer that takes imbalance charges for it): the pay-as-produced or baseload price is reduced by the fee, and the floor premium is increased by it. Without the fee those offers would take imbalance for free.

NPV over the horizon (the longest tenor) discounts year-end revenue at the stated rate; after an offer's tenor the plant earns merchant revenue. Offers with different tenors are therefore compared on the same horizon.

*Limitations:* the negative-price clause applies to pay-as-produced and floor offers; the baseload formula does not use it (a baseload block is a fixed hourly volume). Escalation of the merchant level is a single stated assumption (default 0%/yr real). No degradation, curtailment or basis between the contract and the physical node.

## 5. Credit expected loss (`credit.py`)

Expected loss = PD(rating) x LGD x exposure, accumulated over the tenor. Timing follows the NPV: revenue of contract year *k* is booked at the end of year *k*. A default during year *t* loses years *t* to *T*-1 and is recognised at the end of year *t*. Exposure is the mean over scenarios of the positive part of the present value, at the end of year *t*, of the remaining years' (offer - merchant) revenue, because the seller only loses if the contract is worth more than selling at spot. Loss in year *t* is weighted by the marginal default probability (1 - PD)^t PD, times LGD, and discounted (1 + r)^(t+1) to today, so each year's revenue gap is discounted (1 + r)^(k+1) in total, as in the NPV.

The expected loss (a present value in EUR) is subtracted from every scenario NPV of the offer before the hedge LPs (`npv_net_of_credit`), so the hedge objective is NPV net of credit loss.

- PD by rating: a small table of long-run one-year default rates (AAA 0%, AA 0.02%, A 0.05%, BBB 0.15%, BB 0.60%, B 3.00%), attributed in the code to the S&P annual default study. **The exact edition and values are not yet verified against the source** and must be checked by the author.
- LGD 60%: stated assumption (unsecured corporate).
- *Limitations:* constant PD per rating, no rating migration, no collateral modelled, no correlation between buyer default and price level.

## 6. Tender MCDA and Dirichlet robustness (`tender.py`)

- Criteria: mean NPV, P10 NPV, expected credit loss, tenor, indexation, imbalance on buyer, penalty severity. Min-max normalisation (direction-aware), weighted sum with default weights 0.30, 0.20, 0.15, 0.10, 0.05, 0.10, 0.10.
- **Robustness:** 5,000 weight vectors drawn from a Dirichlet distribution centred on the chosen weights (concentration 20). The robustness figure is each offer's share of first places. Below 70% the recommendation is labelled **fragile**.
- *Limitations:* the weights are the author's judgment, not elicited from a customer. Min-max normalisation makes scores depend on which offers are in the table. Penalty severity is a 1-5 score, not a modelled cost.

## 7. Hedge LP with a CVaR floor (`hedge.py`)

Variables: share x_j of production under each offer (x_j >= 0, sum <= 1; the rest is merchant). Scenario revenue R_s = m_s + sum_j x_j (o_sj - m_s) where o_sj and m_s are scenario NPVs net of credit loss. Maximise mean R_s subject to CVaR of the worst tail >= floor, using the Rockafellar-Uryasev linearisation (variables eta and shortfalls u_s >= eta - R_s; CVaR = eta - (1/K) sum u_s). **K = ceil(alpha n)** scenarios form the tail, alpha = 10%. Solver: `scipy.optimize.linprog`.

- **Default floor (`recommend.py`), bank-style:** the average NPV of the worst 10% of scenarios must be at least gamma x the expected merchant NPV, with gamma = 0.85 (`cvar_floor_share_of_mean` in the TOML; stated and adjustable). The target is capped at the best CVaR the winning offer can deliver (flag `floor_capped`). If merchant CVaR already meets the floor, the share is 0.
- **Result on real data:** the target is not reachable in any zone. The best achievable worst-10% NPV is 74-76% of the expected merchant NPV (SUD 75.9%), so the recommendation hedges as much as possible with the winning offer (share 100%). The app says so on Home and Hedge.
- The single-offer share sizes how much production goes under the MCDA winner; the full multi-offer LP is shown for comparison, and the app says when it disagrees.
- *Limitations:* the tail comes from 285 scenarios built on 5 price-year shapes, so CVaR is noisy; scenarios are equally weighted; no transaction costs; shares are static for the whole tenor.

## 8. Imbalance cost, fair price range, fair floor premium and breakeven (`imbalance.py`, `pricing.py`, `hedge.py`)

- **Imbalance cost per zone** (`imbalance_cost`): the producer misses a share epsilon = 0.10 of its output (`imbalance_error_share`, an assumption) and settles that volume at the imbalance price instead of the day-ahead price, so the cost is epsilon x the solar-weighted mean of abs(imbalance price - day-ahead price), over the last 24 complete calendar months. Italy has a single imbalance price per zone; ENTSO-E publishes a positive and a negative price with 0 on the unused side, so the build takes the non-zero side (mean if both, dropped if both are zero) and averages to hourly. Result: 5.11 EUR/MWh (NORD) to 6.61 (SARD); SUD 6.35. If a zone has no imbalance data, the TOML placeholder (3.0 EUR/MWh) is used and the app says so. *Limitation:* a proxy; real cost depends on the producer's forecast skill and on the sign of its error relative to the zonal imbalance.
- **Fair pay-as-produced price (mid)** = P50 capture price - imbalance cost - margin + GoO value (if transferred). The **low end** is the mid minus the gap between the P50 and P10 capture price (a risk discount from the scenario spread). Margin (2.0) and GoO value (1.0) are placeholders pending sourcing (`examples/default/assumptions.toml`). The range is a pay-as-produced fixed-price equivalent, labelled "fair pay-as-produced price range". SUD: 81.7 to 120.9 EUR/MWh (P50 capture 128.2 EUR/MWh across the 285 scenarios).
- **Fair floor premium** (`fair_floor_premium`): the expected value of the put the floor grants, per scenario sum(max(floor - p_h, 0) v_h) / sum(v_h), averaged over scenarios, with the same volume rule as the payoff (zero volume at p_h <= 0 when the offer has that clause). The example floor offer is priced at 120% of it, plus the balancing fee. SUD: fair 7.76 EUR/MWh, applied 16.31 EUR/MWh (9.32 premium + 6.99 fee).
- **Breakeven** (`merchant_breakeven_price`): the offer price at which the offer's mean NPV equals the mean NPV of staying merchant, found by root-finding on (0, 1000] EUR/MWh. For a floor offer it is the floor level. If no such price exists the app shows "n/a". SUD, offer B: 142.1 EUR/MWh against a price of 140.7.
- *Limitations:* the range is built on an assumed margin and a scenario spread, not on observed deal prices. See `docs/benchmarks.md` for the only dated external comparison found so far.

## 9. Backtest (`pricing.py`)

"Sign at last year's capture price": the prediction for year *t* is the capture price of year *t-1*; the error against the realised value is published next to the price range. SUD, 2022-2026 (2026 to 12 November): mean absolute error 79.8 EUR/MWh, dominated by the 2022 crisis (+180.5 in 2022, -180.5 in 2023); -14.6 (2024), +2.2 (2025), +21.1 (2026). *Limitation:* a naive one-step forecast on a few years of data; it shows that a trailing anchor breaks when the price level moves, which is the reason the scenarios carry a stated level band.
