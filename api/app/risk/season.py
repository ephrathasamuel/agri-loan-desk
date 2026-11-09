"""Rain-fed season simulation: FAO-56 water balance and FAO-33 yield response.

For one season the root-zone depletion is tracked day by day (FAO-56 eq. 85)
with no irrigation. When the soil dries past the readily available water the
crop is stressed (Ks < 1, eq. 84) and transpires less than it could. The
seasonal shortfall of actual against potential crop water use gives the
relative yield loss (FAO-33):  1 - Ya/Ym = Ky (1 - ETa/ETm).

Heat is applied on top: each degree-day of daily maximum above the crop's
critical temperature in the flowering window (the start of mid-season) takes
a fixed share off the water-limited yield.
"""

from datetime import timedelta

from .assumptions import HEAT
from .crops import ROOT_INITIAL_M, season_length

MIN_EFFECTIVE_RAIN_MM = 2.0
EFFECTIVE_RAIN_FRACTION = 0.8
# Before planting the soil is assumed half dry, then 30 days of bare-soil
# drying and rain are simulated so the start reflects that year's rains.
SPIN_UP_DAYS = 30
SPIN_UP_START_DEPLETION = 0.5
BARE_SOIL_KC = 0.30


def crop_stage(crop, das):
    """Stage name, Kc and rooting depth (m) on a day after planting."""
    kc_ini, kc_mid, kc_end = crop["kc"]
    l_ini, l_dev, l_mid, l_late = crop["stages"]
    if das < l_ini:
        stage, kc = "initial", kc_ini
    elif das < l_ini + l_dev:
        stage, kc = "development", kc_ini + (das - l_ini) / l_dev * (kc_mid - kc_ini)
    elif das < l_ini + l_dev + l_mid:
        stage, kc = "mid-season", kc_mid
    else:
        stage = "late season"
        kc = kc_mid + (das - l_ini - l_dev - l_mid) / l_late * (kc_end - kc_mid)
    root = ROOT_INITIAL_M + min(das / (l_ini + l_dev), 1.0) * (crop["root_max_m"] - ROOT_INITIAL_M)
    return stage, kc, root


def effective_rain(rain_mm):
    if rain_mm < MIN_EFFECTIVE_RAIN_MM:
        return 0.0
    return EFFECTIVE_RAIN_FRACTION * rain_mm


def stress_coefficient(depletion, taw, raw):
    """Ks (FAO-56 eq. 84)."""
    if depletion <= raw:
        return 1.0
    if taw <= raw:
        return 0.0
    return max(0.0, (taw - depletion) / (taw - raw))


def index_window_days(crop):
    """Days from planting to the end of mid-season: the water-sensitive part of
    the season that the insurance rainfall index covers."""
    l_ini, l_dev, l_mid, _ = crop["stages"]
    return l_ini + l_dev + l_mid


def flowering_window(crop):
    """(first, last + 1) day after planting of the flowering window."""
    l_ini, l_dev, l_mid, _ = crop["stages"]
    start = l_ini + l_dev
    return start, start + min(HEAT["flowering_days"], l_mid)


def simulate_season(daily, crop, taw_per_m, planting):
    """Simulate one rain-fed season.

    daily: dict date -> {"rain": mm, "et0": mm, "tmax": deg C (optional)}; must cover the spin-up days
    before planting and the whole season.
    Returns season totals and the relative yield (0-1).
    """
    # Pre-season: bare soil over the planting root depth.
    taw0 = taw_per_m * ROOT_INITIAL_M
    depletion = SPIN_UP_START_DEPLETION * taw0
    for i in range(SPIN_UP_DAYS, 0, -1):
        d = daily[planting - timedelta(days=i)]
        ks = stress_coefficient(depletion, taw0, 0.5 * taw0)
        depletion = min(max(depletion - effective_rain(d["rain"]) + ks * BARE_SOIL_KC * d["et0"], 0.0), taw0)

    length = season_length(crop)
    window = index_window_days(crop)
    flower_start, flower_end = flowering_window(crop)
    eta = etm = rain = index_rain = heat_degree_days = 0.0
    stress_days = heat_days = 0
    for das in range(length):
        d = daily[planting + timedelta(days=das)]
        _, kc, root = crop_stage(crop, das)
        taw = taw_per_m * root
        raw = crop["p"] * taw
        ks = stress_coefficient(depletion, taw, raw)
        potential = kc * d["et0"]
        actual = ks * potential
        depletion = min(max(depletion - effective_rain(d["rain"]) + actual, 0.0), taw)
        eta += actual
        etm += potential
        rain += d["rain"]
        if das < window:
            index_rain += d["rain"]
        if ks < 1.0:
            stress_days += 1
        excess = (d.get("tmax") or 0.0) - crop["heat_tmax_c"]
        if flower_start <= das < flower_end and excess > 0:
            heat_days += 1
            heat_degree_days += excess

    deficit = 1 - eta / etm if etm > 0 else 0.0
    water_yield = max(0.0, 1 - crop["ky"] * deficit)
    heat_loss = min(1.0, HEAT["loss_per_degree_day"] * heat_degree_days)
    relative_yield = water_yield * (1 - heat_loss)
    return {
        "season_rain_mm": round(rain, 1),
        "index_rain_mm": round(index_rain, 1),
        "etm_mm": round(etm, 1),
        "eta_mm": round(eta, 1),
        "stress_days": stress_days,
        "heat_days": heat_days,
        "water_yield_loss": round(1 - water_yield, 4),
        "heat_yield_loss": round(heat_loss, 4),
        "relative_yield": round(relative_yield, 4),
        "yield_loss": round(1 - relative_yield, 4),
    }
