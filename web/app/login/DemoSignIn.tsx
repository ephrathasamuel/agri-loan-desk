"use client";

import { useActionState } from "react";
import { signIn, type FormState } from "../actions";

export default function DemoSignIn({ email, password }: { email: string; password: string }) {
  const [state, action, pending] = useActionState<FormState, FormData>(signIn, {});
  return (
    <form action={action} className="card mt-4 space-y-3">
      <div>
        <p className="text-sm font-semibold">Just looking around?</p>
        <p className="mt-1 text-sm text-muted">
          Use the shared demo account. It has every feature, including the admin pages, and anyone can see what is saved in it.
        </p>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted">Email</dt>
        <dd className="font-mono break-all">{email}</dd>
        <dt className="text-muted">Password</dt>
        <dd className="font-mono">{password}</dd>
      </dl>
      <input type="hidden" name="email" value={email} />
      <input type="hidden" name="password" value={password} />
      {state.error ? <p role="alert" className="text-sm text-red-700">{state.error}</p> : null}
      <button type="submit" className="btn-secondary w-full" disabled={pending}>
        {pending ? "Signing in…" : "Try the demo"}
      </button>
    </form>
  );
}
