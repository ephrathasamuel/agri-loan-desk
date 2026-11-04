// A stand-in for the AI briefing note, used when the API has no ANTHROPIC_API_KEY.
// It follows the same headings the model is asked for, but every sentence is a fixed
// template filled with numbers the risk engine already calculated. Nothing here is AI.
import { day, etb, mm, pct } from "./format";
import type { Assessment } from "./types";

const years = (list: number[]) => (list.length ? list.join(", ") : "none");

export function conceptNote(a: Assessment): string {
  const { climate: c, loan: l, insurance: i, crop, soil, assumptions } = a.result;
  const capacity =
    l.verdict === "Within capacity"
      ? "the farmer could repay even in a bad season"
      : l.verdict === "Repayable in a normal year only"
        ? "the farmer could repay in a normal season, but not in a bad one"
        : "the requested amount is more than a normal season's harvest can repay";

  return [
    "Overall:",
    `- ${crop.name} on ${soil.name.toLowerCase()}, ${a.result.field.area_ha.toFixed(2)} ha. Climate risk is ${c.risk_rating.toLowerCase()}.`,
    `- Loan check: ${l.verdict.toLowerCase()}, meaning ${capacity}.`,
    "",
    "Climate risk:",
    `- ${c.years} seasons simulated (${c.first_year}–${c.last_year}). Median season rain is ${mm(c.median_season_rain_mm)}.`,
    `- ${c.dry_seasons} of ${c.years} seasons were dry (${pct(c.dry_season_share)}). The worst year was ${c.worst_year}, with a ${pct(c.worst_yield_loss)} yield loss.`,
    `- Average yield loss from water stress is ${pct(c.mean_yield_loss)}.`,
    "",
    "Loan:",
    `- Requested ${etb(l.requested_etb)}; ${etb(l.total_due_etb)} due on ${day(l.repayment_due_date)}, including ${etb(l.interest_etb)} interest.`,
    `- Largest loan repayable in a bad year: ${etb(l.max_loan_bad_year_etb)}; in a normal year: ${etb(l.max_loan_normal_year_etb)}.`,
    "",
    "Insurance:",
    `- ${i.index_name}: pays from ${mm(i.trigger_mm)} down to ${mm(i.exit_mm)}. Premium ${etb(i.premium_etb)} (${pct(i.premium_rate, 1)}) on ${etb(i.sum_insured_etb)} insured.`,
    `- It would have paid in ${i.years_paid} of ${i.years_total} years and covered ${i.bad_years_paid} of ${i.bad_years} bad seasons.`,
    `- Bad seasons it would have missed: ${years(i.losses_not_covered)}. Payouts in years with little loss: ${years(i.paid_with_small_loss)}.`,
    "",
    "Assumptions to check:",
    `- Typical yield ${String(assumptions.typical_yield_t_per_ha)} t/ha and price ${etb(Number(assumptions.price_etb_per_quintal))} per quintal drive the money figures.`,
    `- ${pct(Number(assumptions.repayment_share))} of the harvest value is assumed to be available for repayment.`,
    "",
    "Questions to ask the farmer:",
    `- How did the ${c.worst_year} season go, and how was the loan or household managed then?`,
    "- What other income could cover the repayment if this season is dry?",
  ].join("\n");
}
