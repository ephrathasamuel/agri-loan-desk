import pytest

from app.risk.et0 import et0_penman_monteith, extraterrestrial_radiation, sat_vapour_pressure


def test_saturation_vapour_pressure_matches_fao56_table():
    # FAO-56 Annex 2, Table 2.3
    assert sat_vapour_pressure(21.5) == pytest.approx(2.564, abs=0.002)
    assert sat_vapour_pressure(12.3) == pytest.approx(1.431, abs=0.002)


def test_extraterrestrial_radiation_example_8():
    # FAO-56 Example 8: 20 deg S, 3 September (day 246) -> Ra = 32.2 MJ/m2/day
    assert extraterrestrial_radiation(-20.0, 246) == pytest.approx(32.2, abs=0.2)


def test_daily_et0_example_18_uccle():
    # FAO-56 Example 18: Uccle (Brussels), 6 July, ET0 = 3.9 mm/day.
    # Mean RH chosen so that ea = 1.409 kPa as in the example.
    es = (sat_vapour_pressure(21.5) + sat_vapour_pressure(12.3)) / 2
    rh_mean = 1.409 / es * 100
    et0 = et0_penman_monteith(tmax=21.5, tmin=12.3, rh_mean=rh_mean, u2=2.078, rs=22.07,
                              lat_deg=50.8, elevation_m=100, doy=187)
    assert et0 == pytest.approx(3.9, abs=0.1)


def test_et0_is_never_negative():
    assert et0_penman_monteith(5, -5, 100, 0, 0.5, 60, 0, 355) >= 0
