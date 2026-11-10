# Data sources

All sources are public. Check each source's terms of use before publishing data, and cite the source in every chart and deliverable.

| Data | Source | Access | Notes |
|---|---|---|---|
| Day-ahead prices by Italian bidding zone | ENTSO-E Transparency Platform — transparency.entsoe.eu | Free registration; request a REST API token by email to the ENTSO-E helpdesk after registering | Python client: `entsoe-py`. Italian zones: NORD, CNOR, CSUD, SUD, CALA, SICI, SARD |
| Actual generation by type (solar, wind) per zone | ENTSO-E Transparency Platform | Same token | Useful to check national profiles |
| Solar production profile for a specific site | PVGIS (EU Joint Research Centre) — re.jrc.ec.europa.eu/pvg_tools | Free, no key; web tool and API | Hourly series for a given lat/lon, capacity, tilt |
| Wind production profile for a specific site | Renewables.ninja — renewables.ninja | Free registration for API | Hourly capacity factors from reanalysis data |
| Imbalance / ancillary prices | Terna — terna.it (Transparency / download centre) | Public downloads | Used for imbalance-cost assumptions |
| Italian market and regulation | GME (mercatoelettrico.org), GSE (gse.it), Terna, ARERA (arera.it) | Public | Verify current status of PUN phase-out, FER X, MACSE before writing the market note |
| Guarantees of origin | GSE; EEX auction results | Public | For GoO value assumptions |

| Italian zonal prices (cross-check only) | Energy-Charts (Fraunhofer ISE) — api.energy-charts.info | No key | Licence for Italian zones: **private and internal use only** — never publish raw or derived data from it |

## Rules

- Raw downloads go in `data/raw/` and are not committed if terms forbid redistribution.
- Every assumption (imbalance cost, risk discount, GoO price) is written in `docs/methodology.md` with its source.
- Numbers in deliverables are indicative and labelled as such.
