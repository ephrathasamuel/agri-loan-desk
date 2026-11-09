import pytest

from app.risk.trend import climate_trend, mann_kendall_p, theil_sen_slope


def test_theil_sen_ignores_one_outlier():
    years = list(range(2000, 2010))
    values = [2.0 * i for i in range(10)]
    values[4] = 500.0
    assert theil_sen_slope(years, values) == pytest.approx(2.0)


def test_mann_kendall_spots_a_steady_trend_but_not_noise():
    assert mann_kendall_p(list(range(30))) < 0.001
    assert mann_kendall_p([5, 1, 4, 2, 3, 5, 1, 4, 2, 3]) > 0.5


def test_climate_trend_compares_recent_and_earlier_seasons():
    seasons = [{"year": 1990 + i, "season_rain_mm": 600 - 5 * i, "yield_loss": 0.3 if i >= 25 else 0.0}
               for i in range(30)]
    t = climate_trend(seasons, bad_loss=0.2, recent_years=10)
    assert t["rain_mm"]["per_decade"] == pytest.approx(-50)
    assert t["rain_mm"]["significant"]
    assert t["recent_from_year"] == 2010
    assert t["recent_bad_season_share"] == 0.5
    assert t["earlier_bad_season_share"] == 0.0
