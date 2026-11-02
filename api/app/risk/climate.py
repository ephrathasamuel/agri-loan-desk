"""Daily weather history from NASA POWER, turned into rainfall and ET0 series.

NASA POWER serves daily data on a grid (MERRA-2, 0.5 deg latitude x 0.625 deg
longitude for rainfall and temperature). Any point inside a grid cell gets the
same values, so data is requested and cached per cell. A field drawn as a
polygon is averaged over every cell it touches.
"""

from datetime import date, timedelta

import requests

from .et0 import et0_penman_monteith

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = "PRECTOTCORR,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN"
# Solar radiation in POWER starts in mid-1983, so the history starts in 1984.
HISTORY_START = date(1984, 1, 1)
LAT_STEP, LON_STEP = 0.5, 0.625
TIMEOUT = 120
FILL = -999.0


class ClimateError(Exception):
    """NASA POWER could not be reached or returned unusable data."""


def history_end(today=None):
    """Last day of the most recent complete year."""
    today = today or date.today()
    return date(today.year - 1, 12, 31)


def cell_for(lat, lon):
    """Centre of the NASA POWER grid cell containing a point."""
    lat_c = round(round(lat / LAT_STEP) * LAT_STEP, 3)
    lon_c = round(round((lon + 180) / LON_STEP) * LON_STEP - 180, 3)
    return lat_c, lon_c


def cells_for_points(points):
    """Distinct grid cells for a list of (lat, lon) points, in a stable order."""
    seen = []
    for lat, lon in points:
        cell = cell_for(lat, lon)
        if cell not in seen:
            seen.append(cell)
    return seen


def fetch_cell(lat, lon, start, end, session=requests):
    """Raw daily series for one grid cell."""
    params = {
        "parameters": PARAMETERS,
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    try:
        res = session.get(POWER_URL, params=params, timeout=TIMEOUT)
        data = res.json()
    except (requests.RequestException, ValueError) as exc:
        raise ClimateError("Could not reach NASA POWER. Check the connection and try again.") from exc
    if res.status_code != 200:
        raise ClimateError(f"NASA POWER returned an error (HTTP {res.status_code}).")
    try:
        values = data["properties"]["parameter"]
        elevation = float(data["geometry"]["coordinates"][2])
        days = sorted(values["PRECTOTCORR"].keys())
        series = {k: [values[k][d] for d in days] for k in values}
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise ClimateError("NASA POWER returned data in an unexpected format.") from exc
    return {"lat": lat, "lon": lon, "elevation": elevation, "start": days[0], "series": series}


def to_daily(cell):
    """date -> {"rain", "et0"} for one cell. Days with missing values are
    skipped here and reported by the caller if a season needs them."""
    s = cell["series"]
    start = date(int(cell["start"][:4]), int(cell["start"][4:6]), int(cell["start"][6:]))
    out = {}
    for i in range(len(s["PRECTOTCORR"])):
        row = {k: s[k][i] for k in s}
        if any(v is None or v <= FILL for v in row.values()):
            continue
        d = start + timedelta(days=i)
        et0 = et0_penman_monteith(
            row["T2M_MAX"], row["T2M_MIN"], row["RH2M"], row["WS2M"], row["ALLSKY_SFC_SW_DWN"],
            cell["lat"], cell["elevation"], d.timetuple().tm_yday,
        )
        out[d] = {"rain": max(row["PRECTOTCORR"], 0.0), "et0": et0}
    return out


def average_daily(dailies):
    """Average several cells' daily series over the days they all have."""
    if len(dailies) == 1:
        return dailies[0]
    common = set(dailies[0]).intersection(*dailies[1:])
    n = len(dailies)
    return {
        d: {
            "rain": sum(x[d]["rain"] for x in dailies) / n,
            "et0": sum(x[d]["et0"] for x in dailies) / n,
        }
        for d in common
    }
