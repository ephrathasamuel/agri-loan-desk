"""Editable business assumptions.

These numbers are NOT measured facts. They are starting values a lender is
expected to replace with its own data (local yields, current market prices,
its own lending terms). The app shows every one of them next to the results,
labelled as an assumption.
"""

# Typical yield in a season with no water stress, tonnes per hectare.
# Assumption: rounded from the national averages reported in the Ethiopian
# Statistics Service (CSA) Agricultural Sample Surveys of the early 2020s.
# Replace with yields for the woreda and the farmer's own records.
TYPICAL_YIELD_T_PER_HA = {
    "wheat": 3.0,
    "teff": 1.9,
    "maize": 4.2,
    "sorghum": 2.9,
    "barley": 2.5,
}

# Farm-gate price, Ethiopian birr per quintal (100 kg).
# Assumption: placeholder values for illustration. Prices change quickly;
# set these to the current local market price before relying on the result.
PRICE_ETB_PER_QUINTAL = {
    "wheat": 6000,
    "teff": 12000,
    "maize": 4000,
    "sorghum": 5000,
    "barley": 6000,
}

LENDING = {
    # Share of the harvest value the household can put towards the loan;
    # the rest goes to food, other costs and savings. Assumption.
    "repayment_share": 0.40,
    # Annual interest rate, flat on the principal for the loan term. Assumption.
    "annual_interest_rate": 0.18,
    # Days before planting the loan is paid out (to buy seed and fertiliser). Assumption.
    "disbursement_days_before_planting": 14,
    # Days after harvest the single repayment falls due (time to sell). Assumption.
    "grace_days_after_harvest": 30,
    # The "bad year" the loan should still be repayable in: the yield exceeded
    # in 4 of 5 years (1-in-5 bad year).
    "bad_year_percentile": 20,
}

RISK = {
    # A season is "dry" when its rainfall is below this share of the median.
    "dry_season_share_of_median": 0.75,
    # A yield loss at or above this share counts as a bad season.
    "bad_loss_threshold": 0.20,
}

INSURANCE = {
    # Index trigger and exit as percentiles of the historical index.
    # Below the trigger the policy starts paying; at or below the exit it pays in full.
    "trigger_percentile": 20,
    "exit_percentile": 5,
    # Premium = expected payout x (1 + loading). The loading covers costs and
    # uncertainty. Assumption.
    "loading": 0.25,
    # A payout year with a yield loss below this share is counted as a
    # possible false payout (basis risk the other way).
    "false_payout_loss_below": 0.10,
}


def as_dict():
    return {
        "typical_yield_t_per_ha": TYPICAL_YIELD_T_PER_HA,
        "price_etb_per_quintal": PRICE_ETB_PER_QUINTAL,
        "lending": LENDING,
        "risk": RISK,
        "insurance": INSURANCE,
    }
