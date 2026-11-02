"""Field boundaries: GeoJSON polygon checks, area and centre."""

import math

EARTH_RADIUS_M = 6371008.8
MAX_FIELD_HA = 5000  # anything bigger is almost certainly a drawing mistake


class GeoError(ValueError):
    pass


def ring_from_geojson(geometry):
    """Outer ring of a GeoJSON Polygon as a list of (lon, lat), closed."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise GeoError("The field boundary must be a GeoJSON Polygon.")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or not coords or not isinstance(coords[0], list):
        raise GeoError("The field boundary has no coordinates.")
    ring = []
    for pt in coords[0]:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            raise GeoError("Each boundary point needs a longitude and a latitude.")
        lon, lat = float(pt[0]), float(pt[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise GeoError("A boundary point is outside valid latitude and longitude.")
        ring.append((lon, lat))
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    if len(ring) < 4:
        raise GeoError("A field boundary needs at least three corners.")
    return ring


def polygon_area_ha(ring):
    """Geodesic area of a closed ring on a spherical Earth, in hectares.

    Uses the spherical-excess approximation of Chamberlain and Duquette
    ("Some algorithms for polygons on a sphere", NASA JPL, 2007), the same
    method used by common web-mapping libraries.
    """
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:]):
        total += math.radians(lon2 - lon1) * (
            2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return abs(total) * EARTH_RADIUS_M ** 2 / 2 / 10000


def centre(ring):
    """Average of the corners (fine for field-sized polygons)."""
    pts = ring[:-1]
    return (sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts))


def field_from_geojson(geometry):
    """Validated ring, area in hectares and centre (lat, lon)."""
    ring = ring_from_geojson(geometry)
    area = polygon_area_ha(ring)
    if area <= 0.001:
        raise GeoError("The field boundary has no area. Draw at least three separate corners.")
    if area > MAX_FIELD_HA:
        raise GeoError(f"The field boundary covers {area:,.0f} ha, which is too large for one farm.")
    lat, lon = centre(ring)
    return {"ring": ring, "area_ha": area, "lat": lat, "lon": lon}
