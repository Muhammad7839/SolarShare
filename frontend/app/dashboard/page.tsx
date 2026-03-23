// Authenticated customer dashboard with persisted savings ledger and billing lifecycle history.
"use client";

import { useEffect, useMemo, useState } from "react";
import { SectionTitle } from "@/components/SectionTitle";
import {
  buildInvoiceDownloadUrl,
  clearAuthSession,
  fetchBillingInvoices,
  fetchCurrentUser,
  fetchDashboardDataAuthenticated,
  getAuthToken,
  getAuthUser,
  loginCustomer,
  signupCustomer,
  updateInvoiceStatus
} from "@/lib/api";
import { AuthUser, DashboardDataResponse } from "@/lib/types";

type AuthMode = "login" | "signup";
type InvoiceStatus = "draft" | "issued" | "paid" | "failed";

async function downloadInvoice(invoiceId: string): Promise<void> {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Sign in to download invoices.");
  }
  const response = await fetch(buildInvoiceDownloadUrl(invoiceId), {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) {
    throw new Error("Unable to download invoice.");
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = `solarshare-invoice-${invoiceId}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(objectUrl);
}

export default function DashboardPage() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [user, setUser] = useState<AuthUser | null>(getAuthUser());
  const [data, setData] = useState<DashboardDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invoiceActionId, setInvoiceActionId] = useState<string | null>(null);

  async function refreshDashboard() {
    setLoading(true);
    setError(null);
    try {
      const profile = await fetchCurrentUser();
      const dashboardPayload = await fetchDashboardDataAuthenticated();
      const invoicePayload = await fetchBillingInvoices();
      setUser(profile);
      setData({ ...dashboardPayload, billing_history: invoicePayload });
    } catch (loadError) {
      setUser(null);
      setData(null);
      clearAuthSession();
      setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }
    void refreshDashboard();
  }, []);

  async function submitAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const credentials = { email: email.trim(), password };
      if (authMode === "signup") {
        await signupCustomer(credentials);
      } else {
        await loginCustomer(credentials);
      }
      await refreshDashboard();
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function setInvoiceStatus(invoiceId: string, status: InvoiceStatus) {
    setInvoiceActionId(invoiceId);
    setError(null);
    try {
      await updateInvoiceStatus(invoiceId, status);
      await refreshDashboard();
    } catch (invoiceError) {
      setError(invoiceError instanceof Error ? invoiceError.message : "Unable to update invoice.");
    } finally {
      setInvoiceActionId(null);
    }
  }

  const chart = useMemo(() => data?.monthly_savings || [], [data]);
  const billingHistory = useMemo(() => data?.billing_history || [], [data]);

  if (!user) {
    return (
      <main className="mx-auto w-full max-w-7xl px-5 py-16">
        <SectionTitle
          eyebrow="Dashboard"
          title="Sign in to your SolarShare account"
          subtitle="Use your customer account to view real subscription savings, invoices, and rollover credits."
        />
        <section className="mt-8 max-w-xl rounded-2xl border border-solarBlue-100 bg-white p-6 shadow-card">
          <div className="mb-4 flex gap-2 rounded-xl bg-solarBlue-50 p-1">
            <button
              type="button"
              onClick={() => setAuthMode("login")}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${
                authMode === "login" ? "bg-white text-solarBlue-700 shadow-sm" : "text-solarBlue-900/70"
              }`}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => setAuthMode("signup")}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${
                authMode === "signup" ? "bg-white text-solarBlue-700 shadow-sm" : "text-solarBlue-900/70"
              }`}
            >
              Sign Up
            </button>
          </div>
          <form className="grid gap-3" onSubmit={submitAuth}>
            <label className="grid gap-1 text-sm font-semibold text-solarBlue-900/80">
              Email
              <input
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="rounded-xl border border-solarBlue-100 px-3 py-2 outline-none ring-solarBlue-200 focus:ring"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-solarBlue-900/80">
              Password
              <input
                required
                type="password"
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="rounded-xl border border-solarBlue-100 px-3 py-2 outline-none ring-solarBlue-200 focus:ring"
              />
            </label>
            <button
              type="submit"
              disabled={submitting}
              className="mt-2 rounded-xl bg-solarBlue-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-solarBlue-900 disabled:opacity-70"
            >
              {submitting ? "Please wait..." : authMode === "signup" ? "Create Account" : "Sign In"}
            </button>
          </form>
          <p className="mt-4 text-xs text-solarBlue-900/65">
            Your dashboard is tied to account identity instead of temporary browser keys.
          </p>
          {error ? <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="Dashboard"
        title="Your Community Solar Subscription"
        subtitle="Billing records and savings history are loaded from persisted project and ledger data."
      />

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-solarBlue-100 bg-white px-4 py-3 text-sm">
        <p className="text-solarBlue-900/80">
          Signed in as <strong>{user.email}</strong>
        </p>
        <button
          type="button"
          onClick={() => {
            clearAuthSession();
            setUser(null);
            setData(null);
          }}
          className="rounded-lg border border-solarBlue-200 px-3 py-1.5 font-semibold text-solarBlue-700 hover:bg-solarBlue-50"
        >
          Sign Out
        </button>
      </div>

      {loading ? <p className="mt-8 text-sm text-solarBlue-900/70">Loading dashboard...</p> : null}
      {error ? <p className="mt-8 rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</p> : null}

      {data && !loading ? (
        <section className="mt-8 grid gap-5 md:grid-cols-3">
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Year-to-Date Savings</p>
            <p className="mt-2 text-3xl font-semibold text-energyGreen-700">${(data.year_to_date_savings ?? data.total_savings).toFixed(2)}</p>
          </article>
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Rollover Balance</p>
            <p className="mt-2 text-3xl font-semibold text-solarBlue-700">{data.rollover_credits.toFixed(2)} kWh</p>
          </article>
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Subscription Size</p>
            <p className="mt-2 text-3xl font-semibold text-solarBlue-700">{data.subscription_size_kw.toFixed(2)} kW</p>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5 md:col-span-2">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Monthly Savings (Persisted Ledger)</p>
            <div className="mt-4 space-y-3">
              {chart.length ? (
                chart.map((entry) => (
                  <div key={entry.month} className="grid grid-cols-[36px_1fr_auto] items-center gap-3">
                    <span className="text-xs font-semibold text-solarBlue-900/70">{entry.month}</span>
                    <div className="h-2 rounded-full bg-solarBlue-50">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-solarBlue-500 to-energyGreen-500"
                        style={{ width: `${Math.min(Math.max((entry.savings / 30) * 100, 2), 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-bold text-energyGreen-700">${entry.savings.toFixed(2)}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-solarBlue-900/70">No ledger months yet. Run product simulation with auto-assign enabled.</p>
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Subscription Profile</p>
            <div className="mt-3 space-y-2 text-sm text-solarBlue-900/80">
              <p>Project: {data.project_info?.name || "-"}</p>
              <p>Utility: {data.utility || "-"}</p>
              <p>Region: {data.region || "-"}</p>
              <p>Billing model: {data.project_info?.billing_model || "-"}</p>
              <p>Project capacity: {data.project_info ? `${data.project_info.capacity_kw} kW` : "-"}</p>
              <p>Remaining capacity: {data.project_info?.remaining_capacity ?? "-"}</p>
              <p>Subscription start: {data.subscription_start_date || "-"}</p>
              <p>Generation share: {data.monthly_generation_share ? `${(data.monthly_generation_share * 100).toFixed(2)}%` : "-"}</p>
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5 md:col-span-3">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Billing History & Invoice Lifecycle</p>
            <div className="mt-3 overflow-x-auto">
              {billingHistory.length ? (
                <table className="w-full min-w-[840px] border-collapse text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.12em] text-solarBlue-900/55">
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Month</th>
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Credits</th>
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Payment</th>
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Savings</th>
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Rollover</th>
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Status</th>
                      <th className="border-b border-solarBlue-100 py-2 pr-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {billingHistory.map((invoice) => (
                      <tr key={invoice.invoice_id} className="text-solarBlue-900/80">
                        <td className="border-b border-solarBlue-50 py-2 pr-3">{invoice.month}</td>
                        <td className="border-b border-solarBlue-50 py-2 pr-3">${invoice.utility_credits.toFixed(2)}</td>
                        <td className="border-b border-solarBlue-50 py-2 pr-3">${invoice.payment_due.toFixed(2)}</td>
                        <td className="border-b border-solarBlue-50 py-2 pr-3 text-energyGreen-700">${invoice.savings.toFixed(2)}</td>
                        <td className="border-b border-solarBlue-50 py-2 pr-3">{invoice.rollover_balance.toFixed(2)} kWh</td>
                        <td className="border-b border-solarBlue-50 py-2 pr-3">
                          <span className="rounded-full bg-solarBlue-50 px-2 py-1 text-xs font-semibold text-solarBlue-700">{invoice.status}</span>
                        </td>
                        <td className="border-b border-solarBlue-50 py-2 pr-3">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                void downloadInvoice(invoice.invoice_id);
                              }}
                              className="rounded-md border border-solarBlue-200 px-2 py-1 text-xs font-semibold text-solarBlue-700 hover:bg-solarBlue-50"
                            >
                              Download
                            </button>
                            <button
                              type="button"
                              disabled={invoiceActionId === invoice.invoice_id || invoice.status === "paid"}
                              onClick={() => {
                                void setInvoiceStatus(invoice.invoice_id, "paid");
                              }}
                              className="rounded-md border border-emerald-200 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60"
                            >
                              Mark Paid
                            </button>
                            <button
                              type="button"
                              disabled={invoiceActionId === invoice.invoice_id || invoice.status === "failed"}
                              onClick={() => {
                                void setInvoiceStatus(invoice.invoice_id, "failed");
                              }}
                              className="rounded-md border border-amber-200 px-2 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-50 disabled:opacity-60"
                            >
                              Mark Failed
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-solarBlue-900/70">No invoice history yet for this account.</p>
              )}
            </div>
          </article>
        </section>
      ) : null}
    </main>
  );
}
