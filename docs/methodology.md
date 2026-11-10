# Methodology

Indicative models on public data. Not trading advice; not any company's pricing.

## Capture price and capture rate (`src/value_engine/capture.py`)

For hourly prices *p_h* (EUR/MWh) and generation *g_h* (MWh):

- Baseload price = mean(*p_h*)
- Capture price = Σ *p_h g_h* / Σ *g_h*
- Capture rate = capture price / baseload price
- Negative-price exposure = hours with *p_h* ≤ 0, and the share of yearly generation produced in them

**15-minute prices.** Since 1 Oct 2025 the day-ahead market clears in 15-minute steps. Prices are averaged to hourly to match hourly generation profiles. This slightly smooths intra-hour price shape; acceptable for indicative valuation.

## Solar profile (`src/value_engine/pvgis.py`, `scripts/build_solar_profile.py`)

- Site: Tavoliere plain near Foggia, 41.46 N 15.55 E (SUD zone). Fictional 20 MWp park.
- PVGIS v5.3, PVGIS-SARAH3 radiation, crystalline silicon, fixed mounting at PVGIS-optimal angles (36°, azimuth −5°), 14% system losses.
- Weather years 2005-2023 (19 years).

**Result (2026-11-10 run):** P50 29,335 MWh/yr, P90 28,308 MWh/yr, mean specific yield 1,468 kWh/kWp, inter-annual variability 3.0%.
**Implication:** weather volume risk is small (P90 only ~3.5% below P50); for this asset, price and profile risk (cannibalisation) dominate. The proposal should weight risks accordingly.
**Limits:** no curtailment, no degradation (~0.4-0.5%/yr typical; to add), no availability losses beyond the 14% lump. Check: plausibility range only; the true judge would be metered data.

## Pay-as-produced PPA price (`src/rtm_pricing/ppa.py`)

Fair PaP price = expected capture price − imbalance cost − risk discount − margin + GoO value (if transferred).

| Assumption | Value | Source |
|---|---|---|
| Imbalance cost | TBD | Terna imbalance prices |
| Risk discount | TBD | derived from P50–P90 spread of capture price |
| Margin | TBD | stated assumption, labelled as such |
| GoO value | TBD | GSE / EEX auction results |

**Weather × price distribution.** Each weather-year profile is paired with each price year by hour-of-year. Limitation: this breaks the real same-hour link between sunshine and price, so it understates cannibalisation in sunny years.

**Backtest.** "Sign at last year's capture price" vs realised next-year capture price; the error is published next to the price range.

## Tender scoring (`src/tender_eval/scoring.py`)

Min-max normalised criteria, weighted sum. Robustness: 5,000 Dirichlet draws around the chosen weights (concentration 20); report each offer's share of first places. Below 70% → recommendation labelled fragile.
