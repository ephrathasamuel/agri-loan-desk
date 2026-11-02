from datetime import date

import pytest
import requests

from app.risk import climate


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


class FakeSession:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.calls = response, exc, []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        if self.exc:
            raise self.exc
        return self.response


def power_payload(days=3):
    keys = [f"202001{d:02d}" for d in range(1, days + 1)]
    def series(v):
        return {k: v for k in keys}
    return {
        "geometry": {"type": "Point", "coordinates": [38.75, 8.5, 2300.0]},
        "properties": {"parameter": {
            "PRECTOTCORR": series(5.0), "T2M_MAX": series(25.0), "T2M_MIN": series(10.0),
            "RH2M": series(60.0), "WS2M": series(2.0), "ALLSKY_SFC_SW_DWN": series(20.0),
        }},
    }


def test_cell_for_snaps_to_the_power_grid():
    assert climate.cell_for(8.75, 38.98) == (9.0, 38.75)
    assert climate.cell_for(8.74, 38.98) == (8.5, 38.75)
    assert climate.cells_for_points([(8.7, 38.9), (8.71, 38.91), (9.3, 38.9)]) == [(8.5, 38.75), (9.5, 38.75)]


def test_fetch_cell_parses_power_json():
    session = FakeSession(FakeResponse(power_payload()))
    cell = climate.fetch_cell(8.5, 38.75, date(2020, 1, 1), date(2020, 1, 3), session=session)
    assert cell["elevation"] == 2300.0
    assert cell["start"] == "20200101"
    assert session.calls[0]["start"] == "20200101" and session.calls[0]["community"] == "AG"
    daily = climate.to_daily(cell)
    assert len(daily) == 3
    assert daily[date(2020, 1, 2)]["rain"] == 5.0
    assert 2.0 < daily[date(2020, 1, 2)]["et0"] < 8.0


def test_missing_values_are_skipped():
    data = power_payload()
    data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]["20200102"] = -999.0
    cell = climate.fetch_cell(8.5, 38.75, date(2020, 1, 1), date(2020, 1, 3),
                              session=FakeSession(FakeResponse(data)))
    assert date(2020, 1, 2) not in climate.to_daily(cell)


@pytest.mark.parametrize("session", [
    FakeSession(exc=requests.ConnectionError("down")),
    FakeSession(FakeResponse({"messages": ["bad"]}, status=422)),
    FakeSession(FakeResponse({"unexpected": True})),
    FakeSession(FakeResponse(ValueError("not json"))),
])
def test_power_failures_raise_climate_error(session):
    with pytest.raises(climate.ClimateError):
        climate.fetch_cell(8.5, 38.75, date(2020, 1, 1), date(2020, 1, 3), session=session)


def test_average_daily_uses_common_days():
    a = {date(2020, 1, 1): {"rain": 2.0, "et0": 4.0}, date(2020, 1, 2): {"rain": 0.0, "et0": 4.0}}
    b = {date(2020, 1, 1): {"rain": 6.0, "et0": 2.0}}
    avg = climate.average_daily([a, b])
    assert avg == {date(2020, 1, 1): {"rain": 4.0, "et0": 3.0}}


def test_history_end_is_last_complete_year():
    assert climate.history_end(date(2026, 11, 2)) == date(2025, 12, 31)
