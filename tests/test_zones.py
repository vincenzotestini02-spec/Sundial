import pytest

from ppa_italia.zones import REGION_TO_ZONE, ZONE_SITE, ZONES, zone_of


def test_every_region_maps_to_a_known_zone():
    assert len(REGION_TO_ZONE) == 20
    assert set(REGION_TO_ZONE.values()) <= set(ZONES)
    assert zone_of("Puglia") == "SUD" and zone_of("Sicilia") == "SICI" and zone_of("Sardegna") == "SARD"
    assert set(ZONE_SITE) == set(ZONES) and ZONE_SITE["SUD"][1:] == (41.46, 15.55)


def test_zone_of_unknown_region_raises():
    with pytest.raises(KeyError):
        zone_of("Atlantide")
