import { Suspense } from "react";
import { api } from "@/lib/api";
import DemoSignIn from "./DemoSignIn";
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

// Shown only when the API has DEMO_ACCOUNT on. A sleeping or unreachable API just hides it.
// The box is hidden only when the API says the demo is off. If the API is still waking up
// (about half a minute on a free plan), the box is shown and the button waits for it.
async function DemoAccount() {
  const demo = await api<{ enabled: boolean }>(
    "/auth/demo", { signal: AbortSignal.timeout(10_000) }, { auth: false }).catch(() => null);
  if (demo && !demo.enabled) return null;
  return <DemoSignIn waking={!demo} />;
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
        <Suspense fallback={null}>
          <DemoAccount />
        </Suspense>
      </div>
    </main>
  );
}
