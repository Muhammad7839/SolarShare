// Interactive product module that runs live comparisons against the FastAPI backend.
"use client";

import { useMemo, useState } from "react";
import { fetchLiveComparison, getAuthIdentityKey, resolveLocation } from "@/lib/api";
import { LiveComparisonResponse, LocationResolveResponse, PriorityMode } from "@/lib/types";

const priorities: Array<{ value: PriorityMode; label: string }> = [
  { value: "balanced", label: "Balanced" },
  { value: "lowest_cost", label: "Lowest Cost" },
  { value: "highest_reliability", label: "Highest Reliability" },
  { value: "closest_distance", label: "Closest Distance" }
];

const zipSuggestionPool = ["10001", "11201", "11368", "11757", "11746", "11590", "11901"];

function getUserKey(): string {
  const authIdentity = getAuthIdentityKey();
  if (authIdentity) {
    return authIdentity;
  }
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

export function ComparisonTool() {
  const [step, setStep] = useState(1);
  const [location, setLocation] = useState("");
  const [zipCode, setZipCode] = useState("");
  const [usageInput, setUsageInput] = useState("650");
  const [priority, setPriority] = useState<PriorityMode>("balanced");
  const [autoAssign, setAutoAssign] = useState(true);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locationPreview, setLocationPreview] = useState<LocationResolveResponse | null>(null);
  const [result, setResult] = useState<LiveComparisonResponse | null>(null);

  const recommendation = result?.recommendation.recommended_option;
  const financial = result?.financial_breakdown;
  const confidenceScore = result?.confidence_score ?? result?.resolution_confidence ?? 0;
  const isWaitlist = result?.project_status === "waitlist";
  const optionChartData = useMemo(() => {
    if (!result) {
      return [];
    }
    return result.options.slice(0, 4).map((item) => ({
      name: item.option.provider_name,
      savings: Math.max(item.savings_vs_baseline, 0)
    }));
  }, [result]);
  const monthlyChartData = useMemo(() => {
    const monthly = financial?.monthly_breakdown || [];
    return monthly.map((entry) => ({
      month: entry.month,
      savings: Number(entry.savings || 0)
    }));
  }, [financial]);

  function usageValue(): number | null {
    const trimmed = usageInput.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    if (!Number.isFinite(parsed)) {
      return null;
    }
    return parsed;
  }

  function zipSuggestionsForInput(input: string): string[] {
    const trimmed = input.trim();
    if (!trimmed) {
      return zipSuggestionPool.slice(0, 3);
    }
    if (!/^\d+$/.test(trimmed)) {
      return zipSuggestionPool.slice(0, 3);
    }
    const numeric = Number(trimmed.slice(0, 5));
    return [...zipSuggestionPool].sort((a, b) => Math.abs(Number(a) - numeric) - Math.abs(Number(b) - numeric)).slice(0, 3);
  }

  function validateStep(stepNumber: number): boolean {
    const safeLocation = location.trim();
    const safeZip = zipCode.trim();

    if (stepNumber === 1) {
      if (!safeLocation && !safeZip) {
        setError("Enter a city/state location or ZIP code.");
        return false;
      }
      if (safeZip && !/^\d{5}(?:-\d{4})?$/.test(safeZip)) {
        const suggestions = zipSuggestionsForInput(safeZip).join(", ");
        setError(`ZIP code must be 5 digits or ZIP+4 format. Try: ${suggestions}`);
        return false;
      }
    }

    if (stepNumber === 2) {
      const parsedUsage = usageValue();
      if (parsedUsage === null || parsedUsage <= 0) {
        setError("Monthly usage must be a number greater than 0.");
        return false;
      }
    }

    setError(null);
    return true;
  }

  async function previewResolvedLocation() {
    if (!validateStep(1)) {
      return;
    }
    setPreviewLoading(true);
    setError(null);
    try {
      const preview = await resolveLocation({
        location: location.trim(),
        zip_code: zipCode.trim() || null
      });
      setLocationPreview(preview);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Unable to resolve location.");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validateStep(1) || !validateStep(2)) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const parsedUsage = usageValue();
      if (parsedUsage === null) {
        setError("Monthly usage must be a number greater than 0.");
        return;
      }
      const payload = await fetchLiveComparison({
        location: location.trim(),
        zip_code: zipCode.trim() || null,
        user_key: getUserKey(),
        assign_project: autoAssign,
        monthly_usage_kwh: parsedUsage,
        priority
      });
      setResult(payload);
      setStep(3);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card dark:border-slate-700 dark:bg-slate-900/70" id="comparison-tool">
      <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-solarBlue-100 bg-solarBlue-50/60 p-5 dark:border-slate-700 dark:bg-slate-800/70">
          <h3 className="text-xl font-semibold text-solarBlue-900 dark:text-slate-100">Start Comparison</h3>
          <div className="comparison-stepper">
            <span className={step === 1 ? "active" : step > 1 ? "done" : ""}>1. Location</span>
            <span className={step === 2 ? "active" : step > 2 ? "done" : ""}>2. Usage</span>
            <span className={step === 3 ? "active" : ""}>3. Review</span>
          </div>

          {step === 1 ? (
            <>
              <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80 dark:text-slate-200">
                Location (city, state)
                <input
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                  placeholder="Example: New York, NY"
                  className="rounded-xl border border-solarBlue-100 bg-white px-4 py-3 text-solarBlue-900 outline-none ring-solarBlue-200 focus:ring dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-600"
                />
              </label>

              <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80 dark:text-slate-200">
                ZIP Code
                <input
                  value={zipCode}
                  onChange={(event) => setZipCode(event.target.value)}
                  placeholder="11757"
                  className="rounded-xl border border-solarBlue-100 bg-white px-4 py-3 text-solarBlue-900 outline-none ring-solarBlue-200 focus:ring dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-600"
                />
              </label>

              <button
                type="button"
                onClick={() => {
                  void previewResolvedLocation();
                }}
                disabled={previewLoading}
                className="w-full rounded-xl border border-solarBlue-200 bg-white px-4 py-3 text-sm font-semibold text-solarBlue-700 transition hover:bg-solarBlue-50 disabled:cursor-not-allowed disabled:opacity-70 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {previewLoading ? "Resolving Location..." : "Preview Location"}
              </button>

              {locationPreview ? (
                <article className="rounded-xl border border-energyGreen-200 bg-energyGreen-100/70 p-3 text-sm text-solarBlue-900 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-100">
                  <p className="font-semibold">Resolved: {locationPreview.resolved_location}</p>
                  <p className="mt-1">
                    {locationPreview.city || "City n/a"}, {locationPreview.county || "County n/a"}, {locationPreview.state_code || "State n/a"}{" "}
                    {locationPreview.postal_code || ""}
                  </p>
                  <p className="mt-1">
                    Utility region: {locationPreview.region || "n/a"} | Utility: {locationPreview.utility || "n/a"}
                  </p>
                  <p className="mt-1">
                    Confidence: {Math.round((locationPreview.confidence || 0) * 100)}% | Mode:{" "}
                    {locationPreview.using_fallback ? "Fallback" : "Live"}
                  </p>
                  {locationPreview.resolution_status === "unresolved" && locationPreview.suggested_zip_codes?.length ? (
                    <p className="mt-1">Suggested ZIPs: {locationPreview.suggested_zip_codes.join(", ")}</p>
                  ) : null}
                </article>
              ) : null}

              <button
                type="button"
                onClick={() => {
                  if (validateStep(1)) {
                    setStep(2);
                  }
                }}
                className="w-full rounded-xl bg-solarBlue-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-solarBlue-900"
              >
                Continue
              </button>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80 dark:text-slate-200">
                Monthly Usage (kWh)
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={usageInput}
                  onChange={(event) => setUsageInput(event.target.value)}
                  required
                  className="rounded-xl border border-solarBlue-100 bg-white px-4 py-3 text-solarBlue-900 outline-none ring-solarBlue-200 focus:ring dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-600"
                />
              </label>

              <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80 dark:text-slate-200">
                Priority
                <select
                  value={priority}
                  onChange={(event) => setPriority(event.target.value as PriorityMode)}
                  className="rounded-xl border border-solarBlue-100 bg-white px-4 py-3 text-solarBlue-900 outline-none ring-solarBlue-200 focus:ring dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-600"
                >
                  {priorities.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex items-center gap-2 text-sm font-semibold text-solarBlue-900/80 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={autoAssign}
                  onChange={(event) => setAutoAssign(event.target.checked)}
                  className="h-4 w-4 rounded border-solarBlue-300"
                />
                Automatically assign best project if capacity is available
              </label>

              <div className="grid gap-2 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="rounded-xl border border-solarBlue-200 bg-white px-4 py-3 text-sm font-semibold text-solarBlue-700 transition hover:bg-solarBlue-50"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (validateStep(2)) {
                      setStep(3);
                    }
                  }}
                  className="rounded-xl bg-solarBlue-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-solarBlue-900"
                >
                  Review
                </button>
              </div>
            </>
          ) : null}

          {step === 3 ? (
            <>
              <article className="rounded-xl border border-solarBlue-100 bg-white p-3 text-sm text-solarBlue-900/75 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-200">
                <p>
                  Location: <strong>{location.trim() || "Not provided"}</strong>
                </p>
                <p>
                  ZIP: <strong>{zipCode.trim() || "Not provided"}</strong>
                </p>
                <p>
                  Usage: <strong>{usageInput.trim() ? `${usageInput.trim()} kWh` : "Not provided"}</strong>
                </p>
                <p>
                  Priority: <strong>{priorities.find((item) => item.value === priority)?.label || priority}</strong>
                </p>
                <p>
                  Auto-assign best project: <strong>{autoAssign ? "Enabled" : "Disabled"}</strong>
                </p>
              </article>

              <div className="grid gap-2 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="rounded-xl border border-solarBlue-200 bg-white px-4 py-3 text-sm font-semibold text-solarBlue-700 transition hover:bg-solarBlue-50"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-xl bg-solarBlue-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-solarBlue-900 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? "Running Live Comparison..." : "Run Live Comparison"}
                </button>
              </div>
            </>
          ) : null}

          {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-600 dark:bg-red-950/50 dark:text-red-200">{error}</p> : null}
        </form>

        <div className="space-y-4">
          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">Top Recommendation</p>
            <h4 className="mt-2 text-xl font-semibold text-solarBlue-900 dark:text-slate-100">
              {recommendation ? "Best project automatically selected" : "Run a scenario to see your best fit"}
            </h4>
            <p className="mt-1 text-sm font-semibold text-solarBlue-700 dark:text-slate-200">
              {recommendation ? recommendation.option.provider_name : "-"}
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full bg-solarBlue-50 px-2 py-1 text-solarBlue-700">No upfront cost</span>
              <span className="rounded-full bg-solarBlue-50 px-2 py-1 text-solarBlue-700">Cancel anytime</span>
              <span className="rounded-full bg-solarBlue-50 px-2 py-1 text-solarBlue-700">No installation</span>
            </div>
            <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/75 dark:text-slate-200">
              <p>
                Monthly Cost: <strong className="metric-value">{recommendation ? `$${recommendation.monthly_cost.toFixed(2)}` : "-"}</strong>
              </p>
              <p>
                Savings vs Baseline:{" "}
                <strong className="metric-value metric-accent-green">
                  {recommendation ? `$${recommendation.savings_vs_baseline.toFixed(2)}` : "-"}
                </strong>
              </p>
              <p>
                Estimated Monthly Savings:{" "}
                <strong className="metric-value metric-accent-green">
                  {financial ? `$${(financial.average_monthly_savings ?? financial.user_savings).toFixed(2)}` : "-"}
                </strong>
              </p>
              <p>
                Estimated Annual Savings:{" "}
                <strong className="metric-value metric-accent-green">{financial ? `$${(financial.annual_savings ?? financial.user_savings).toFixed(2)}` : "-"}</strong>
              </p>
              <p>
                Reliability:{" "}
                <strong className="metric-value">{recommendation ? `${Math.round(recommendation.option.reliability_score * 100)}%` : "-"}</strong>
              </p>
              <p>
                CO2 avoided estimate:{" "}
                <strong className="metric-value">
                  {financial ? `${Math.round((((financial.estimated_credit_value ?? financial.credit_value) / 0.2) * 0.7))} lb/year` : "-"}
                </strong>
              </p>
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">Savings by Option</p>
            <div className="mt-4 space-y-3">
              {optionChartData.length ? (
                optionChartData.map((row) => (
                  <div key={row.name} className="grid grid-cols-[120px_1fr_auto] items-center gap-3">
                    <span className="truncate text-xs font-semibold text-solarBlue-900/70 dark:text-slate-200">{row.name}</span>
                    <div className="h-2 rounded-full bg-solarBlue-50 dark:bg-slate-800">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-solarBlue-500 to-energyGreen-500"
                        style={{ width: `${Math.min((row.savings / 120) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="metric-value metric-accent-green text-xs font-bold text-solarBlue-900 dark:text-emerald-300">${row.savings.toFixed(0)}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-solarBlue-900/60 dark:text-slate-300">No chart yet. Run the tool to populate.</p>
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">12-Month Savings Simulation</p>
            <div className="mt-4 space-y-3">
              {monthlyChartData.length ? (
                monthlyChartData.map((row) => (
                  <div key={row.month} className="grid grid-cols-[32px_1fr_auto] items-center gap-3">
                    <span className="text-xs font-semibold text-solarBlue-900/70 dark:text-slate-200">{row.month}</span>
                    <div className="h-2 rounded-full bg-solarBlue-50 dark:bg-slate-800">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-solarBlue-500 to-energyGreen-500"
                        style={{ width: `${Math.min(Math.max((row.savings / 30) * 100, 2), 100)}%` }}
                      />
                    </div>
                    <span className="metric-value metric-accent-green text-xs font-bold text-solarBlue-900 dark:text-emerald-300">${row.savings.toFixed(2)}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-solarBlue-900/60 dark:text-slate-300">No monthly simulation data yet.</p>
              )}
            </div>
            <p className="mt-3 text-xs text-solarBlue-900/60 dark:text-slate-300">
              Seasonality is modeled, so winter months can show lower savings than summer months.
            </p>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">Live Data Context</p>
            <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/75 dark:text-slate-200">
              <p>Location: {result?.market_context.resolved_location || "-"}</p>
              <p>
                Region: {result?.market_context.city || "-"}, {result?.market_context.county || "-"}, {result?.market_context.state_code || "-"}{" "}
                {result?.market_context.postal_code || ""}
              </p>
              <p>Utility region: {result?.market_context.region || "-"}</p>
              <p>Utility: {result?.market_context.utility || "-"}</p>
              <p>Project status: {result?.project_status || "-"}</p>
              <p>Matched projects: {result?.matched_project_count ?? "-"}</p>
              <p>Project: {result?.project_name || "-"}</p>
              <p>Project capacity: {result?.project_capacity ? `${result.project_capacity} kW` : "-"}</p>
              <p>Remaining capacity: {result?.remaining_capacity ?? "-"}</p>
              {isWaitlist ? <p>Waitlist timeline: {result?.waitlist_timeline || "Estimated availability pending"}</p> : null}
              {result?.waitlist_position ? <p>Waitlist position estimate: #{result.waitlist_position}</p> : null}
              <p>Project detail: {result?.project_status_reason || "-"}</p>
              {isWaitlist ? (
                <p className="rounded-lg bg-amber-50 px-2 py-1 text-amber-700">
                  Capacity is currently full in your matched region. Join waitlist to reserve the next available slot.
                </p>
              ) : null}
              <p>Utility baseline: {result ? `$${result.market_context.utility_price_per_kwh.toFixed(3)}/kWh` : "-"}</p>
              <p>Rate source: {result?.market_context.rate_source || "-"}</p>
              <p>Resolution confidence: {result ? `${Math.round(confidenceScore * 100)}%` : "-"}</p>
              <p>Fallback reason: {result?.fallback_reason || "None"}</p>
              <p>Observed: {result?.market_context.observed_at_utc || "-"}</p>
              {result?.market_context.rate_is_estimated ? (
                <p className="rounded-lg bg-amber-50 px-2 py-1 text-amber-700">
                  Rate is estimated based on New York averages.
                </p>
              ) : null}
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">Why this recommendation</p>
            <div className="mt-3 grid gap-3 text-sm text-solarBlue-900/75 dark:text-slate-200 md:grid-cols-3">
              <article className="rounded-xl bg-solarBlue-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.1em] text-solarBlue-700">Why this project</p>
                <p className="mt-1">Auto-selected for region fit and open capacity.</p>
                <p className="mt-1 text-xs">Distance score: {result ? `${Math.round((result.factor_breakdown?.distance || 0) * 100)}%` : "-"}</p>
              </article>
              <article className="rounded-xl bg-solarBlue-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.1em] text-solarBlue-700">Why utility match</p>
                <p className="mt-1">Matched to your NY utility region and credit policy.</p>
                <p className="mt-1 text-xs">
                  Reliability score: {result ? `${Math.round((result.factor_breakdown?.reliability || 0) * 100)}%` : "-"}
                </p>
              </article>
              <article className="rounded-xl bg-solarBlue-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.1em] text-solarBlue-700">Why this savings estimate</p>
                <p className="mt-1">12-month generation and rollover model with discount billing.</p>
                <p className="mt-1 text-xs">Price score: {result ? `${Math.round((result.factor_breakdown?.price || 0) * 100)}%` : "-"}</p>
              </article>
            </div>
            <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/75 dark:text-slate-200">
              {result?.recommendation.reasons?.map((reason) => (
                <p key={reason}>• {reason}</p>
              ))}
              {result?.platform_highlights?.map((item) => (
                <p key={item}>• {item}</p>
              ))}
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">Billing & Revenue Breakdown</p>
            <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/75 dark:text-slate-200">
              <p>Credit value: {financial ? `$${financial.credit_value.toFixed(2)}` : "-"}</p>
              <p>User payment: {financial ? `$${financial.user_payment.toFixed(2)}` : "-"}</p>
              <p>User savings: {financial ? `$${financial.user_savings.toFixed(2)}` : "-"}</p>
              <p>Platform revenue: {financial ? `$${financial.platform_revenue.toFixed(2)}` : "-"}</p>
              <p>Developer payout: {financial ? `$${financial.developer_payout.toFixed(2)}` : "-"}</p>
              <p>Platform margin: {financial ? `${Math.round(financial.platform_margin * 100)}%` : "-"}</p>
              <p>System size (estimated): {financial ? `${financial.system_size_kw?.toFixed(2)} kW` : "-"}</p>
              <p>Subscription size: {financial ? `${financial.subscription_size_kw?.toFixed(2)} kW` : "-"}</p>
              <p>Rollover credit balance: {financial ? `${financial.rollover_credit_balance?.toFixed(2)} kWh` : "-"}</p>
              <p>Savings percent: {financial ? `${financial.savings_percent?.toFixed(2)}%` : "-"}</p>
              <p>{financial?.platform_revenue_explanation || "How SolarShare makes money"}</p>
              <p>{financial?.billing_explanation || "-"}</p>
              {result?.recommendation_label === "low_savings" || result?.recommendation_label === "not_recommended" ? (
                <p className="rounded-lg bg-amber-50 px-2 py-1 text-amber-700">{result.low_savings_reason || "Savings are currently limited."}</p>
              ) : null}
              {result?.alternatives?.map((alternative) => (
                <p key={alternative}>• {alternative}</p>
              ))}
              {financial?.invoice_preview ? (
                <p>
                  Invoice preview: credits ${financial.invoice_preview.utility_credits.toFixed(2)}, payment ${financial.invoice_preview.payment_due.toFixed(2)}, savings $
                  {financial.invoice_preview.savings.toFixed(2)}
                </p>
              ) : null}
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">Billing Flow</p>
            <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/75 dark:text-slate-200">
              <p>Step 1: Solar generates credits</p>
              <p>Step 2: Utility applies credits</p>
              <p>Step 3: You pay discounted amount</p>
              <p>Billing model: {isWaitlist ? "Pending assignment" : "Consolidated or separate depending on utility/project"}</p>
              <p>Dual billing: utility bill and solar subscription bill arrive separately when required.</p>
              <p>Consolidated billing: utility statement includes community-solar credit adjustments.</p>
            </div>
          </article>

          <article className="rounded-2xl border border-solarBlue-100 p-5 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-900/60 dark:text-slate-300">How this estimate was calculated</p>
            <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/75 dark:text-slate-200">
              <p>Confidence score: {result ? `${Math.round(confidenceScore * 100)}%` : "-"}</p>
              {result?.confidence_reason?.map((item) => (
                <p key={item}>• {item}</p>
              ))}
              {(result?.assumptions_used || result?.assumptions || []).map((item) => (
                <p key={`assumption-${item}`}>Assumption: {item}</p>
              ))}
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
