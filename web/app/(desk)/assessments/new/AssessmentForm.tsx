"use client";

import dynamic from "next/dynamic";
import { useActionState, useMemo, useState } from "react";
import { createAssessment, type FormState } from "@/app/actions";
import type { FieldValue } from "@/components/FieldMap";
import { formatHa, ringAreaHa } from "@/lib/geo";
import { MONTHS } from "@/lib/format";
import type { Reference } from "@/lib/types";

// Leaflet needs the browser, so the map only renders on the client.
const FieldMap = dynamic(() => import("@/components/FieldMap"), {
  ssr: false,
  loading: () => <div className="h-[340px] animate-pulse rounded-lg bg-slate-100 sm:h-[420px]" />,
});

export default function AssessmentForm({ reference }: { reference: Reference }) {
  const [state, action, pending] = useActionState<FormState, FormData>(createAssessment, {});
  const [mode, setMode] = useState<"boundary" | "point">("boundary");
  const [field, setField] = useState<FieldValue>({ boundary: null, point: null });
  const [cropKey, setCropKey] = useState(reference.crops[0].key);
  const crop = reference.crops.find((c) => c.key === cropKey)!;
  const ins = reference.assumptions.insurance;

  const drawnArea = useMemo(
    () => (field.boundary ? ringAreaHa(field.boundary.coordinates[0]) : null),
    [field.boundary],
  );
  const located = mode === "boundary" ? !!field.boundary : !!field.point;

  return (
    <form action={action} className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
      <input type="hidden" name="location_mode" value={mode} />
      <input type="hidden" name="boundary" value={field.boundary ? JSON.stringify(field.boundary) : ""} />
      <input type="hidden" name="lat" value={field.point?.lat ?? ""} />
      <input type="hidden" name="lon" value={field.point?.lon ?? ""} />

      <section className="card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">1. The field</h2>
          <div className="inline-flex rounded-lg border border-slate-300 p-0.5 text-sm" role="group" aria-label="How to mark the field">
            {(["boundary", "point"] as const).map((m) => (
              <button key={m} type="button" onClick={() => setMode(m)}
                className={`rounded-md px-3 py-1 ${mode === m ? "bg-brand text-white" : "text-ink hover:bg-slate-100"}`}
                aria-pressed={mode === m}>
                {m === "boundary" ? "Draw boundary" : "Pin + size"}
              </button>
            ))}
          </div>
        </div>
        <p className="text-sm text-muted">
          {mode === "boundary"
            ? "Zoom in on the satellite view and click each corner of the farmer's field. The area is measured from the shape, and rainfall is averaged over every NASA POWER grid cell the field touches."
            : "Click the field's location, then enter the farm size below."}
        </p>
        <FieldMap mode={mode} onChange={setField} />
        {mode === "point" ? (
          <div className="max-w-48">
            <label htmlFor="area_ha" className="label">Farm size (hectares)</label>
            <input id="area_ha" name="area_ha" type="number" step="0.01" min="0.01" max="5000" className="input" required />
          </div>
        ) : drawnArea ? (
          <p className="text-sm">Measured area: <strong>{formatHa(drawnArea)}</strong></p>
        ) : null}
      </section>

      <section className="space-y-5">
        <div className="card space-y-3">
          <h2 className="font-semibold">2. Farmer and loan</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="farmer_name" className="label">Farmer name</label>
              <input id="farmer_name" name="farmer_name" required maxLength={120} className="input" />
            </div>
            <div>
              <label htmlFor="farmer_ref" className="label">Reference <span className="font-normal text-muted">(optional)</span></label>
              <input id="farmer_ref" name="farmer_ref" maxLength={60} className="input" placeholder="e.g. customer ID" />
            </div>
          </div>
          <div>
            <label htmlFor="loan_amount_etb" className="label">Requested loan (ETB)</label>
            <input id="loan_amount_etb" name="loan_amount_etb" type="number" min="1" step="1" required className="input" />
          </div>
        </div>

        <div className="card space-y-3">
          <h2 className="font-semibold">3. Crop and season</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="crop" className="label">Crop</label>
              <select id="crop" name="crop" className="input" value={cropKey} onChange={(e) => setCropKey(e.target.value)}>
                {reference.crops.map((c) => <option key={c.key} value={c.key}>{c.name}</option>)}
              </select>
              <p className="hint">{crop.season_days}-day season (FAO-56).</p>
            </div>
            <div>
              <label htmlFor="soil" className="label">Soil</label>
              <select id="soil" name="soil" className="input" defaultValue="loam">
                {reference.soils.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="planting_month" className="label">Planting month</label>
              <select id="planting_month" name="planting_month" className="input" defaultValue="7">
                {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="planting_day" className="label">Planting day</label>
              <input id="planting_day" name="planting_day" type="number" min="1" max="31" defaultValue="1" required className="input" />
            </div>
          </div>
          {crop.notes.map((n) => <p key={n} className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">{n}</p>)}
        </div>

        <details className="card">
          <summary className="cursor-pointer font-semibold">4. Assumptions <span className="font-normal text-muted">(optional overrides)</span></summary>
          <p className="mt-2 text-xs text-muted">
            Leave blank to use the default assumptions. They are estimates, not facts: replace them with local data when you have it.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="typical_yield_t_per_ha" className="label">Typical yield (t/ha)</label>
              <input id="typical_yield_t_per_ha" name="typical_yield_t_per_ha" type="number" step="0.1" min="0.1" max="20"
                className="input" placeholder={`default ${crop.typical_yield_t_per_ha}`} />
            </div>
            <div>
              <label htmlFor="price_etb_per_quintal" className="label">Price (ETB per quintal)</label>
              <input id="price_etb_per_quintal" name="price_etb_per_quintal" type="number" step="1" min="1"
                className="input" placeholder={`default ${crop.price_etb_per_quintal}`} />
            </div>
            <div>
              <label htmlFor="trigger_percentile" className="label">Insurance trigger (percentile)</label>
              <input id="trigger_percentile" name="trigger_percentile" type="number" min="5" max="50"
                className="input" placeholder={`default ${ins.trigger_percentile}`} />
            </div>
            <div>
              <label htmlFor="exit_percentile" className="label">Full payout at (percentile)</label>
              <input id="exit_percentile" name="exit_percentile" type="number" min="1" max="45"
                className="input" placeholder={`default ${ins.exit_percentile}`} />
            </div>
          </div>
        </details>

        {state.error ? <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{state.error}</p> : null}
        <button type="submit" className="btn-primary w-full py-3" disabled={pending || !located}>
          {pending ? "Analysing 40+ years of weather…" : located ? "Assess this loan" : "Mark the field on the map first"}
        </button>
      </section>
    </form>
  );
}
