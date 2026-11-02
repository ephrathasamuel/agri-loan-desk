"use client";

import { useActionState } from "react";
import { createOfficer, type FormState } from "@/app/actions";

export default function OfficerForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(createOfficer, {});
  return (
    <form action={action} className="space-y-3">
      <div>
        <label htmlFor="name" className="label">Name</label>
        <input id="name" name="name" required maxLength={120} className="input" />
      </div>
      <div>
        <label htmlFor="email" className="label">Email</label>
        <input id="email" name="email" type="email" required className="input" />
      </div>
      <div>
        <label htmlFor="password" className="label">Starting password</label>
        <input id="password" name="password" type="password" minLength={10} required className="input" autoComplete="new-password" />
        <p className="hint">At least 10 characters. Share it privately.</p>
      </div>
      <div>
        <label htmlFor="role" className="label">Role</label>
        <select id="role" name="role" className="input" defaultValue="officer">
          <option value="officer">Loan officer (sees own assessments)</option>
          <option value="admin">Admin (sees all, manages accounts)</option>
        </select>
      </div>
      {state.error ? <p role="alert" className="text-sm text-red-700">{state.error}</p> : null}
      {state.ok ? <p role="status" className="text-sm text-emerald-700">{state.ok}</p> : null}
      <button type="submit" className="btn-primary" disabled={pending}>{pending ? "Adding…" : "Add account"}</button>
    </form>
  );
}
