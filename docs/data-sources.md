# Data sources

All sources are public. Cite the source in every chart and deliverable.

The shipped data are in `data/precomputed/` (committed Parquet files plus `manifest.json`, which the app footer reads). They can be rebuilt from either of two sources that write identical files:

```bash
# ENTSO-E File Library zips (monthly CSV extracts, registered download, no API token)
python scripts/build_data.py --source file-library --prices-zips data/raw/energyprices.zip data/raw/Energyprices2.zip \
    --solar-zips data/raw/AggregatedGenerationPerType.zip data/raw/AggregatedGenerationPerType2.zip \
    --imbalance-zips data/raw/ImbalancePrices.zip data/raw/ImbalacePrices2.zip --sites
# ENTSO-E API (free token in the environment)
ENTSOE_TOKEN=... python scripts/build_data.py --source api --start 2021-01 --sites
```

`--zones` limits the build to some zones; `--sites` also fetches the PVGIS site profiles. Raw downloads go in `data/raw/` and are not committed.

| Data | Source | Access | File Library folder | Files written | Build command | Licence decision / note |
|---|---|---|---|---|---|---|
| Day-ahead prices by bidding zone (NORD, CNOR, CSUD, SUD, CALA, SICI, SARD) | ENTSO-E Transparency Platform | File Library zips (registered download) or API token | `EnergyPrices_12.1.D_r3.1` | `prices_<ZONE>.parquet` | `build_data.py --source file-library --prices-zips ...` or `--source api` | Publication allowed per the author's reading of the ENTSO-E terms of use. Hourly UTC; 15-minute prices (from 1 Oct 2025) averaged to hourly. Gaps up to 6 hours interpolated; longer gaps stay missing |
| Actual solar generation by zone | ENTSO-E Transparency Platform | Same | `AggregatedGenerationPerType_16.1.B_C_r3` (production type Solar) | `solar_zone_<ZONE>.parquet` | `build_data.py ... --solar-zips ...` | Same decision. Used for the zonal solar shape only (normalised). SARD has gaps in 2022-2025: those years use the PVGIS shape |
| Imbalance prices by zone | ENTSO-E Transparency Platform | Same | `ImbalancePrices_17.1.G_r3.1` | `imbalance_<ZONE>.parquet` | `build_data.py ... --imbalance-zips ...` | Same decision. Positive and negative prices collapsed to one price (non-zero side) before storing; available from 2022-03-31 |
| Site solar profile (one site per zone) | PVGIS (EU Joint Research Centre), re.jrc.ec.europa.eu/pvg_tools | Free, no key | not applicable | `site_<ZONE>.parquet` | `build_data.py ... --sites` | Cite "PVGIS (c) European Union". Weather years 2005-2023 |
| Region to zone mapping | GME zone table; Terna "Le nuove zone del mercato elettrico" | Public | not applicable | `src/ppa_italia/zones.py` | not applicable | URLs in the module docstring |
| Guarantees of origin | GSE; EEX auction results | Public | not applicable | `examples/default/assumptions.toml` | not applicable | Placeholder (1.0 EUR/MWh) until sourced |
| Italian market and regulation | GME, GSE, Terna, ARERA | Public | not applicable | `docs/term-sheet-*.md` | not applicable | Verify the current status of the PUN phase-out before relying on the change-in-law wording |
| Default probabilities | S&P Global Ratings annual default study (as cited in `credit.py`) | Public report | not applicable | `src/ppa_italia/credit.py` | not applicable | Edition and values to be verified |
| PPA price benchmarks | Press reports of LevelTen / Pexapark indices | Public articles | not applicable | `docs/benchmarks.md` | not applicable | One dated figure so far, with caveats |
| Italian zonal prices (cross-check only) | Energy-Charts (Fraunhofer ISE), api.energy-charts.info | No key | not applicable | none | **Never used** | Licence for Italian zones: private and internal use only. No raw or derived data from it is stored or published |

Not built: actual wind generation per zone (the loader remains but the pipeline does not produce wind profiles).

## Open items

- GoO value and margin are placeholders; default probabilities need their edition checked against the source.
- Terms link for the ENTSO-E licence decision: the author to record the terms version and date read.

## Rules

- Every assumption (imbalance error share, balancing fee, price-level band, hedge floor share, margin, GoO price) is written in `docs/methodology.md` and `examples/default/assumptions.toml` or `offers.csv` with its source, or marked as a placeholder.
- Numbers in deliverables are indicative and labelled as such.
