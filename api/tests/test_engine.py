from datetime import date

import pytest

from app.risk import assumptions as A
from app.risk.engine import AssessmentError, assess, historical_seasons, next_planting
from app.risk.crops import CROPS

TODAY = date(2026, 11, 2)
BASE = {"crop": "wheat", "soil": "loam", "planting_month": 6, "planting_day": 15,
        "area_ha": 2.0, "loan_amount_etb": 20000}


def test_every_complete_year_is_simulated(daily):
    seasons = historical_seasons(daily, CROPS["wheat"], 155, 6, 15)
    assert [s["year"] for s in seasons] == list(range(1984, 2026))


def test_seasons_crossing_the_end_of_data_are_skipped(daily):
    # Planted 1 December: the 2025 season would end in 2026, after the data.
    seasons = historical_seasons(daily, CROPS["wheat"], 155, 12, 1)
    assert seasons[-1]["year"] == 2024


def test_too_little_history_is_an_error(daily):
    short = {d: v for d, v in daily.items() if d.year >= 2015}
    with pytest.raises(AssessmentError):
        historical_seasons(short, CROPS["wheat"], 155, 6, 15)


def test_dry_years_show_up_as_dry_and_lossy(daily):
    r = assess(BASE, daily, today=TODAY)
    by_year = {s["year"]: s for s in r["climate"]["seasons"]}
    for y in (1990, 2002, 2015):
        assert by_year[y]["dry"]
        assert by_year[y]["yield_loss"] > 0.2
    assert r["climate"]["dry_seasons"] == 3
    assert r["climate"]["bad_season_share"] == pytest.approx(3 / 42, abs=1e-4)
    assert r["climate"]["risk_rating"] == "Low"


def test_loan_dates_follow_the_crop_calendar(daily):
    loan = assess(BASE, daily, today=TODAY)["loan"]
    # 15 June 2026 has passed, so the next season is 2027.
    assert loan["planting_date"] == "2027-06-15"
    assert loan["disbursement_date"] == "2027-06-01"
    assert loan["harvest_date"] == "2027-10-28"     # + 135 days for wheat
    assert loan["repayment_due_date"] == "2027-11-27"  # + 30 days grace
    assert loan["term_days"] == 179


def test_loan_capacity_and_verdict(daily):
    r = assess(BASE, daily, today=TODAY)
    loan = r["loan"]
    growth = 1 + A.LENDING["annual_interest_rate"] * loan["term_days"] / 365
    revenue = 2.0 * A.TYPICAL_YIELD_T_PER_HA["wheat"] * loan["bad_year_relative_yield"] * 10 * A.PRICE_ETB_PER_QUINTAL["wheat"]
    assert loan["max_loan_bad_year_etb"] == round(revenue * A.LENDING["repayment_share"] / growth)
    assert loan["verdict"] == "Within capacity"
    assert loan["total_due_etb"] == round(20000 * growth)

    big = assess({**BASE, "loan_amount_etb": loan["max_loan_normal_year_etb"] * 2}, daily, today=TODAY)
    assert big["loan"]["verdict"] == "Above capacity"


def test_officer_overrides_are_used_and_labelled(daily):
    r = assess({**BASE, "typical_yield_t_per_ha": 4.0, "price_etb_per_quintal": 7000}, daily, today=TODAY)
    assert r["assumptions"]["typical_yield_t_per_ha"] == 4.0
    assert r["assumptions"]["typical_yield_source"] == "officer"
    assert r["assumptions"]["price_source"] == "officer"
    default = assess(BASE, daily, today=TODAY)
    assert default["assumptions"]["price_source"] == "default assumption"
    assert r["loan"]["max_loan_bad_year_etb"] > default["loan"]["max_loan_bad_year_etb"]


def test_insurance_pays_in_the_dry_years(daily):
    ins = assess(BASE, daily, today=TODAY)["insurance"]
    paid = {y["year"] for y in ins["years"] if y["payout_fraction"] > 0}
    assert {1990, 2002, 2015} <= paid
    assert ins["sum_insured_etb"] == 20000
    assert ins["max_payout_per_ha_etb"] == 10000


def test_next_planting_today_counts_as_this_year():
    assert next_planting(11, 2, TODAY) == date(2026, 11, 2)
    assert next_planting(11, 1, TODAY) == date(2027, 11, 1)
