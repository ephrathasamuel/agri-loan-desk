import pytest

from app.risk.insurance import design_policy, payout_fraction, percentile


def test_percentile_matches_linear_interpolation():
    xs = [10, 20, 30, 40, 50]
    assert percentile(xs, 0) == 10
    assert percentile(xs, 50) == 30
    assert percentile(xs, 25) == 20
    assert percentile(xs, 10) == pytest.approx(14)
    assert percentile([5], 80) == 5


def test_payout_is_linear_between_trigger_and_exit():
    assert payout_fraction(300, 300, 100) == 0.0
    assert payout_fraction(200, 300, 100) == pytest.approx(0.5)
    assert payout_fraction(100, 300, 100) == 1.0
    assert payout_fraction(50, 300, 100) == 1.0


def seasons():
    # index 100..1000 mm; the two driest years have big losses, plus one
    # bad year with normal rain (late-season drought the index cannot see).
    out = []
    for i, idx in enumerate(range(100, 1001, 100)):
        loss = 0.6 if idx <= 200 else 0.0
        out.append({"year": 2000 + i, "index_rain_mm": float(idx), "yield_loss": loss})
    out[7]["yield_loss"] = 0.3
    return out


def test_premium_is_burning_cost_plus_loading():
    p = design_policy(seasons(), sum_insured_etb=10000, area_ha=2, trigger_pct=30, exit_pct=10,
                      loading=0.25, bad_loss=0.2, false_payout_loss_below=0.1)
    assert p["trigger_mm"] == pytest.approx(370)
    assert p["exit_mm"] == pytest.approx(190)
    expected = sum(payout_fraction(s["index_rain_mm"], 370, 190) for s in seasons()) / 10
    assert p["expected_payout_rate"] == pytest.approx(expected, abs=1e-4)
    assert p["premium_rate"] == pytest.approx(expected * 1.25, abs=1e-4)
    assert p["premium_etb"] == round(p["premium_rate"] * 10000)
    assert p["max_payout_per_ha_etb"] == 5000


def test_basis_risk_is_reported_both_ways():
    p = design_policy(seasons(), sum_insured_etb=10000, area_ha=2, trigger_pct=30, exit_pct=10,
                      loading=0.25, bad_loss=0.2, false_payout_loss_below=0.1)
    assert p["bad_years"] == 3
    assert p["bad_years_paid"] == 2
    assert p["losses_not_covered"] == [2007]
    # 300 mm is below the 370 mm trigger but had no loss.
    assert p["paid_with_small_loss"] == [2002]
    flags = {y["year"]: y["flag"] for y in p["years"]}
    assert flags[2000] == "paid" and flags[2007] == "loss not covered" and flags[2009] == ""
