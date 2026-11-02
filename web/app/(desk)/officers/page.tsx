import { redirect } from "next/navigation";
import { getMe, listUsers } from "@/lib/api";
import { when } from "@/lib/format";
import OfficerForm from "./OfficerForm";

export const metadata = { title: "Officers · Agri-Loan Climate Risk Desk" };

export default async function OfficersPage() {
  const me = await getMe();
  if (me.role !== "admin") redirect("/assessments");
  const users = await listUsers();
  return (
    <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
      <section className="card overflow-x-auto">
        <h1 className="mb-3 text-xl font-semibold">Loan officers</h1>
        <table className="table">
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Added</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td className="font-medium">{u.name}</td>
                <td>{u.email}</td>
                <td className="capitalize">{u.role}</td>
                <td className="text-muted">{when(u.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card">
        <h2 className="mb-3 text-lg font-semibold">Add an account</h2>
        <OfficerForm />
      </section>
    </div>
  );
}
