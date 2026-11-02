import math

import pytest

from app.risk.geo import GeoError, field_from_geojson, polygon_area_ha


def square(lon, lat, size):
    return {"type": "Polygon", "coordinates": [[
        [lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat],
    ]]}


def test_area_of_small_square_at_equator():
    side_m = math.radians(0.01) * 6371008.8
    field = field_from_geojson(square(0, 0, 0.01))
    assert field["area_ha"] == pytest.approx(side_m ** 2 / 10000, rel=0.002)


def test_area_shrinks_with_latitude_and_ignores_winding():
    ring = [(38.98, 8.75), (38.99, 8.75), (38.99, 8.76), (38.98, 8.76), (38.98, 8.75)]
    a = polygon_area_ha(ring)
    assert a == pytest.approx(polygon_area_ha(list(reversed(ring))))
    assert a == pytest.approx(polygon_area_ha([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)])
                              * math.cos(math.radians(8.755)), rel=0.002)


def test_unclosed_ring_is_closed_and_centre_found():
    geo = {"type": "Polygon", "coordinates": [[[38.98, 8.75], [38.99, 8.75], [38.99, 8.76], [38.98, 8.76]]]}
    field = field_from_geojson(geo)
    assert field["lat"] == pytest.approx(8.755)
    assert field["lon"] == pytest.approx(38.985)


@pytest.mark.parametrize("geo", [
    {"type": "Point", "coordinates": [38.9, 8.7]},
    {"type": "Polygon", "coordinates": [[[38.9, 8.7], [38.91, 8.7]]]},
    {"type": "Polygon", "coordinates": [[[200, 8.7], [38.91, 8.7], [38.91, 8.71]]]},
    {"type": "Polygon", "coordinates": [[[38.9, 8.7], [38.9, 8.7], [38.9, 8.7], [38.9, 8.7]]]},
    square(38, 8, 1.0),  # about 1.2 million hectares
])
def test_bad_boundaries_are_rejected(geo):
    with pytest.raises(GeoError):
        field_from_geojson(geo)
