import Link from "next/link";
import { listAssessments } from "@/lib/api";
import { etb, riskClass, verdictClass, when } from "@/lib/format";

export const metadata = { title: "Assessments · Agri-Loan Climate Risk Desk" };

export default async function AssessmentsPage() {
  const rows = await listAssessments();
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Assessments</h1>
          <p className="text-sm text-muted">Every loan assessment is saved here with its full climate history.</p>
        </div>
        <Link href="/assessments/new" className="btn-primary">New assessment</Link>
      </div>

      {rows.length === 0 ? (
        <div className="card text-center">
          <p className="font-medium">No assessments yet</p>
          <p className="mt-1 text-sm text-muted">Start by drawing a farmer&apos;s field on the map.</p>
          <Link href="/assessments/new" className="btn-primary mt-4">Assess a field</Link>
        </div>
      ) : (
        <div className="card overflow-x-auto p-0 sm:p-0">
          <table className="table min-w-[640px]" data-testid="assessment-list">
            <thead>
              <tr>
                <th className="pl-4">Farmer</th>
                <th>Crop</th>
                <th className="text-right">Area</th>
                <th className="text-right">Loan</th>
                <th>Climate risk</th>
                <th>Loan check</th>
                <th className="pr-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="pl-4">
                    <Link href={`/assessments/${a.id}`} className="font-medium text-brand hover:underline">
                      {a.farmer_name}
                    </Link>
                    {a.farmer_ref ? <div className="text-xs text-muted">{a.farmer_ref}</div> : null}
                  </td>
                  <td className="capitalize">{a.crop}</td>
                  <td className="text-right tabular-nums">{a.area_ha.toFixed(2)} ha</td>
                  <td className="text-right tabular-nums">{etb(a.loan_amount_etb)}</td>
                  <td>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${riskClass[a.risk_rating]}`}>
                      {a.risk_rating}
                    </span>
                  </td>
                  <td>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${verdictClass(a.verdict)}`}>
                      {a.verdict}
                    </span>
                  </td>
                  <td className="pr-4 text-muted">
                    {when(a.created_at)}
                    <div className="text-xs">{a.created_by}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
