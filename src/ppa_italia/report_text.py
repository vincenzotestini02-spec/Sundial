"""Bilingual (Italian / English) copy for the customer report.

Templates use ``str.format`` fields: {offer} {share_pct} {fair_low} {fair_mid}
{win_pct} {breakeven} {capture_rate} {zone} {price} {rating} {tenor} {index_pct}
{floor_label}. Italian templates also use article fields that elide before a
vowel sound ({il_share} = "il " / "l'", {nel_win} = "nel " / "nell'",
{al_capture}, {al_index} = "al " / "all'"); English templates ignore them. Both languages
share identical keys.
"""
from __future__ import annotations

from typing import Literal

DISCLAIMER_EN = "Indicative, educational, built on public data. Not trading advice and not any company's pricing."
SYNTHETIC_LABEL = "SYNTHETIC — placeholder until ENTSO-E data"

TEXT: dict[Literal["it", "en"], dict[str, str]] = {
    "en": {
        "title": "PPA assessment — zone {zone}",
        "disclaimer": DISCLAIMER_EN,
        "sources": "Sources: ENTSO-E Transparency Platform; PVGIS © European Union.",
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
            "Share of production allocated to each offer in the multi-offer mix chosen by the "
            "risk-constrained optimisation (the recommended offer is {offer}):"
        ),
        "options_single": "Recommended offer alone ({offer}): {share_pct}% of production, the rest merchant.",
        "options_single_block": (
            "Recommended offer alone ({offer}): a {block_mw} MW baseload block (about {block_pct}% of "
            "average production), {volume}; production above the block stays at spot."
        ),
        "recommendation_block": (
            "Recommendation\n"
            "Sign offer {offer}, a {block_mw} MW baseload block (about {block_pct}% of average "
            "production), {volume}. Fair pay-as-produced price range: {fair_low}-{fair_mid} EUR/MWh."
        ),
        "volume_full": "for the full contracted volume",
        "volume_part": "for {share_pct}% of the contracted volume",
        "col_offer": "Offer",
        "col_share": "Share of production",
        "recommendation": (
            "Recommendation\n"
            "Sign offer {offer} for {share_pct}% of production. Fair pay-as-produced price range: "
            "{fair_low}-{fair_mid} EUR/MWh."
        ),
        "recommendation_merchant": (
            "Recommendation\n"
            "Stay merchant for now; best offer if hedging: {offer}. Fair pay-as-produced price "
            "range: {fair_low}-{fair_mid} EUR/MWh."
        ),
        "floor_label": " (floor level)",
        "breakeven": (
            "Merchant break-even price{floor_label} of offer {offer}: {breakeven} EUR/MWh. This is "
            "the level at which the offer matches staying merchant on expected value; it is "
            "distinct from the fair price range above."
        ),
        "risks": (
            "Risks\n"
            "Prices, volumes and counterparty credit are scenario-based; results change with the "
            "assumptions."
        ),
        "risk_pap": (
            " A pay-as-produced fixed price removes price risk on the contracted share but gives "
            "up the upside if the market rises."
        ),
        "risk_baseload": (
            " A baseload contract fixes the price for a flat block: in hours when the plant "
            "produces less than the block, the seller buys the shortfall at spot, so it carries "
            "shape and volume risk."
        ),
        "risk_floor": (
            " A floor keeps the upside: the seller earns spot when it is above the floor. The cost "
            "is the premium paid on every contracted MWh, whether or not the floor is used."
        ),
        "red_team_fragile": (
            "Case against: the recommendation wins in only {win_pct}% of weightings of the "
            "tender criteria, so the ranking is fragile and a different priority could favour "
            "another offer."
        ),
        "red_team_robust": (
            "Case against: the recommendation wins in {win_pct}% of weightings, so it is robust "
            "to the choice of criteria."
        ),
        "red_floor_below": (
            " The floor at {price} EUR/MWh is below its own break-even of {breakeven} EUR/MWh: the "
            "offer costs expected value and is bought only for downside protection."
        ),
        "red_floor_above": (
            " The floor at {price} EUR/MWh is above its own break-even of {breakeven} EUR/MWh: it "
            "adds expected value as well as protection, so check why the buyer offers it."
        ),
        "red_fixed_below": (
            " The price of {price} EUR/MWh is below the merchant break-even of {breakeven} EUR/MWh: "
            "signing costs expected value in exchange for certainty."
        ),
        "red_fixed_above": (
            " The price of {price} EUR/MWh is above the merchant break-even of {breakeven} EUR/MWh: "
            "the offer beats merchant on expected value, so the case against is the upside given up."
        ),
        "red_rating_sub_ig": (
            " The buyer is rated {rating}, below investment grade: a default puts the remaining "
            "years back on merchant prices. The expected loss is deducted from the hedge value, "
            "but the tail is not."
        ),
        "red_rating_ig": (
            " The buyer is rated {rating} (investment grade): credit risk is small but not zero."
        ),
        "red_tenor_flat": (
            " The price runs for {tenor} years with no indexation, so inflation erodes its real value."
        ),
        "red_tenor_indexed": (
            " The price runs for {tenor} years, indexed at {index_pct}% a year."
        ),
        "red_team_disagrees": (
            " Note: the criteria ranking and the risk-constrained allocation point to different "
            "offers, so treat the result with additional caution."
        ),
        "na": "n/a",
    },
    "it": {
        "title": "Valutazione PPA — zona {zone}",
        "sources": "Fonti: ENTSO-E Transparency Platform; PVGIS © European Union.",
        "disclaimer": (
            "Indicativo, a scopo educativo, basato su dati pubblici. Non è consulenza di trading "
            "né il prezzo di alcuna società."
        ),
        "synthetic_banner": (
            SYNTHETIC_LABEL + " (prezzi sintetici, da sostituire con i dati ENTSO-E)"
        ),
        "situation": (
            "Situazione\n"
            "Nella zona {zone}, il capture rate più recente della vostra produzione è pari "
            "{al_capture}{capture_rate}% del prezzo baseload. Più è basso, meno l'esposizione "
            "merchant pura incassa rispetto al prezzo medio di mercato."
        ),
        "capture_trend": "Capture rate per anno",
        "options": (
            "Opzioni\n"
            "Quota di produzione assegnata a ciascuna offerta nel mix di più offerte scelto "
            "dall'ottimizzazione con vincolo di rischio (l'offerta raccomandata è la {offer}):"
        ),
        "options_single": (
            "Offerta raccomandata da sola ({offer}): {il_share}{share_pct}% della produzione, il "
            "resto merchant."
        ),
        "options_single_block": (
            "Offerta raccomandata da sola ({offer}): un blocco baseload di {block_mw} MW (circa il "
            "{block_pct}% della produzione media), {volume}; la produzione oltre il blocco resta al "
            "prezzo di mercato."
        ),
        "recommendation_block": (
            "Raccomandazione\n"
            "Firmare l'offerta {offer}, un blocco baseload di {block_mw} MW (circa il {block_pct}% "
            "della produzione media), {volume}. Intervallo di prezzo equo pay-as-produced: "
            "{fair_low}-{fair_mid} EUR/MWh."
        ),
        "volume_full": "per l'intero volume contrattuale",
        "volume_part": "per {il_share}{share_pct}% del volume contrattuale",
        "col_offer": "Offerta",
        "col_share": "Quota di produzione",
        "recommendation": (
            "Raccomandazione\n"
            "Firmare l'offerta {offer} per {il_share}{share_pct}% della produzione. Intervallo di "
            "prezzo equo pay-as-produced: {fair_low}-{fair_mid} EUR/MWh."
        ),
        "recommendation_merchant": (
            "Raccomandazione\n"
            "Per ora restare merchant; migliore offerta in caso di copertura: {offer}. "
            "Intervallo di prezzo equo pay-as-produced: {fair_low}-{fair_mid} EUR/MWh."
        ),
        "floor_label": " (livello del floor)",
        "breakeven": (
            "Prezzo di pareggio rispetto al merchant{floor_label} dell'offerta {offer}: "
            "{breakeven} EUR/MWh. È il livello al quale l'offerta eguaglia il restare merchant in "
            "termini di valore atteso; è distinto dall'intervallo di prezzo equo indicato sopra."
        ),
        "risks": (
            "Rischi\n"
            "Prezzi, volumi e rischio di credito della controparte sono basati su scenari; i "
            "risultati cambiano al variare delle ipotesi."
        ),
        "risk_pap": (
            " Un prezzo fisso pay-as-produced elimina il rischio di prezzo sulla quota contrattata "
            "ma rinuncia al rialzo se il mercato sale."
        ),
        "risk_baseload": (
            " Un contratto baseload fissa il prezzo su un blocco costante: nelle ore in cui "
            "l'impianto produce meno del blocco, il venditore acquista la differenza a prezzo "
            "spot, quindi sopporta il rischio di profilo e di volume."
        ),
        "risk_floor": (
            " Un floor conserva il rialzo: il venditore incassa lo spot quando è sopra il floor. "
            "Il costo è il premio pagato su ogni MWh contrattato, che il floor venga usato o no."
        ),
        "red_team_fragile": (
            "Il caso contrario: la raccomandazione prevale solo {nel_win}{win_pct}% delle "
            "ponderazioni dei criteri di gara, quindi la graduatoria è fragile e una priorità "
            "diversa potrebbe favorire un'altra offerta."
        ),
        "red_team_robust": (
            "Il caso contrario: la raccomandazione prevale {nel_win}{win_pct}% delle ponderazioni, "
            "quindi è robusta rispetto alla scelta dei criteri."
        ),
        "red_floor_below": (
            " Il floor a {price} EUR/MWh è sotto il proprio prezzo di pareggio di {breakeven} "
            "EUR/MWh: l'offerta costa valore atteso e si acquista solo come protezione dal ribasso."
        ),
        "red_floor_above": (
            " Il floor a {price} EUR/MWh è sopra il proprio prezzo di pareggio di {breakeven} "
            "EUR/MWh: aggiunge valore atteso oltre alla protezione, quindi va capito perché "
            "l'acquirente lo offre."
        ),
        "red_fixed_below": (
            " Il prezzo di {price} EUR/MWh è sotto il prezzo di pareggio merchant di {breakeven} "
            "EUR/MWh: firmare costa valore atteso in cambio di certezza."
        ),
        "red_fixed_above": (
            " Il prezzo di {price} EUR/MWh è sopra il prezzo di pareggio merchant di {breakeven} "
            "EUR/MWh: l'offerta batte il merchant in valore atteso, quindi il caso contrario è il "
            "rialzo a cui si rinuncia."
        ),
        "red_rating_sub_ig": (
            " L'acquirente ha rating {rating}, sotto l'investment grade: un default riporta gli "
            "anni residui ai prezzi merchant. La perdita attesa è dedotta dal valore della "
            "copertura, la coda no."
        ),
        "red_rating_ig": (
            " L'acquirente ha rating {rating} (investment grade): il rischio di credito è basso ma "
            "non nullo."
        ),
        "red_tenor_flat": (
            " Il prezzo vale per {tenor} anni senza indicizzazione, quindi l'inflazione ne riduce "
            "il valore reale."
        ),
        "red_tenor_indexed": (
            " Il prezzo vale per {tenor} anni, indicizzato {al_index}{index_pct}% annuo."
        ),
        "red_team_disagrees": (
            " Nota: la graduatoria dei criteri e l'allocazione con vincolo di rischio indicano "
            "offerte diverse; il risultato va quindi letto con ulteriore cautela."
        ),
        "na": "n/d",
    },
}
