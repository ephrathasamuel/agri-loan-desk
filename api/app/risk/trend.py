"""Is the climate at this field changing? Trends over the season history.

The slope is the Theil-Sen estimate (the median of the slopes between every
pair of years), which one extreme season cannot drag. Whether the trend is
real is judged with the Mann-Kendall test, the usual test for trends in
climate records. Neither needs the data to be normally distributed.
"""

from math import erf, sqrt
from statistics import median

SIGNIFICANCE = 0.10


def theil_sen_slope(years, values):
    slopes = [
        (values[j] - values[i]) / (years[j] - years[i])
        for i in range(len(years))
        for j in range(i + 1, len(years))
        if years[j] != years[i]
    ]
    return median(slopes) if slopes else 0.0


def mann_kendall_p(values):
    """Two-sided p-value of the Mann-Kendall trend test (no tie correction)."""
    n = len(values)
    if n < 3:
        return 1.0
    s = sum(
        (values[j] > values[i]) - (values[j] < values[i])
        for i in range(n)
        for j in range(i + 1, n)
    )
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (s - 1) / sqrt(var) if s > 0 else (s + 1) / sqrt(var) if s < 0 else 0.0
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))


def series_trend(years, values):
    p = mann_kendall_p(values)
    return {"per_decade": round(theil_sen_slope(years, values) * 10, 4),
            "p_value": round(p, 4), "significant": p < SIGNIFICANCE}


def climate_trend(seasons, bad_loss, recent_years):
    """Trends in season rainfall and yield loss, and the recent seasons
    compared with the earlier ones."""
    years = [s["year"] for s in seasons]
    recent = seasons[-recent_years:]
    earlier = seasons[:-recent_years]

    def bad_share(group):
        return round(sum(1 for s in group if s["yield_loss"] >= bad_loss) / len(group), 4) if group else None

    def mean_rain(group):
        return round(sum(s["season_rain_mm"] for s in group) / len(group), 1) if group else None

    return {
        "rain_mm": series_trend(years, [s["season_rain_mm"] for s in seasons]),
        "yield_loss": series_trend(years, [s["yield_loss"] for s in seasons]),
        "recent_from_year": recent[0]["year"],
        "recent_bad_season_share": bad_share(recent),
        "earlier_bad_season_share": bad_share(earlier),
        "recent_mean_rain_mm": mean_rain(recent),
        "earlier_mean_rain_mm": mean_rain(earlier),
        "significance_level": SIGNIFICANCE,
    }
