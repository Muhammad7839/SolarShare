"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchDashboardData } from "@/lib/api";
import { DashboardDataResponse } from "@/lib/types";
import { SectionTitle } from "@/components/SectionTitle";

function getUserKey(): string {
  if (typeof window === "undefined") {
    return "ss-server";
  }
  try {
    const key = "solarshare_session_id_v2";
    const existing = window.localStorage.getItem(key);
    if (existing) {
      return existing;
    }
    const created = `ss-${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(key, created);
    return created;
  } catch {
    return "ss-browser";
  }
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchDashboardData(getUserKey());
        if (active) {
          setData(payload);
        }
      } catch (dashboardError) {
        if (active) {
          setError(dashboardError instanceof Error ? dashboardError.message : "Unable to load dashboard.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

  const chart = useMemo(() => data?.monthly_savings || [], [data]);

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="Dashboard"
        title="Subscription and Savings Overview"
        subtitle="Live data from your assigned project, billing ledger, and rollover history."
      />

      {loading ? <p className="mt-8 text-sm text-solarBlue-900/70">Loading dashboard...</p> : null}
      {error ? <p className="mt-8 rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</p> : null}

      {data && !loading ? (
        <section className="mt-8 grid gap-5 md:grid-cols-3">
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Total Savings</p>
            <p className="mt-2 text-3xl font-semibold text-energyGreen-700">${data.total_savings.toFixed(2)}</p>
          </article>
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Rollover Credits</p>
            <p className="mt-2 text-3xl font-semibold text-solarBlue-700">{data.rollover_credits.toFixed(2)} kWh</p>
          </article>
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Subscription Size</p>
            <p className="mt-2 text-3xl font-semibold text-solarBlue-700">{data.subscription_size_kw.toFixed(2)} kW</p>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 bg-white p-5 md:col-span-2">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Monthly Savings Chart</p>
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
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60">Project Info</p>
            <div className="mt-3 space-y-2 text-sm text-solarBlue-900/80">
              <p>Name: {data.project_info?.name || "-"}</p>
              <p>Capacity: {data.project_info ? `${data.project_info.capacity_kw} kW` : "-"}</p>
              <p>Remaining capacity: {data.project_info?.remaining_capacity ?? "-"}</p>
              <p>Billing model: {data.project_info?.billing_model || "-"}</p>
              <p>Utility: {data.utility || "-"}</p>
              <p>Region: {data.region || "-"}</p>
            </div>
          </article>
        </section>
      ) : null}
    </main>
  );
}
