// src/App.jsx
import { useMemo, useState } from "react";
import "./App.css";
import { getOptions, getRecommendation, healthCheck } from "./api/solarShareApi";

function formatMoney(value) {
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  return num.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function formatPricePerKwh(value) {
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  return `$${num.toFixed(3)}/kWh`;
}

function Badge({ text }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        border: "1px solid #e2e8f0",
        background: "#f8fafc",
        marginRight: "8px",
        marginBottom: "6px",
      }}
    >
      {text}
    </span>
  );
}

function InfoCard({ title, children }) {
  return (
    <div className="infoCard">
      <div className="infoTitle">{title}</div>
      <div className="infoBody">{children}</div>
    </div>
  );
}

function ErrorCard({ message }) {
  if (!message) return null;
  return (
    <div className="errorCard" role="alert" aria-live="polite">
      <div className="errorTitle">Something went wrong</div>
      <div className="errorMessage">{message}</div>
    </div>
  );
}

function App() {
  const [location, setLocation] = useState("");
  const [monthlyUsage, setMonthlyUsage] = useState("");
  const [priority, setPriority] = useState("lowest_cost");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [options, setOptions] = useState(null);
  const [recommendation, setRecommendation] = useState(null);

  // TODO: Replace this with your real GitHub repo URL
  const GITHUB_REPO_URL = "https://github.com/YOUR_USERNAME/YOUR_REPO";

  const requestPayload = useMemo(() => {
    return {
      location: location.trim(),
      monthly_usage_kwh: Number(monthlyUsage),
      priority,
    };
  }, [location, monthlyUsage, priority]);

  const spotlight = useMemo(() => {
    if (!Array.isArray(options) || options.length === 0) return null;
    const rec = options.find((x) => x.is_recommended);
    return rec || options[0];
  }, [options]);

  function validate() {
    if (!requestPayload.location) return "Location is required.";
    if (
      !Number.isFinite(requestPayload.monthly_usage_kwh) ||
      requestPayload.monthly_usage_kwh <= 0
    ) {
      return "Monthly usage must be a number greater than 0.";
    }
    if (!requestPayload.priority) return "Priority is required.";
    return "";
  }

  async function handleHealthCheck() {
    setError("");
    setLoading(true);
    try {
      const res = await healthCheck();
      alert(`Backend OK: ${res.status} (v${res.version})`);
    } catch (e) {
      setError(`Health check failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleGetOptions() {
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }

    setError("");
    setLoading(true);
    setRecommendation(null);

    try {
      const res = await getOptions(requestPayload);
      setOptions(res);
      if (!Array.isArray(res) || res.length === 0) {
        setError("No options found for this location.");
      }
    } catch (e) {
      setError(e.message);
      setOptions(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleGetRecommendation() {
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }

    setError("");
    setLoading(true);
    setOptions(null);

    try {
      const res = await getRecommendation(requestPayload);
      setRecommendation(res);
      if (!res?.recommended_option) {
        setError("No recommendation available for this location.");
      }
    } catch (e) {
      setError(e.message);
      setRecommendation(null);
    } finally {
      setLoading(false);
    }
  }

  const year = new Date().getFullYear();

  const hasAnyResult =
    Boolean(spotlight) || Boolean(options) || Boolean(recommendation);

  const showEmptyState =
    !loading &&
    !error &&
    !hasAnyResult &&
    location.trim().length === 0 &&
    String(monthlyUsage).trim().length === 0;

  const showHintState =
    !loading &&
    !error &&
    !hasAnyResult &&
    (location.trim().length > 0 || String(monthlyUsage).trim().length > 0);

  return (
    <div className="container">
      <div className="bg-logo" />

      <div className="header">
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <img
            src="/logo.png"
            alt="SolarShare logo"
            style={{
              width: "64px",
              height: "64px",
              filter: "drop-shadow(0 6px 12px rgba(0,0,0,0.15))",
            }}
          />

          <div className="brand">
            <h1>SolarShare</h1>
            <p>
              Compare local clean energy options and get a clear recommendation
              in dollars.
            </p>
          </div>
        </div>

        <button
          className="secondary"
          onClick={handleHealthCheck}
          disabled={loading}
        >
          Test Backend
        </button>
      </div>

      {/* ABOUT (NEW) */}
      <div className="about">
        <div className="aboutTitle">About SolarShare</div>
        <div className="aboutText">
          SolarShare is an educational project that compares clean energy options
          based on your location and estimated monthly electricity usage. It
          returns cost estimates and highlights potential savings for easy
          side-by-side comparison. Estimates are informational and can vary
          based on provider fees and plan terms.
        </div>
      </div>

      <div className="card">
        <div className="field">
          <label>Location</label>
          <input
            type="text"
            placeholder="e.g. Long Island, NY"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Monthly usage (kWh)</label>
          <input
            type="number"
            placeholder="e.g. 650"
            value={monthlyUsage}
            onChange={(e) => setMonthlyUsage(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Priority</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="lowest_cost">Lowest cost</option>
            <option value="closest">Closest</option>
            <option value="most_reliable">Most reliable</option>
          </select>
        </div>

        <div className="actions">
          <button className="primary" onClick={handleGetOptions} disabled={loading}>
            {loading ? "Loading..." : "Get Options"}
          </button>
          <button
            className="secondary"
            onClick={handleGetRecommendation}
            disabled={loading}
          >
            {loading ? "Loading..." : "Get Recommendation"}
          </button>
        </div>
      </div>

      {/* ERROR UI CARD (NEW) */}
      <ErrorCard message={error} />

      {/* LOADING / EMPTY STATES (NEW) */}
      {loading ? (
        <InfoCard title="Loading">
          We’re contacting the backend and calculating estimates.
        </InfoCard>
      ) : null}

      {showEmptyState ? (
        <InfoCard title="Ready when you are">
          Enter your location and monthly usage to see recommendations.
        </InfoCard>
      ) : null}

      {showHintState ? (
        <InfoCard title="Almost there">
          Add any missing fields above, then click Get Options or Get Recommendation.
        </InfoCard>
      ) : null}

      {/* HOW IT WORKS */}
      <div className="howItWorks">
        <div className="howHeader">
          <h2 className="howTitle">How SolarShare works</h2>
          <p className="howSubtitle">
            A quick way to compare clean energy options using your location,
            usage, and what you care about most.
          </p>
        </div>

        <div className="howGrid">
          <div className="howStep">
            <div className="howNum">1</div>
            <div>
              <div className="howStepTitle">Enter your details</div>
              <div className="howStepText">
                Add your location and monthly kWh usage so we can estimate your
                monthly cost.
              </div>
            </div>
          </div>

          <div className="howStep">
            <div className="howNum">2</div>
            <div>
              <div className="howStepTitle">Compare plans</div>
              <div className="howStepText">
                We rank available options by effective price and show estimated
                savings versus a baseline.
              </div>
            </div>
          </div>

          <div className="howStep">
            <div className="howNum">3</div>
            <div>
              <div className="howStepTitle">Get a recommendation</div>
              <div className="howStepText">
                Choose a priority like lowest cost, closest, or most reliable
                and we highlight the best match.
              </div>
            </div>
          </div>
        </div>

        <div className="howNote">
          Estimates are informational. Your exact bill can vary based on fees,
          time-of-use rates, and provider terms.
        </div>
      </div>

      {/* SPOTLIGHT */}
      {spotlight ? (
        <div className="spotlight">
          <div className="spotlightTitle">Recommended option</div>

          <div className="spotlightMain">
            <div>
              <div className="spotlightName">{spotlight.option.provider_name}</div>
              <p className="spotlightReason">
                Best match based on your priority and the effective price score.
              </p>
            </div>

            <div className="savingsViz">
              {(() => {
                const recommendedMonthly = Number(spotlight.monthly_cost);
                const savings = Number(spotlight.savings_vs_baseline);

                if (!Number.isFinite(recommendedMonthly) || !Number.isFinite(savings))
                  return null;

                const baselineMonthly = recommendedMonthly + savings;
                const maxVal = Math.max(baselineMonthly, recommendedMonthly, 1);

                const baselinePct = Math.round((baselineMonthly / maxVal) * 100);
                const recommendedPct = Math.round((recommendedMonthly / maxVal) * 100);

                const yearlySavings = savings * 12;

                return (
                  <>
                    <div className="spotlightTitle">Savings comparison</div>

                    <div className="barsRow">
                      <div className="barItem">
                        <div className="barLabel">Baseline</div>
                        <div className="barTrack">
                          <div
                            className="barFill"
                            style={{
                              width: `${baselinePct}%`,
                              background: "rgba(148, 163, 184, 0.9)",
                            }}
                          />
                        </div>
                        <div className="barValue">{formatMoney(baselineMonthly)}</div>
                      </div>

                      <div className="barItem">
                        <div className="barLabel">Recommended</div>
                        <div className="barTrack">
                          <div
                            className="barFill"
                            style={{
                              width: `${recommendedPct}%`,
                              background: "rgba(34, 197, 94, 0.95)",
                            }}
                          />
                        </div>
                        <div className="barValue">{formatMoney(recommendedMonthly)}</div>
                      </div>
                    </div>

                    <div className="smallHint">
                      Estimated savings: {formatMoney(savings)} per month (
                      {formatMoney(yearlySavings)} per year).
                    </div>
                  </>
                );
              })()}
            </div>

            <Badge text="Recommended" />
          </div>

          <div className="kpis">
            <div className="kpi">
              <div className="kpiLabel">Effective price</div>
              <div className="kpiValue">{formatPricePerKwh(spotlight.effective_price)}</div>
            </div>

            <div className="kpi">
              <div className="kpiLabel">Monthly cost</div>
              <div className="kpiValue">{formatMoney(spotlight.monthly_cost)}</div>
            </div>

            <div className="kpi">
              <div className="kpiLabel">Savings vs baseline</div>
              <div className="kpiValue">{formatMoney(spotlight.savings_vs_baseline)}</div>
            </div>
          </div>
        </div>
      ) : null}

      {/* OPTIONS TABLE */}
      {options ? (
        <div className="card" style={{ marginTop: "18px" }}>
          <h2 style={{ marginTop: 0 }}>Ranked Options</h2>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
                  <th style={{ padding: "10px 8px" }}>Provider</th>
                  <th style={{ padding: "10px 8px" }}>Plan</th>
                  <th style={{ padding: "10px 8px" }}>Effective price</th>
                  <th style={{ padding: "10px 8px" }}>Monthly cost</th>
                  <th style={{ padding: "10px 8px" }}>Savings</th>
                  <th style={{ padding: "10px 8px" }}>Badges</th>
                </tr>
              </thead>
              <tbody>
                {options.map((row) => {
                  const isRec = row.is_recommended;
                  return (
                    <tr
                      key={row.option.id}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        background: isRec ? "#eff6ff" : "transparent",
                      }}
                    >
                      <td style={{ padding: "10px 8px" }}>{row.option.provider_name}</td>
                      <td style={{ padding: "10px 8px" }}>{row.option.utility_plan_name}</td>
                      <td style={{ padding: "10px 8px" }}>
                        {formatPricePerKwh(row.effective_price)}
                      </td>
                      <td style={{ padding: "10px 8px" }}>{formatMoney(row.monthly_cost)}</td>
                      <td style={{ padding: "10px 8px" }}>
                        {formatMoney(row.savings_vs_baseline)}
                      </td>
                      <td style={{ padding: "10px 8px" }}>
                        {isRec ? <Badge text="Recommended" /> : null}
                        {(row.badges || []).map((b) => (
                          <Badge key={b} text={b} />
                        ))}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* RECOMMENDATION CARD */}
      {recommendation ? (
        <div className="card" style={{ marginTop: "18px" }}>
          <h2 style={{ marginTop: 0 }}>Recommendation</h2>

          <div style={{ marginTop: "10px" }}>
            <div style={{ fontSize: "16px", marginBottom: "6px" }}>
              {recommendation.recommended_option?.option?.provider_name}
            </div>

            <div style={{ color: "#475569", marginBottom: "12px" }}>
              {recommendation.reason}
            </div>

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <Badge
                text={`Plan: ${recommendation.recommended_option?.option?.utility_plan_name}`}
              />
              <Badge
                text={`Effective: ${formatPricePerKwh(
                  recommendation.recommended_option?.effective_price
                )}`}
              />
              <Badge
                text={`Monthly: ${formatMoney(recommendation.recommended_option?.monthly_cost)}`}
              />
              <Badge
                text={`Savings: ${formatMoney(
                  recommendation.recommended_option?.savings_vs_baseline
                )}`}
              />
            </div>
          </div>
        </div>
      ) : null}

      {/* FAQs (title only, no “Trust”) */}
      <div className="faq">
        <div className="faqHeader">
          <h2 className="faqTitle">FAQs</h2>
          <p className="faqSubtitle">
            Clear answers so you understand how SolarShare estimates costs and savings.
          </p>
        </div>

        <details className="faqItem">
          <summary className="faqQ">How does SolarShare calculate savings?</summary>
          <div className="faqA">
            We estimate monthly cost for each option using your monthly kWh usage and
            the option’s effective price. Savings are shown as the difference between
            a baseline estimate and the option estimate.
          </div>
        </details>

        <details className="faqItem">
          <summary className="faqQ">What is the baseline?</summary>
          <div className="faqA">
            The baseline is an estimated monthly cost used as a comparison point. It
            helps you quickly see whether an option is likely to cost more or less.
          </div>
        </details>

        <details className="faqItem">
          <summary className="faqQ">Why might my real bill be different?</summary>
          <div className="faqA">
            Bills can vary due to provider fees, taxes, time-of-use rates, and plan
            terms. SolarShare provides estimates for comparison, not an exact bill.
          </div>
        </details>

        <details className="faqItem">
          <summary className="faqQ">Do you store my location or usage?</summary>
          <div className="faqA">
            In this version, inputs are used only to request results and are not
            stored after a refresh. If accounts are added later, the app will show
            a clear privacy explanation before saving anything.
          </div>
        </details>
      </div>

      {/* FOOTER */}
      <footer className="footer">
        <div className="footerInner">
          <div className="footerLeft">
            <div className="footerBrand">SolarShare</div>
            <div className="footerMeta">© {year} Educational project</div>
          </div>

          <div className="footerRight">
            <a className="footerLink" href={GITHUB_REPO_URL} target="_blank" rel="noreferrer">
              GitHub
            </a>
            <span className="footerDot">•</span>
            <span className="footerMeta">Estimates may vary by provider terms</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
