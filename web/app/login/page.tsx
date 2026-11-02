import { Suspense } from "react";
import LoginForm from "./LoginForm";

export const metadata = { title: "Sign in · Agri-Loan Climate Risk Desk" };

async function ExpiredNotice({ searchParams }: { searchParams: PageProps<"/login">["searchParams"] }) {
  const { expired } = await searchParams;
  if (!expired) return null;
  return (
    <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
      Your session ended. Please sign in again.
    </p>
  );
}

export default function LoginPage({ searchParams }: PageProps<"/login">) {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-lg font-bold text-white">
            AL
          </div>
          <h1 className="text-xl font-semibold">Agri-Loan Climate Risk Desk</h1>
          <p className="mt-1 text-sm text-muted">Sign in with your loan officer account.</p>
        </div>
        <Suspense fallback={null}>
          <ExpiredNotice searchParams={searchParams} />
        </Suspense>
        <LoginForm />
      </div>
    </main>
  );
}
