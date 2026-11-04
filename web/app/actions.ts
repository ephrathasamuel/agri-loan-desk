"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { api, ApiError, SESSION_COOKIE } from "@/lib/api";
import type { Assessment, User } from "@/lib/types";

export interface FormState {
  error?: string;
  ok?: string;
}

const str = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
const num = (f: FormData, k: string) => {
  const v = str(f, k);
  return v === "" ? null : Number(v);
};

type Session = { token: string; expires_in_seconds: number };

async function startSession(session: Session): Promise<never> {
  (await cookies()).set(SESSION_COOKIE, session.token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production" && process.env.INSECURE_COOKIES !== "1",
    path: "/",
    maxAge: session.expires_in_seconds,
  });
  redirect("/assessments");
}

export async function signIn(_prev: FormState, form: FormData): Promise<FormState> {
  let session: Session;
  try {
    session = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: str(form, "email"), password: String(form.get("password") ?? "") }),
    }, { auth: false });
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : "Sign-in failed." };
  }
  return startSession(session);
}

// The shared demo account has no password; the API hands out a session when the demo is on.
export async function demoSignIn(): Promise<FormState> {
  let session: Session;
  try {
    session = await api("/auth/demo", { method: "POST" }, { auth: false });
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : "The demo is not available right now." };
  }
  return startSession(session);
}

export async function signOut() {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}

export async function createAssessment(_prev: FormState, form: FormData): Promise<FormState> {
  const boundaryText = str(form, "boundary");
  const body: Record<string, unknown> = {
    farmer_name: str(form, "farmer_name"),
    farmer_ref: str(form, "farmer_ref") || null,
    crop: str(form, "crop"),
    soil: str(form, "soil"),
    planting_month: num(form, "planting_month"),
    planting_day: num(form, "planting_day"),
    loan_amount_etb: num(form, "loan_amount_etb"),
    typical_yield_t_per_ha: num(form, "typical_yield_t_per_ha"),
    price_etb_per_quintal: num(form, "price_etb_per_quintal"),
    trigger_percentile: num(form, "trigger_percentile"),
    exit_percentile: num(form, "exit_percentile"),
  };
  if (str(form, "location_mode") === "boundary") {
    if (!boundaryText) return { error: "Draw the field boundary on the map and press Finish shape." };
    body.boundary = JSON.parse(boundaryText);
  } else {
    body.lat = num(form, "lat");
    body.lon = num(form, "lon");
    body.area_ha = num(form, "area_ha");
    if (body.lat === null || body.lon === null) return { error: "Click the field's location on the map." };
    if (!body.area_ha) return { error: "Enter the farm size in hectares." };
  }
  let created: Assessment;
  try {
    created = await api<Assessment>("/assessments", { method: "POST", body: JSON.stringify(body) });
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : "The assessment could not be created." };
  }
  redirect(`/assessments/${created.id}`);
}

export async function requestSummary(id: number, _prev: FormState, form: FormData): Promise<FormState> {
  try {
    await api(`/assessments/${id}/summary`, {
      method: "POST",
      body: JSON.stringify({ language: str(form, "language") || "en" }),
    });
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : "The AI note could not be written." };
  }
  redirect(`/assessments/${id}#ai-note`);
}

export async function createOfficer(_prev: FormState, form: FormData): Promise<FormState> {
  try {
    const user = await api<User>("/users", {
      method: "POST",
      body: JSON.stringify({
        email: str(form, "email"), name: str(form, "name"),
        password: String(form.get("password") ?? ""), role: str(form, "role") || "officer",
      }),
    });
    revalidatePath("/officers");
    return { ok: `Account created for ${user.name}.` };
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : "The account could not be created." };
  }
}
