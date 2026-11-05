"""Climate history with a database cache, so each grid cell is downloaded once."""

import json
import zlib

from sqlalchemy.orm import Session

from .db import ClimateCell
from .risk import climate
from .risk.climate import HISTORY_START, history_end


def _key(lat, lon, end):
    return f"power:{lat:.3f}:{lon:.3f}:{HISTORY_START.isoformat()}:{end.isoformat()}"


def cell_history(db: Session, lat, lon, today=None, fetch=climate.fetch_cell):
    end = history_end(today)
    key = _key(lat, lon, end)
    row = db.get(ClimateCell, key)
    if row is None:
        cell = fetch(lat, lon, HISTORY_START, end)
        row = ClimateCell(
            key=key, lat=lat, lon=lon, elevation=cell["elevation"],
            start=HISTORY_START.isoformat(), end=end.isoformat(),
            payload=zlib.compress(json.dumps(cell).encode()),
        )
        db.merge(row)
        db.commit()
        return cell
    return json.loads(zlib.decompress(row.payload))


def field_daily(db: Session, points, today=None, fetch=climate.fetch_cell):
    """Daily rain and ET0 for a field, averaged over every grid cell its
    corners (and centre) fall in. Returns (daily, cells)."""
    cells = climate.cells_for_points(points)
    dailies = [climate.to_daily(cell_history(db, lat, lon, today, fetch)) for lat, lon in cells]
    return climate.average_daily(dailies), cells


def field_rain(db: Session, lat, lon, today=None, fetch=climate.fetch_rain_era5):
    """ERA5 daily rainfall for the 0.25 deg cell under the field centre, cached like POWER cells."""
    end = history_end(today)
    clat, clon = climate.era5_cell_for(lat, lon)
    key = f"era5:{clat:.2f}:{clon:.2f}:{HISTORY_START.isoformat()}:{end.isoformat()}"
    row = db.get(ClimateCell, key)
    if row is None:
        rain = fetch(clat, clon, HISTORY_START, end)
        db.merge(ClimateCell(key=key, lat=clat, lon=clon, elevation=0.0, start=HISTORY_START.isoformat(),
                             end=end.isoformat(), payload=zlib.compress(json.dumps(rain).encode())))
        db.commit()
        return rain
    return json.loads(zlib.decompress(row.payload))
