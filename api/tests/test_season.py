from datetime import date, timedelta

import pytest

from app.risk.assumptions import HEAT
from app.risk.crops import CROPS, ROOT_INITIAL_M, season_length
from app.risk.season import (crop_stage, effective_rain, flowering_window, index_window_days,
                             simulate_season, stress_coefficient)

WHEAT = CROPS["wheat"]
PLANTING = date(2020, 7, 1)


def flat_weather(rain, et0=4.0):
    start = PLANTING - timedelta(days=40)
    return {start + timedelta(days=i): {"rain": rain, "et0": et0} for i in range(220)}


def test_crop_stage_follows_fao56_curve():
    assert crop_stage(WHEAT, 0) == ("initial", 0.30, ROOT_INITIAL_M)
    stage, kc, _ = crop_stage(WHEAT, 20 + 12.5)  # half-way through development
    assert stage == "development" and kc == pytest.approx((0.30 + 1.15) / 2)
    stage, kc, root = crop_stage(WHEAT, 50)
    assert stage == "mid-season" and kc == 1.15 and root == pytest.approx(1.25)
    stage, kc, _ = crop_stage(WHEAT, season_length(WHEAT) - 1)
    assert stage == "late season" and 0.25 < kc < 1.15


def test_effective_rain_ignores_small_showers():
    assert effective_rain(1.5) == 0.0
    assert effective_rain(10) == pytest.approx(8.0)


def test_stress_coefficient():
    assert stress_coefficient(10, 100, 50) == 1.0
    assert stress_coefficient(75, 100, 50) == pytest.approx(0.5)
    assert stress_coefficient(100, 100, 50) == 0.0


def test_wet_season_has_no_yield_loss():
    result = simulate_season(flat_weather(rain=10), WHEAT, 155, PLANTING)
    assert result["yield_loss"] == 0.0
    assert result["stress_days"] == 0
    assert result["eta_mm"] == result["etm_mm"]


def test_no_rain_gives_large_loss_by_fao33():
    result = simulate_season(flat_weather(rain=0), WHEAT, 155, PLANTING)
    deficit = 1 - result["eta_mm"] / result["etm_mm"]
    assert result["yield_loss"] == pytest.approx(min(1.0, WHEAT["ky"] * deficit), abs=1e-3)
    assert result["yield_loss"] > 0.5
    assert result["index_rain_mm"] == 0.0


def test_index_window_ends_with_mid_season():
    assert index_window_days(WHEAT) == 20 + 25 + 60
    result = simulate_season(flat_weather(rain=3), WHEAT, 155, PLANTING)
    assert result["index_rain_mm"] == pytest.approx(3 * index_window_days(WHEAT))
    assert result["season_rain_mm"] == pytest.approx(3 * season_length(WHEAT))


def test_heat_at_flowering_cuts_yield():
    weather = flat_weather(rain=10)
    start, end = flowering_window(WHEAT)
    for das in range(start, start + 3):  # three days 2 degrees over the limit
        weather[PLANTING + timedelta(days=das)]["tmax"] = WHEAT["heat_tmax_c"] + 2
    result = simulate_season(weather, WHEAT, 155, PLANTING)
    assert result["heat_days"] == 3
    assert result["heat_yield_loss"] == pytest.approx(6 * HEAT["loss_per_degree_day"])
    assert result["yield_loss"] == pytest.approx(result["heat_yield_loss"], abs=1e-4)


def test_heat_outside_flowering_is_ignored():
    weather = flat_weather(rain=10)
    weather[PLANTING + timedelta(days=5)]["tmax"] = WHEAT["heat_tmax_c"] + 5
    result = simulate_season(weather, WHEAT, 155, PLANTING)
    assert result["heat_days"] == 0 and result["heat_yield_loss"] == 0
