"""Italian bidding zones, the region -> zone mapping and one representative solar site per zone.

Region -> zone follows the zone configuration in force since 1 January 2021 (7 zones; Calabria
became its own zone and Umbria moved from Centro-Nord to Centro-Sud). Sources:
- GME (Italian power exchange) zone table listing the regions of each zone:
  https://www.mercatoelettrico.org/portals/0/Documents/it-IT/20231018_ME_Zone.pdf
- Terna, "Le nuove zone del mercato elettrico" (confirms the 2021 configuration and the Umbria move):
  https://lightbox.terna.it/it/insight/riorganizzazione-zone-mercato-elettrico

Every region is wholly inside one zone, so no region needs a split-assignment choice. Trentino-Alto
Adige is one region here (the GME table lists "Trentino" under NORD).
"""
from __future__ import annotations

ZONES: tuple[str, ...] = ("NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD")

REGION_TO_ZONE: dict[str, str] = {
    "Valle d'Aosta": "NORD",
    "Piemonte": "NORD",
    "Liguria": "NORD",
    "Lombardia": "NORD",
    "Trentino-Alto Adige": "NORD",
    "Veneto": "NORD",
    "Friuli-Venezia Giulia": "NORD",
    "Emilia-Romagna": "NORD",
    "Toscana": "CNOR",
    "Marche": "CNOR",
    "Lazio": "CSUD",
    "Abruzzo": "CSUD",
    "Campania": "CSUD",
    "Umbria": "CSUD",
    "Molise": "SUD",
    "Puglia": "SUD",
    "Basilicata": "SUD",
    "Calabria": "CALA",
    "Sicilia": "SICI",
    "Sardegna": "SARD",
}

# (site name, latitude, longitude): a typical utility-scale solar area of each zone.
ZONE_SITE: dict[str, tuple[str, float, float]] = {
    "NORD": ("Mantova", 45.16, 10.79),
    "CNOR": ("Grosseto", 42.76, 11.11),
    "CSUD": ("Viterbo", 42.42, 12.11),
    "SUD": ("Foggia", 41.46, 15.55),
    "CALA": ("Crotone", 39.08, 17.13),
    "SICI": ("Catania", 37.50, 15.09),
    "SARD": ("Sassari", 40.73, 8.56),
}


def zone_of(region: str) -> str:
    """Return the bidding-zone code of an Italian region; raise KeyError if the region is unknown."""
    return REGION_TO_ZONE[region]
