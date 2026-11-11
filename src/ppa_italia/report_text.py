"""Bilingual (Italian / English) copy for the customer report.

Templates use ``str.format`` fields: {offer} {share_pct} {fair_low} {fair_mid}
{win_pct} {breakeven} {capture_rate} {zone}. Both languages share identical keys.
"""
from __future__ import annotations

from typing import Literal

DISCLAIMER_EN = "Indicative, educational, built on public data. Not trading advice and not any company's pricing."
SYNTHETIC_LABEL = "SYNTHETIC — placeholder until ENTSO-E data"

TEXT: dict[Literal["it", "en"], dict[str, str]] = {
    "en": {
        "title": "PPA assessment — zone {zone}",
        "disclaimer": DISCLAIMER_EN,
        "synthetic_banner": SYNTHETIC_LABEL,
        "situation": (
            "Situation\n"
            "In zone {zone}, the latest capture rate of your production is {capture_rate}% of the "
            "baseload price. The lower it falls, the less a plain merchant exposure earns "
            "relative to the average market price."
        ),
        "capture_trend": "Capture rate by year",
        "options": (
            "Options\n"
            "Share of production allocated to each offer by the risk-constrained optimisation "
            "(the recommended offer is {offer}):"
        ),
        "col_offer": "Offer",
        "col_share": "Share of production",
        "recommendation": (
            "Recommendation\n"
            "Sign offer {offer} for {share_pct}% of production. Fair price range: "
            "{fair_low}-{fair_mid} EUR/MWh."
        ),
        "recommendation_merchant": (
            "Recommendation\n"
            "Stay merchant for now; best offer if hedging: {offer}. Fair price range: "
            "{fair_low}-{fair_mid} EUR/MWh."
        ),
        "breakeven": (
            "Merchant break-even price of offer {offer}: {breakeven} EUR/MWh. This is the level at "
            "which the offer matches staying merchant on expected value; it is distinct from the "
            "fair price range above."
        ),
        "risks": (
            "Risks\n"
            "Prices, volumes and counterparty credit are scenario-based; results change with the "
            "assumptions. A fixed-price structure gives up upside if the market rises."
        ),
        "red_team_fragile": (
            "Case against: the recommendation wins in only {win_pct}% of weightings of the "
            "tender criteria, so the ranking is fragile and a different priority could favour "
            "another offer."
        ),
        "red_team_robust": (
            "Case against: the recommendation wins in {win_pct}% of weightings, so it is robust "
            "to the choice of criteria. Even so, a merchant view would argue that hedging gives "
            "up expected upside in exchange for lower risk."
        ),
        "red_team_disagrees": (
            " Note: the criteria ranking and the risk-constrained allocation point to different "
            "offers, so treat the result with additional caution."
        ),
        "na": "n/a",
    },
    "it": {
        "title": "Valutazione PPA — zona {zone}",
        "disclaimer": (
            "Indicativo, a scopo educativo, basato su dati pubblici. Non è consulenza di trading "
            "né il prezzo di alcuna società."
        ),
        "synthetic_banner": (
            SYNTHETIC_LABEL + " (prezzi sintetici, da sostituire con i dati ENTSO-E)"
        ),
        "situation": (
            "Situazione\n"
            "Nella zona {zone}, il capture rate più recente della vostra produzione è pari al "
            "{capture_rate}% del prezzo baseload. Più è basso, meno l'esposizione merchant pura "
            "incassa rispetto al prezzo medio di mercato."
        ),
        "capture_trend": "Capture rate per anno",
        "options": (
            "Opzioni\n"
            "Quota di produzione assegnata a ciascuna offerta dall'ottimizzazione con vincolo di "
            "rischio (l'offerta raccomandata è la {offer}):"
        ),
        "col_offer": "Offerta",
        "col_share": "Quota di produzione",
        "recommendation": (
            "Raccomandazione\n"
            "Firmare l'offerta {offer} per il {share_pct}% della produzione. Intervallo di "
            "prezzo equo: {fair_low}-{fair_mid} EUR/MWh."
        ),
        "recommendation_merchant": (
            "Raccomandazione\n"
            "Per ora restare merchant; migliore offerta in caso di copertura: {offer}. "
            "Intervallo di prezzo equo: {fair_low}-{fair_mid} EUR/MWh."
        ),
        "breakeven": (
            "Prezzo di pareggio rispetto al merchant dell'offerta {offer}: {breakeven} EUR/MWh. "
            "È il livello al quale l'offerta eguaglia il restare merchant in termini di valore "
            "atteso; è distinto dall'intervallo di prezzo equo indicato sopra."
        ),
        "risks": (
            "Rischi\n"
            "Prezzi, volumi e rischio di credito della controparte sono basati su scenari; i "
            "risultati cambiano al variare delle ipotesi. Una struttura a prezzo fisso rinuncia "
            "al rialzo se il mercato sale."
        ),
        "red_team_fragile": (
            "Il caso contrario: la raccomandazione prevale solo nel {win_pct}% delle ponderazioni "
            "dei criteri di gara, quindi la graduatoria è fragile e una priorità diversa potrebbe "
            "favorire un'altra offerta."
        ),
        "red_team_robust": (
            "Il caso contrario: la raccomandazione prevale nel {win_pct}% delle ponderazioni, "
            "quindi è robusta rispetto alla scelta dei criteri. Una lettura merchant osserverebbe "
            "comunque che la copertura rinuncia a parte del rialzo atteso in cambio di minore "
            "rischio."
        ),
        "red_team_disagrees": (
            " Nota: la graduatoria dei criteri e l'allocazione con vincolo di rischio indicano "
            "offerte diverse; il risultato va quindi letto con ulteriore cautela."
        ),
        "na": "n/d",
    },
}
