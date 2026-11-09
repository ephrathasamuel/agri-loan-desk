"""Put the pieces together: climate history -> seasons -> loan -> insurance."""

from datetime import date, timedelta

from . import assumptions as A
from .crops import CROPS, SOILS, season_length
from .insurance import design_policy, percentile
from .season import SPIN_UP_DAYS, simulate_season
from .trend import climate_trend

MIN_YEARS = 20


class AssessmentError(ValueError):
    pass


def _safe_date(year, month, day):
    # 29 February in a non-leap year becomes 28 February.
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, day - 1)


def historical_seasons(daily, crop, taw_per_m, month, day):
    """Simulate the season for every year the history fully covers."""
    if not daily:
        raise AssessmentError("No weather history is available for this location.")
    first, last = min(daily), max(daily)
    length = season_length(crop)
    out = []
    for year in range(first.year, last.year + 1):
        planting = _safe_date(year, month, day)
        start = planting - timedelta(days=SPIN_UP_DAYS)
        end = planting + timedelta(days=length - 1)
        if start < first or end > last:
            continue
        needed = (start + timedelta(days=i) for i in range((end - start).days + 1))
        if any(d not in daily for d in needed):
            continue  # a gap in the data: skip the year rather than guess
        result = simulate_season(daily, crop, taw_per_m, planting)
        out.append({"year": year, "planting": planting.isoformat(), **result})
    if len(out) < MIN_YEARS:
        raise AssessmentError(
            f"Only {len(out)} complete seasons are available; at least {MIN_YEARS} are needed."
        )
    return out


def risk_rating(p_bad):
    if p_bad < 0.10:
        return "Low"
    if p_bad < 0.25:
        return "Medium"
    return "High"


def next_planting(month, day, today):
    planting = _safe_date(today.year, month, day)
    if planting < today:
        planting = _safe_date(today.year + 1, month, day)
    return planting


def loan_terms(inputs, crop, yield_t, price, ratios, today):
    lend = A.LENDING
    planting = next_planting(inputs["planting_month"], inputs["planting_day"], today)
    disbursement = planting - timedelta(days=lend["disbursement_days_before_planting"])
    harvest = planting + timedelta(days=season_length(crop))
    due = harvest + timedelta(days=lend["grace_days_after_harvest"])
    term_days = (due - disbursement).days
    rate = lend["annual_interest_rate"]
    growth = 1 + rate * term_days / 365

    def capacity(ratio):
        revenue = inputs["area_ha"] * yield_t * ratio * 10 * price  # 10 quintals per tonne
        return revenue, revenue * lend["repayment_share"] / growth

    bad_ratio = percentile(ratios, lend["bad_year_percentile"])
    normal_ratio = percentile(ratios, 50)
    bad_revenue, max_bad = capacity(bad_ratio)
    normal_revenue, max_normal = capacity(normal_ratio)

    requested = inputs["loan_amount_etb"]
    if requested <= max_bad:
        verdict = "Within capacity"
    elif requested <= max_normal:
        verdict = "Repayable in a normal year only"
    else:
        verdict = "Above capacity"

    return {
        "requested_etb": round(requested),
        "disbursement_date": disbursement.isoformat(),
        "planting_date": planting.isoformat(),
        "harvest_date": harvest.isoformat(),
        "repayment_due_date": due.isoformat(),
        "term_days": term_days,
        "annual_interest_rate": rate,
        "interest_etb": round(requested * (growth - 1)),
        "total_due_etb": round(requested * growth),
        "bad_year_percentile": lend["bad_year_percentile"],
        "bad_year_relative_yield": round(bad_ratio, 4),
        "normal_year_relative_yield": round(normal_ratio, 4),
        "bad_year_harvest_value_etb": round(bad_revenue),
        "normal_year_harvest_value_etb": round(normal_revenue),
        "repayment_share": lend["repayment_share"],
        "max_loan_bad_year_etb": round(max_bad),
        "max_loan_normal_year_etb": round(max_normal),
        "verdict": verdict,
    }


def assess(inputs, daily, today=None):
    """Full assessment from validated inputs and a daily weather history.

    inputs: crop, soil, planting_month, planting_day, area_ha, loan_amount_etb,
    and optional typical_yield_t_per_ha, price_etb_per_quintal,
    trigger_percentile, exit_percentile.
    """
    today = today or date.today()
    crop = CROPS[inputs["crop"]]
    soil = SOILS[inputs["soil"]]
    seasons = historical_seasons(daily, crop, soil["taw_mm_per_m"],
                                 inputs["planting_month"], inputs["planting_day"])

    rains = [s["season_rain_mm"] for s in seasons]
    ratios = [s["relative_yield"] for s in seasons]
    median_rain = percentile(rains, 50)
    dry_limit = A.RISK["dry_season_share_of_median"] * median_rain
    bad_loss = A.RISK["bad_loss_threshold"]
    for s in seasons:
        s["dry"] = s["season_rain_mm"] < dry_limit
        s["rain_share_of_median"] = round(s["season_rain_mm"] / median_rain, 3) if median_rain else None
    p_bad = sum(1 for s in seasons if s["yield_loss"] >= bad_loss) / len(seasons)
    dry = [s for s in seasons if s["dry"]]
    hot = [s for s in seasons if s["heat_yield_loss"] > 0]

    climate = {
        "years": len(seasons),
        "first_year": seasons[0]["year"],
        "last_year": seasons[-1]["year"],
        "median_season_rain_mm": round(median_rain, 1),
        "dry_limit_mm": round(dry_limit, 1),
        "dry_seasons": len(dry),
        "dry_season_share": round(len(dry) / len(seasons), 4),
        "mean_yield_loss": round(sum(s["yield_loss"] for s in seasons) / len(seasons), 4),
        "mean_yield_loss_dry_seasons": round(sum(s["yield_loss"] for s in dry) / len(dry), 4) if dry else None,
        "worst_year": max(seasons, key=lambda s: s["yield_loss"])["year"],
        "worst_yield_loss": max(s["yield_loss"] for s in seasons),
        "bad_season_share": round(p_bad, 4),
        "bad_loss_threshold": bad_loss,
        "risk_rating": risk_rating(p_bad),
        "heat_seasons": len(hot),
        "mean_heat_yield_loss": round(sum(s["heat_yield_loss"] for s in seasons) / len(seasons), 4),
        "trend": climate_trend(seasons, bad_loss, A.RISK["recent_years"]),
        "seasons": seasons,
    }

    yield_t = inputs.get("typical_yield_t_per_ha") or A.TYPICAL_YIELD_T_PER_HA[inputs["crop"]]
    price = inputs.get("price_etb_per_quintal") or A.PRICE_ETB_PER_QUINTAL[inputs["crop"]]
    loan = loan_terms(inputs, crop, yield_t, price, ratios, today)

    ins = A.INSURANCE
    insurance = design_policy(
        seasons,
        sum_insured_etb=inputs["loan_amount_etb"],
        area_ha=inputs["area_ha"],
        trigger_pct=inputs.get("trigger_percentile") or ins["trigger_percentile"],
        exit_pct=inputs.get("exit_percentile") or ins["exit_percentile"],
        loading=ins["loading"],
        bad_loss=bad_loss,
        false_payout_loss_below=ins["false_payout_loss_below"],
    )

    used = {
        "typical_yield_t_per_ha": yield_t,
        "typical_yield_source": "officer" if inputs.get("typical_yield_t_per_ha") else "default assumption",
        "price_etb_per_quintal": price,
        "price_source": "officer" if inputs.get("price_etb_per_quintal") else "default assumption",
        "repayment_share": A.LENDING["repayment_share"],
        "annual_interest_rate": A.LENDING["annual_interest_rate"],
        "disbursement_days_before_planting": A.LENDING["disbursement_days_before_planting"],
        "grace_days_after_harvest": A.LENDING["grace_days_after_harvest"],
        "insurance_loading": ins["loading"],
        "dry_season_share_of_median": A.RISK["dry_season_share_of_median"],
        "heat_tmax_c": crop["heat_tmax_c"],
        "heat_flowering_days": A.HEAT["flowering_days"],
        "heat_loss_per_degree_day": A.HEAT["loss_per_degree_day"],
    }

    return {
        "crop": {"key": inputs["crop"], "name": crop["name"], "season_days": season_length(crop),
                 "ky": crop["ky"], "heat_tmax_c": crop["heat_tmax_c"], "notes": crop["notes"]},
        "soil": {"key": inputs["soil"], "name": soil["name"]},
        "climate": climate,
        "loan": loan,
        "insurance": insurance,
        "assumptions": used,
    }
