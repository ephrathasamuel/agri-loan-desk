"use client";

import dynamic from "next/dynamic";
import { useActionState } from "react";
import { requestSummary, type FormState } from "@/app/actions";

export const ResultMap = dynamic(() => import("@/components/ResultMap"), {
  ssr: false,
  loading: () => <div className="h-64 animate-pulse rounded-lg bg-slate-100 sm:h-72" />,
});

export function SummaryForm({ id, aiAvailable, hasNote }: { id: number; aiAvailable: boolean; hasNote: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(requestSummary.bind(null, id), {});
  if (!aiAvailable) {
    return (
      <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-muted" data-testid="ai-off">
        AI briefing notes are off: the API has no ANTHROPIC_API_KEY. Everything above is calculated without AI.
      </p>
    );
  }
  return (
    <form action={action} className="flex flex-wrap items-end gap-2">
      <div>
        <label htmlFor="language" className="label">Language</label>
        <select id="language" name="language" className="input" defaultValue="en">
          <option value="en">English</option>
          <option value="am">Amharic (አማርኛ)</option>
        </select>
      </div>
      <button type="submit" className="btn-primary" disabled={pending}>
        {pending ? "Writing note…" : hasNote ? "Write a new note" : "Write briefing note"}
      </button>
      {state.error ? <p role="alert" className="w-full text-sm text-red-700">{state.error}</p> : null}
    </form>
  );
}
