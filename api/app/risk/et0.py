"""Daily reference evapotranspiration (ET0), FAO-56 Penman-Monteith.

Equation numbers refer to FAO Irrigation and Drainage Paper No. 56 (1998).
Inputs are the daily values NASA POWER provides: maximum and minimum air
temperature (C), mean relative humidity (%), wind speed at 2 m (m/s) and
incoming solar radiation (MJ/m2/day).
"""

import math

SIGMA = 4.903e-9  # Stefan-Boltzmann constant, MJ K-4 m-2 day-1
GSC = 0.0820      # solar constant, MJ m-2 min-1


def sat_vapour_pressure(t):
    """e0(T), kPa (eq. 11)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def extraterrestrial_radiation(lat_deg, doy):
    """Ra, MJ m-2 day-1 (eqs. 21-25)."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * doy)
    delta = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    return (24 * 60 / math.pi) * GSC * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def et0_penman_monteith(tmax, tmin, rh_mean, u2, rs, lat_deg, elevation_m, doy):
    """ET0 in mm/day (eq. 6), with soil heat flux G = 0 for daily steps."""
    t = (tmax + tmin) / 2
    delta = 4098 * sat_vapour_pressure(t) / (t + 237.3) ** 2               # eq. 13
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26          # eq. 7
    gamma = 0.000665 * pressure                                             # eq. 8
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2         # eq. 12
    ea = rh_mean / 100 * es                                                 # eq. 19
    ra = extraterrestrial_radiation(lat_deg, doy)
    rso = (0.75 + 2e-5 * elevation_m) * ra                                  # eq. 37
    rns = (1 - 0.23) * rs                                                   # eq. 38
    ratio = min(rs / rso, 1.0) if rso > 0 else 0.0
    rnl = SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (
        0.34 - 0.14 * math.sqrt(max(ea, 0.0))
    ) * (1.35 * ratio - 0.35)                                               # eq. 39
    rn = rns - rnl                                                          # eq. 40
    num = 0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * (es - ea)
    den = delta + gamma * (1 + 0.34 * u2)
    return max(num / den, 0.0)
