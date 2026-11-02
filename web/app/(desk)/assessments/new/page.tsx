import { getReference } from "@/lib/api";
import AssessmentForm from "./AssessmentForm";

export const metadata = { title: "New assessment · Agri-Loan Climate Risk Desk" };

export default async function NewAssessmentPage() {
  const reference = await getReference();
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">New assessment</h1>
        <p className="text-sm text-muted">
          Mark the field, describe the loan and crop. The desk replays the season in every year since 1984.
        </p>
      </div>
      <AssessmentForm reference={reference} />
    </div>
  );
}
