export const etb = (n: number) =>
  `ETB ${Math.round(n).toLocaleString("en-US")}`;

export const pct = (x: number, digits = 0) => `${(x * 100).toFixed(digits)}%`;

export const mm = (n: number) => `${Math.round(n).toLocaleString("en-US")} mm`;

export function day(iso: string) {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}

export function when(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Africa/Addis_Ababa",
  });
}

export const riskClass: Record<string, string> = {
  Low: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  Medium: "bg-amber-100 text-amber-800 ring-amber-200",
  High: "bg-red-100 text-red-800 ring-red-200",
};

export function verdictClass(verdict: string) {
  if (verdict === "Within capacity") return "bg-emerald-100 text-emerald-800 ring-emerald-200";
  if (verdict.startsWith("Repayable")) return "bg-amber-100 text-amber-800 ring-amber-200";
  return "bg-red-100 text-red-800 ring-red-200";
}

export const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
