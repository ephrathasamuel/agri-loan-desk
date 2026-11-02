import Link from "next/link";
import { notFound } from "next/navigation";
import { PayoutChart, SeasonRainChart, YieldLossChart } from "@/components/Charts";
import { ApiError, getAssessment, getReference } from "@/lib/api";
import { day, etb, mm, pct, riskClass, verdictClass, when } from "@/lib/format";
import type { Assessment } from "@/lib/types";
import { ResultMap, SummaryForm } from "./ClientParts";

export async function generateMetadata({ params }: PageProps<"/assessments/[id]">) {
  const { id } = await params;
  return { title: `Assessment #${id} · Agri-Loan Climate Risk Desk` };
}

function Stat({ label, value, sub, testId }: { label: string; value: React.ReactNode; sub?: React.ReactNode; testId?: string }) {
  return (
    <div className="card" data-testid={testId}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub ? <div className="mt-1 text-xs text-muted">{sub}</div> : null}
    </div>
  );
}

function Section({ title, intro, children, id }: { title: string; intro?: string; children: React.ReactNode; id?: string }) {
  return (
    <section className="card space-y-4" id={id}>
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        {intro ? <p className="mt-1 text-sm text-muted">{intro}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Swatch({ colour, label }: { colour: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: colour }} />
      {label}
    </span>
  );
}

export default async function AssessmentPage({ params }: PageProps<"/assessments/[id]">) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  let a: Assessment;
  try {
    a = await getAssessment(id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const { aiAvailable } = await getReference().then((r) => ({ aiAvailable: r.ai_available }));
  const { climate, loan, insurance, crop, soil, field, assumptions } = a.result;
  const timeline = [
    ["Loan paid out", loan.disbursement_date],
    ["Planting", loan.planting_date],
    ["Expected harvest", loan.harvest_date],
    ["Repayment due", loan.repayment_due_date],
  ] as const;
  const payoutYears = insurance.years.filter((y) => y.payout_fraction > 0 || y.flag);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/assessments" className="text-sm text-muted hover:underline">← All assessments</Link>
          <h1 className="mt-1 text-2xl font-semibold" data-testid="farmer-name">{a.farmer_name}</h1>
          <p className="text-sm text-muted">
            {a.farmer_ref ? `${a.farmer_ref} · ` : ""}{crop.name} on {soil.name.toLowerCase()} ·{" "}
            {field.area_ha.toFixed(2)} ha {field.area_source === "boundary" ? "(measured from boundary)" : "(entered)"} ·{" "}
            {field.lat.toFixed(4)}, {field.lon.toFixed(4)}
          </p>
          <p className="text-xs text-muted">Assessed {when(a.created_at)} by {a.created_by}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`rounded-full px-3 py-1 text-sm font-medium ring-1 ${riskClass[a.risk_rating]}`} data-testid="risk-badge">
            {a.risk_rating} climate risk
          </span>
          <span className={`rounded-full px-3 py-1 text-sm font-medium ring-1 ${verdictClass(loan.verdict)}`} data-testid="verdict-badge">
            {loan.verdict}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Bad seasons" testId="stat-bad"
          value={pct(climate.bad_season_share)}
          sub={`${Math.round(climate.bad_season_share * climate.years)} of ${climate.years} seasons lost ≥ ${pct(climate.bad_loss_threshold)} of yield`} />
        <Stat label="Max loan, 1-in-5 bad year" testId="stat-maxloan"
          value={etb(loan.max_loan_bad_year_etb)}
          sub={<>Requested {etb(loan.requested_etb)}</>} />
        <Stat label="Drought cover premium" testId="stat-premium"
          value={etb(insurance.premium_etb)}
          sub={`${pct(insurance.premium_rate, 1)} of ${etb(insurance.sum_insured_etb)} insured`} />
        <Stat label="Repayment due" value={day(loan.repayment_due_date)}
          sub={`${etb(loan.total_due_etb)} incl. interest`} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <Section title="Field and data" intro="The field as drawn, and the NASA POWER grid cells its daily weather history comes from.">
          <ResultMap lat={field.lat} lon={field.lon} boundary={a.boundary} cells={climate.cells} />
          <p className="text-xs text-muted">
            {climate.source}. {climate.years} complete seasons, {climate.first_year}–{climate.last_year}
            {climate.cells.length > 1 ? `, averaged over ${climate.cells.length} grid cells` : ""}.
          </p>
        </Section>

        <Section title="Loan structure" intro="Repayment is timed after the expected harvest. Capacity is what the harvest can repay in a bad year.">
          <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {timeline.map(([label, d], i) => (
              <li key={label} className="rounded-lg bg-brand-50 px-3 py-2">
                <div className="text-xs text-muted">{i + 1}. {label}</div>
                <div className="text-sm font-semibold">{day(d)}</div>
              </li>
            ))}
          </ol>
          <table className="table">
            <tbody>
              <tr><td>Requested loan</td><td className="text-right font-medium tabular-nums">{etb(loan.requested_etb)}</td></tr>
              <tr><td>Interest ({pct(loan.annual_interest_rate)} a year, {loan.term_days} days)</td><td className="text-right tabular-nums">{etb(loan.interest_etb)}</td></tr>
              <tr>
                <td>Harvest value in a 1-in-5 bad year <span className="text-muted">({pct(loan.bad_year_relative_yield)} of a normal crop)</span></td>
                <td className="text-right tabular-nums">{etb(loan.bad_year_harvest_value_etb)}</td>
              </tr>
              <tr>
                <td>Harvest value in a median year <span className="text-muted">({pct(loan.normal_year_relative_yield)})</span></td>
                <td className="text-right tabular-nums">{etb(loan.normal_year_harvest_value_etb)}</td>
              </tr>
              <tr><td>Max loan, bad year <span className="text-muted">({pct(loan.repayment_share)} of harvest value)</span></td><td className="text-right font-semibold tabular-nums">{etb(loan.max_loan_bad_year_etb)}</td></tr>
              <tr><td>Max loan, median year</td><td className="text-right tabular-nums">{etb(loan.max_loan_normal_year_etb)}</td></tr>
            </tbody>
          </table>
        </Section>
      </div>

      <Section title="Climate risk for this field"
        intro={`The ${crop.name.toLowerCase()} season replayed with each year's real weather since ${climate.first_year}, using the FAO-56 soil water balance and the FAO-33 yield response (Ky ${crop.ky}).`}>
        <div className="grid gap-3 text-sm sm:grid-cols-4">
          <div><div className="stat-label">Median season rain</div><div className="font-semibold">{mm(climate.median_season_rain_mm)}</div></div>
          <div><div className="stat-label">Dry seasons</div><div className="font-semibold">{climate.dry_seasons} of {climate.years} ({pct(climate.dry_season_share)})</div></div>
          <div><div className="stat-label">Average yield loss</div><div className="font-semibold">{pct(climate.mean_yield_loss, 1)}{climate.mean_yield_loss_dry_seasons !== null ? <span className="font-normal text-muted"> · {pct(climate.mean_yield_loss_dry_seasons, 1)} in dry seasons</span> : null}</div></div>
          <div><div className="stat-label">Worst season</div><div className="font-semibold">{climate.worst_year}: {pct(climate.worst_yield_loss)} loss</div></div>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <h3 className="mb-1 text-sm font-semibold">Season rainfall</h3>
            <div className="mb-1 flex gap-3 text-xs text-muted">
              <Swatch colour="#3b82f6" label="normal" />
              <Swatch colour="#f59e0b" label={`dry (below ${mm(climate.dry_limit_mm)})`} />
            </div>
            <SeasonRainChart seasons={climate.seasons} median={climate.median_season_rain_mm} dryLimit={climate.dry_limit_mm} />
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold">Estimated yield loss from water stress</h3>
            <div className="mb-1 flex gap-3 text-xs text-muted">
              <Swatch colour="#dc2626" label={`bad season (≥ ${pct(climate.bad_loss_threshold)})`} />
            </div>
            <YieldLossChart seasons={climate.seasons} badThreshold={climate.bad_loss_threshold} />
          </div>
        </div>
        {crop.notes.map((n) => <p key={n} className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">{n}</p>)}
      </Section>

      <Section title="Weather-index drought insurance"
        intro={`${insurance.index_name}. Below the trigger the policy pays part of the sum insured, rising to the full amount at the exit. Priced from the ${insurance.years_total}-year backtest.`}>
        <div className="grid gap-3 text-sm sm:grid-cols-4">
          <div><div className="stat-label">Trigger</div><div className="font-semibold">{mm(insurance.trigger_mm)}</div><div className="text-xs text-muted">{insurance.trigger_percentile}th percentile</div></div>
          <div><div className="stat-label">Full payout at</div><div className="font-semibold">{mm(insurance.exit_mm)}</div><div className="text-xs text-muted">{insurance.exit_percentile}th percentile</div></div>
          <div><div className="stat-label">Premium</div><div className="font-semibold">{pct(insurance.premium_rate, 1)} · {etb(insurance.premium_etb)}</div><div className="text-xs text-muted">average payout {pct(insurance.expected_payout_rate, 1)} + {pct(insurance.loading)} loading</div></div>
          <div><div className="stat-label">Max payout</div><div className="font-semibold">{insurance.max_payout_per_ha_etb !== null ? `${etb(insurance.max_payout_per_ha_etb)} / ha` : "–"}</div></div>
        </div>
        <div>
          <div className="mb-1 flex flex-wrap gap-3 text-xs text-muted">
            <Swatch colour="#16a34a" label="would have paid" />
            <Swatch colour="#dc2626" label="bad season, no payout" />
            <Swatch colour="#a3a3a3" label="paid, little loss" />
            <Swatch colour="#cbd5e1" label="no payout" />
          </div>
          <PayoutChart years={insurance.years} trigger={insurance.trigger_mm} exit={insurance.exit_mm} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-slate-50 p-3 text-sm" data-testid="basis-risk">
            <div className="font-semibold">Basis risk, shown honestly</div>
            <p className="mt-1">
              It would have paid in {insurance.years_paid} of {insurance.years_total} seasons, and in{" "}
              {insurance.bad_years_paid} of the {insurance.bad_years} bad seasons.
            </p>
            <p className="mt-1">
              Bad seasons with no payout: <strong>{insurance.losses_not_covered.length ? insurance.losses_not_covered.join(", ") : "none"}</strong>
            </p>
            <p className="mt-1">
              Payouts with little loss: <strong>{insurance.paid_with_small_loss.length ? insurance.paid_with_small_loss.join(", ") : "none"}</strong>
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="table">
              <thead><tr><th>Season</th><th className="text-right">Index rain</th><th className="text-right">Payout</th><th className="text-right">Yield loss</th></tr></thead>
              <tbody>
                {payoutYears.map((y) => (
                  <tr key={y.year}>
                    <td>{y.year}</td>
                    <td className="text-right tabular-nums">{mm(y.index_rain_mm)}</td>
                    <td className="text-right tabular-nums">{y.payout_fraction > 0 ? etb(y.payout_etb) : "–"}</td>
                    <td className="text-right tabular-nums">{pct(y.yield_loss)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      <Section id="ai-note" title="Briefing note"
        intro="A plain-language note written by Claude from the numbers above only. It explains; the decision is yours.">
        {a.summary_text ? (
          <div className="rounded-lg border border-line bg-brand-50/50 p-4" data-testid="ai-note">
            <div className="whitespace-pre-wrap text-sm leading-6">{a.summary_text}</div>
            <p className="mt-3 text-xs text-muted">
              {a.summary_language} · {a.summary_model} · {a.summary_at ? when(a.summary_at) : ""}
            </p>
          </div>
        ) : null}
        <SummaryForm id={a.id} aiAvailable={aiAvailable} hasNote={!!a.summary_text} />
      </Section>

      <Section title="Assumptions used" intro="Estimates, not measurements. Check them against local data before relying on the result.">
        <div className="overflow-x-auto">
          <table className="table" data-testid="assumptions">
            <tbody>
              <tr><td>Typical yield without water stress</td><td className="text-right">{String(assumptions.typical_yield_t_per_ha)} t/ha</td><td className="text-muted">{String(assumptions.typical_yield_source)}</td></tr>
              <tr><td>Farm-gate price</td><td className="text-right">{etb(Number(assumptions.price_etb_per_quintal))} / quintal</td><td className="text-muted">{String(assumptions.price_source)}</td></tr>
              <tr><td>Share of harvest value for repayment</td><td className="text-right">{pct(Number(assumptions.repayment_share))}</td><td className="text-muted">default assumption</td></tr>
              <tr><td>Annual interest rate</td><td className="text-right">{pct(Number(assumptions.annual_interest_rate))}</td><td className="text-muted">default assumption</td></tr>
              <tr><td>Loan paid out before planting</td><td className="text-right">{String(assumptions.disbursement_days_before_planting)} days</td><td className="text-muted">default assumption</td></tr>
              <tr><td>Grace after harvest</td><td className="text-right">{String(assumptions.grace_days_after_harvest)} days</td><td className="text-muted">default assumption</td></tr>
              <tr><td>Insurance loading</td><td className="text-right">{pct(Number(assumptions.insurance_loading))}</td><td className="text-muted">default assumption</td></tr>
              <tr><td>Dry season</td><td className="text-right">below {pct(Number(assumptions.dry_season_share_of_median))} of median rain</td><td className="text-muted">definition</td></tr>
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
