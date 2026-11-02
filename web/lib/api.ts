import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Assessment, AssessmentSummary, Reference, User } from "./types";

// The browser never talks to the API directly: pages and server actions call
// it from the Next.js server with the officer's token from an httpOnly cookie.
export const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
export const SESSION_COOKIE = "ald_session";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function messageFrom(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      // FastAPI validation errors: [{loc, msg}, ...]
      return detail
        .map((d: { msg?: string; loc?: unknown[] }) => (d.msg ?? "").replace(/^Value error, /, ""))
        .filter(Boolean)
        .join(" ");
    }
  }
  return status >= 500 ? "The risk service is unavailable. Try again shortly." : `Request failed (${status}).`;
}

export async function api<T>(path: string, init: RequestInit = {}, opts: { auth?: boolean } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (opts.auth !== false) {
    const token = (await cookies()).get(SESSION_COOKIE)?.value;
    if (!token) redirect("/login");
    headers.set("Authorization", `Bearer ${token}`);
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError(503, "The risk service cannot be reached. Is the API running?");
  }
  if (res.status === 401 && opts.auth !== false) redirect("/login?expired=1");
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(body, res.status));
  return body as T;
}

export const getMe = () => api<User>("/auth/me");
export const getReference = () => api<Reference>("/reference");
export const listAssessments = () => api<AssessmentSummary[]>("/assessments");
export const getAssessment = (id: string | number) => api<Assessment>(`/assessments/${id}`);
export const listUsers = () => api<User[]>("/users");
