"""Weather-index drought insurance, designed and priced from the history.

The index is the rainfall from planting to the end of mid-season. Below the
trigger the policy pays a growing share of the sum insured; at or below the
exit it pays in full. The premium is the average payout over the history
(the "burning cost") plus a loading.
"""


def percentile(values, pct):
    """Linear-interpolation percentile (same as numpy's default)."""
    xs = sorted(values)
    if not xs:
        raise ValueError("no values")
    k = (len(xs) - 1) * pct / 100
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def payout_fraction(index, trigger, exit_):
    if index >= trigger:
        return 0.0
    if index <= exit_:
        return 1.0
    return (trigger - index) / (trigger - exit_)


def design_policy(seasons, sum_insured_etb, area_ha, trigger_pct, exit_pct, loading,
                  bad_loss, false_payout_loss_below):
    """Trigger, exit, premium and a year-by-year backtest.

    seasons: list of {"year", "index_rain_mm", "yield_loss"}.
    """
    index = [s["index_rain_mm"] for s in seasons]
    trigger = percentile(index, trigger_pct)
    exit_ = percentile(index, exit_pct)
    if exit_ >= trigger:  # a flat history: keep a usable payout range
        exit_ = trigger * 0.5

    years = []
    for s in seasons:
        frac = payout_fraction(s["index_rain_mm"], trigger, exit_)
        loss = s["yield_loss"]
        if frac > 0 and loss < false_payout_loss_below:
            flag = "paid, small loss"
        elif frac > 0:
            flag = "paid"
        elif loss >= bad_loss:
            flag = "loss not covered"
        else:
            flag = ""
        years.append({
            "year": s["year"],
            "index_rain_mm": s["index_rain_mm"],
            "payout_fraction": round(frac, 4),
            "payout_etb": round(frac * sum_insured_etb),
            "yield_loss": loss,
            "flag": flag,
        })

    n = len(years)
    expected = sum(y["payout_fraction"] for y in years) / n
    premium_rate = expected * (1 + loading)
    bad_years = [y for y in years if y["yield_loss"] >= bad_loss]
    covered = [y for y in bad_years if y["payout_fraction"] > 0]
    return {
        "index_name": "Rainfall from planting to the end of mid-season",
        "trigger_mm": round(trigger, 1),
        "exit_mm": round(exit_, 1),
        "trigger_percentile": trigger_pct,
        "exit_percentile": exit_pct,
        "sum_insured_etb": round(sum_insured_etb),
        "max_payout_per_ha_etb": round(sum_insured_etb / area_ha) if area_ha else None,
        "expected_payout_rate": round(expected, 4),
        "loading": loading,
        "premium_rate": round(premium_rate, 4),
        "premium_etb": round(premium_rate * sum_insured_etb),
        "years_paid": sum(1 for y in years if y["payout_fraction"] > 0),
        "years_total": n,
        "bad_years": len(bad_years),
        "bad_years_paid": len(covered),
        "losses_not_covered": [y["year"] for y in bad_years if y["payout_fraction"] == 0],
        "paid_with_small_loss": [y["year"] for y in years if y["flag"] == "paid, small loss"],
        "years": years,
    }
