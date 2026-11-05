"""Daily weather history, turned into rainfall and ET0 series.

NASA POWER serves daily data on a grid (MERRA-2, 0.5 deg latitude x 0.625 deg
longitude). Its temperature, humidity, wind and solar radiation drive ET0, and
it is requested and cached per cell; a field drawn as a polygon is averaged
over every cell it touches.

Rainfall comes from the ECMWF ERA5 reanalysis through the Open-Meteo archive
(0.25 deg, about 28 km): each cell covers about a fifth of the area of a POWER
cell, so local dry spells are smoothed less. If ERA5 cannot be reached, POWER
rainfall is used instead.
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


ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
ERA5_STEP = 0.25


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


def era5_cell_for(lat, lon):
    """Centre of the 0.25 deg ERA5 cell containing a point."""
    return round(round(lat / ERA5_STEP) * ERA5_STEP, 2), round(round(lon / ERA5_STEP) * ERA5_STEP, 2)


def fetch_rain_era5(lat, lon, start, end, session=requests):
    """Daily rainfall (mm) from ERA5 for one 0.25 deg cell: {"YYYY-MM-DD": mm}."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "precipitation_sum",
        "models": "era5",
        "timezone": "UTC",
    }
    try:
        res = session.get(ERA5_URL, params=params, timeout=TIMEOUT)
        data = res.json()
    except (requests.RequestException, ValueError) as exc:
        raise ClimateError("Could not reach the ERA5 rainfall archive.") from exc
    if res.status_code != 200:
        raise ClimateError(f"The ERA5 archive returned an error (HTTP {res.status_code}).")
    try:
        days, rain = data["daily"]["time"], data["daily"]["precipitation_sum"]
    except (KeyError, TypeError) as exc:
        raise ClimateError("The ERA5 archive returned data in an unexpected format.") from exc
    return {d: max(float(r), 0.0) for d, r in zip(days, rain) if r is not None}


def with_rain(daily, rain):
    """Replace the rainfall in a daily series with another source, on the days both have."""
    return {d: {**v, "rain": rain[d.isoformat()]} for d, v in daily.items() if d.isoformat() in rain}
