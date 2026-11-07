"use client";

import { useActionState } from "react";
import { demoSignIn, type FormState } from "../actions";

export default function DemoSignIn({ waking = false }: { waking?: boolean }) {
  const [state, action, pending] = useActionState<FormState>(demoSignIn, {});
  return (
    <form action={action} className="card mt-4 space-y-3">
      <div>
        <p className="text-sm font-semibold">Just looking around?</p>
        <p className="mt-1 text-sm text-muted">
          Open the demo desk with every feature. It is separate from real accounts and their data.
        </p>
      </div>
      {state.error ? <p role="alert" className="text-sm text-red-700">{state.error}</p> : null}
      <button type="submit" className="btn-secondary w-full" disabled={pending}>
        {pending ? "Opening… this can take up to a minute" : "Try the demo"}
      </button>
      {waking && !pending ? (
        <p className="text-xs text-muted">The demo server is waking up, so the first sign-in can take up to a minute.</p>
      ) : null}
    </form>
  );
}
