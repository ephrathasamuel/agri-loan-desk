"""Crop and soil tables for the seasonal water balance.

Agronomic values come from FAO Irrigation and Drainage Paper No. 56
(Allen, Pereira, Raes & Smith, 1998), "Crop evapotranspiration":
  - Kc values: Table 12 (single crop coefficients)
  - Stage lengths: Table 11 (lengths of crop development stages, days)
  - Rooting depth and depletion fraction p: Table 22
  - Soil water held between field capacity and wilting point: Table 19
Yield response factors Ky come from FAO Irrigation and Drainage Paper No. 33
(Doorenbos & Kassam, 1979), "Yield response to water", Table 24 (seasonal Ky).

Where FAO gives a range, the middle of the range is used. Values marked
"approximation" are not in the FAO tables and are stated as such in the app.
"""

# kc: (initial, mid-season, end of late season)
# stages: (initial, development, mid-season, late season) in days
# root_max_m: maximum effective rooting depth in metres
# p: share of total available water the crop can use before it is stressed
# ky: seasonal yield response factor (relative yield loss per relative ET deficit)
# heat_tmax_c: daily maximum (deg C) above which heat around flowering harms the
#   grain. Approximate critical values from the crop heat-stress literature;
#   not FAO table values.
CROPS = {
    "wheat": {
        "name": "Wheat",
        "kc": (0.30, 1.15, 0.25),        # Table 12, spring wheat
        "stages": (20, 25, 60, 30),       # Table 11, spring wheat
        "root_max_m": 1.25,               # Table 22: 1.0-1.5 m
        "p": 0.55,                        # Table 22
        "ky": 1.15,                       # FAO-33 Table 24, spring wheat
        "heat_tmax_c": 34,
        "notes": [],
    },
    "teff": {
        "name": "Teff",
        "kc": (0.30, 1.15, 0.25),         # small grains (Table 12)
        "stages": (15, 25, 50, 30),
        "root_max_m": 0.60,
        "p": 0.55,
        "ky": 1.0,
        "heat_tmax_c": 35,
        "notes": ["Teff is not in the FAO-56 or FAO-33 tables. Small-grain values are used as an "
                  "approximation, with a shorter season and shallower roots, and Ky = 1.0 is assumed."],
    },
    "maize": {
        "name": "Maize",
        "kc": (0.30, 1.20, 0.35),         # Table 12, maize field corn (grain)
        "stages": (30, 40, 50, 30),       # Table 11, maize grain
        "root_max_m": 1.35,               # Table 22: 1.0-1.7 m
        "p": 0.55,                        # Table 22
        "ky": 1.25,                       # FAO-33 Table 24, maize
        "heat_tmax_c": 35,
        "notes": [],
    },
    "sorghum": {
        "name": "Sorghum",
        "kc": (0.30, 1.05, 0.55),         # Table 12, sorghum grain (mid 1.00-1.10)
        "stages": (20, 35, 40, 30),       # Table 11, sorghum grain
        "root_max_m": 1.50,               # Table 22: 1.0-2.0 m
        "p": 0.55,                        # Table 22
        "ky": 0.90,                       # FAO-33 Table 24, sorghum
        "heat_tmax_c": 38,
        "notes": [],
    },
    "barley": {
        "name": "Barley",
        "kc": (0.30, 1.15, 0.25),         # Table 12, barley
        "stages": (15, 25, 50, 30),       # Table 11, barley
        "root_max_m": 1.25,               # Table 22: 1.0-1.5 m
        "p": 0.55,                        # Table 22
        "ky": 1.0,
        "heat_tmax_c": 34,
        "notes": ["Barley has no seasonal Ky in FAO-33 Table 24; Ky = 1.0 is assumed."],
    },
}

# Rooting depth at planting (FAO-56 suggests 0.15-0.20 m).
ROOT_INITIAL_M = 0.20

# Total available water per metre of soil: (field capacity - wilting point) x 1000.
# FAO-56 Table 19 ranges, middle value.
SOILS = {
    "sand":       {"name": "Sand",                 "taw_mm_per_m": 80},
    "sandy_loam": {"name": "Sandy loam",           "taw_mm_per_m": 130},
    "loam":       {"name": "Loam",                 "taw_mm_per_m": 155},
    "clay_loam":  {"name": "Clay loam",            "taw_mm_per_m": 155},
    "clay":       {"name": "Clay (e.g. vertisol)", "taw_mm_per_m": 160},
}


def season_length(crop):
    return sum(crop["stages"])
