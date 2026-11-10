# Italian Renewables Route-to-Market Toolkit

A commercial toolkit for valuing Italian renewable assets and preparing customer-ready route-to-market proposals: market analysis, PPA structure comparison, tender evaluation, contract management and settlement reconciliation.

> **Status (2026-11-10):** depth foundations built and tested — capture-rate engine, real PVGIS solar profile for the Puglia park (P50 29,335 MWh/yr, 1,468 kWh/kWp), PPA pricing formula, tender scoring with robustness check. Zonal prices wait on the ENTSO-E API token. See [ROADMAP.md](ROADMAP.md) and the [ambition plan](docs/ambition-plan.md).
>
> **Quick start:** `pip install -r requirements.txt` · `python -m pytest` · `python scripts/build_solar_profile.py` · set `ENTSOE_TOKEN` for prices.
>
> **Disclaimer:** all models are simplified and indicative, built on public data for learning and demonstration. They are not trading advice and do not represent any company's actual pricing.

## Why this project

Built as a portfolio project for a student role in **Commercial Asset Management (Italy)** at an energy trading company: supporting Italian customers with renewable assets through contract management, tender and sales material, customer meetings, collaboration with middle/back office, and internal projects.

The goal is to show I could sit down with an Italian renewable asset owner with a credible analysis and proposal.

## Scenario

I play a junior commercial asset manager. A fictional customer owns:

- a **20 MW solar park in Puglia** (SUD bidding zone)
- a **wind park in Sicily** (SICI bidding zone)

The customer wants to know how to sell their power. The toolkit covers the full path from analysis to proposal.

## Components and the role tasks they cover

| Role task | Component | Folder |
|---|---|---|
| Energy market understanding | **Asset value engine** — Italian zonal day-ahead prices (ENTSO-E) and generation profiles (PVGIS solar, Renewables.ninja wind) → capture price and capture rate by zone, solar cannibalisation trend, zero/negative-price hours | `src/value_engine/` |
| Solutions for customer growth, drafting contracts | **Route-to-market comparison** — merchant vs fixed-price PPA (pay-as-produced, baseload), floor, collar; includes imbalance costs, profile risk, guarantee-of-origin (GoO) value → indicative price range with risk discount | `src/rtm_pricing/` |
| Tender and sales material | **Customer proposal** — 2-page proposal in **Italian and English**: findings, recommended options, risks | `deliverables/proposal/` |
| Managing tender processes | **Offer comparison** — 3 fictional PPA offers scored on explicit weighted criteria (price, tenor, indexation, counterparty, penalties), multi-criteria method | `src/tender_eval/` |
| Contract management | **Contract register** — simulated portfolio of 10-15 Italian contracts: key terms, expiries, indexation, renewal alerts, volume deviations | `src/contracts/` |
| Collaboration with middle/back office | **Settlement reconciliation** — contracted volume vs metered production vs invoiced amount, with exceptions flagged | `src/contracts/settlement/` |
| Customer growth, business development | **Portfolio opportunity map** — expiring contracts, assets not monetising GoOs, assets in zones with many negative-price hours (battery co-location candidates) | `src/opportunities/` |
| Internal projects | **Italian market note** — zonal pricing transition (PUN phase-out), renewable auctions (FER X), storage auctions (MACSE). Every regulatory point verified on GSE / Terna / ARERA before writing | `deliverables/market-note/` |

## Stack

- **Python** (pandas, requests, entsoe-py) — data and models
- **Power BI** — portfolio dashboard
- **Excel** — offer comparison and contract register views
- **PDF** — customer proposal and market note

## Data sources

See [docs/data-sources.md](docs/data-sources.md).

## Planned structure

```
italian-renewables-rtm/
├── README.md
├── ROADMAP.md
├── docs/
│   ├── data-sources.md
│   ├── methodology.md        # capture rate, PPA pricing, assumptions
│   └── ambition-plan.md      # altitude / depth / range plan and outside judges
├── data/
│   ├── raw/                  # downloaded, not committed
│   └── processed/
├── src/
│   ├── value_engine/
│   ├── rtm_pricing/
│   ├── tender_eval/
│   ├── contracts/
│   │   └── settlement/
│   └── opportunities/
├── notebooks/                # exploration
├── dashboards/               # Power BI file
└── deliverables/
    ├── tender/               # offer comparison
    ├── proposal/             # IT + EN
    ├── contracts/            # term sheet summary
    ├── customer-meeting/     # slides (IT)
    ├── settlement/           # reconciliation report
    └── market-note/
```

## How I approached it / what I learned

To be written as the project progresses: problem, approach, choices and trade-offs, what I learned, and what I would do with real customer data.
