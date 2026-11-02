import Link from "next/link";
import { Suspense } from "react";
import { getMe } from "@/lib/api";
import { signOut } from "../actions";

// The header shell is static; who is signed in is read per request.
async function UserMenu() {
  const me = await getMe();
  return (
    <>
      {me.role === "admin" ? (
        <Link href="/officers" className="rounded-md px-2.5 py-1.5 text-sm hover:bg-slate-100">Officers</Link>
      ) : null}
      <div className="ml-auto flex items-center gap-3 text-sm">
        <span className="hidden text-muted md:inline" data-testid="signed-in-as">{me.name}</span>
        <form action={signOut}>
          <button type="submit" className="btn-secondary">Sign out</button>
        </form>
      </div>
    </>
  );
}

export default function DeskLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
          <Link href="/assessments" className="flex items-center gap-2 font-semibold">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">AL</span>
            <span className="hidden sm:inline">Agri-Loan Climate Risk Desk</span>
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <Link href="/assessments" className="rounded-md px-2.5 py-1.5 hover:bg-slate-100">Assessments</Link>
            <Link href="/assessments/new" className="rounded-md px-2.5 py-1.5 hover:bg-slate-100">New</Link>
          </nav>
          <Suspense fallback={<div className="ml-auto h-8 w-24 animate-pulse rounded-lg bg-slate-100" />}>
            <UserMenu />
          </Suspense>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
      <footer className="border-t border-line py-4 text-center text-xs text-muted">
        Prototype decision-support tool. Weather history: NASA POWER. Method: FAO-56 and FAO-33.
      </footer>
    </>
  );
}
