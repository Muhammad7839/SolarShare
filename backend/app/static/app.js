// SolarShare browser client: drives live comparisons, advanced planning, and customer scenario workflows.
(function () {
  const STORAGE_KEY = "solarshare_customer_preferences_v1";
  const HISTORY_KEY = "solarshare_customer_history_v1";

  const form = document.getElementById("recommendation-form");
  const submitButton = document.getElementById("submit-button");
  const heroCompareCta = document.querySelector("a[href='#recommendation-form']");
  const loadingState = document.getElementById("loading-state");
  const liveStatusPill = document.getElementById("live-status-pill");
  const filterPanel = document.getElementById("filter-panel");
  const maxDistanceInput = document.getElementById("max-distance");
  const maxDistanceValue = document.getElementById("max-distance-value");
  const minReliabilityInput = document.getElementById("min-reliability");
  const minReliabilityValue = document.getElementById("min-reliability-value");
  const sortSelect = document.getElementById("sort-options");

  const errorBanner = document.getElementById("error-banner");
  const insightsPanel = document.getElementById("insights-panel");
  const insightsContent = document.getElementById("insights-content");
  const marketContextPanel = document.getElementById("market-context-panel");
  const marketContextContent = document.getElementById("market-context-content");
  const recommendationPanel = document.getElementById("recommendation-panel");
  const recommendationContent = document.getElementById("recommendation-content");
  const optionsPanel = document.getElementById("options-panel");
  const optionsList = document.getElementById("options-list");
  const noResults = document.getElementById("no-results");

  const comparePanel = document.getElementById("compare-panel");
  const compareContent = document.getElementById("compare-content");
  const plannerPanel = document.getElementById("planner-panel");
  const plannerYears = document.getElementById("planner-years");
  const plannerYearsValue = document.getElementById("planner-years-value");
  const plannerInflation = document.getElementById("planner-inflation");
  const plannerInflationValue = document.getElementById("planner-inflation-value");
  const plannerInsights = document.getElementById("planner-insights");
  const plannerChart = document.getElementById("planner-chart");
  const stepper = document.getElementById("comparison-stepper");
  const stepPanels = Array.from(document.querySelectorAll("[data-step-panel]"));
  const stepChips = Array.from(document.querySelectorAll("[data-step-chip]"));
  const nextStepButtons = Array.from(document.querySelectorAll("[data-next-step]"));
  const prevStepButtons = Array.from(document.querySelectorAll("[data-prev-step]"));
  const previewLocationButton = document.getElementById("preview-location-btn");
  const locationPreviewCard = document.getElementById("location-preview-card");
  const locationPreviewText = document.getElementById("location-preview-text");
  const reviewSummary = document.getElementById("review-summary");

  const historyList = document.getElementById("history-list");
  const saveScenarioButton = document.getElementById("save-scenario-btn");
  const downloadReportButton = document.getElementById("download-report-btn");
  const shareSummaryButton = document.getElementById("share-summary-btn");
  const demoRequestForm = document.getElementById("demo-request-form");
  const demoStatus = document.getElementById("demo-status");
  const testimonialCard = document.getElementById("testimonial-card");
  const testimonialPrev = document.getElementById("testimonial-prev");
  const testimonialNext = document.getElementById("testimonial-next");

  let cachedOptions = [];
  let cachedRecommendation = null;
  let cachedMarketContext = null;
  let cachedRequestPayload = null;
  let selectedOptionIds = new Set();
  let testimonialIndex = 0;
  let testimonialTimer = null;
  let currentStep = 1;

  const TESTIMONIALS = [
    {
      quote:
        "SolarShare helped us compare three options quickly and pick the one with the best long-term savings.",
      author: "M. Carter",
      role: "Homeowner, New York",
    },
    {
      quote:
        "The Comparison Lab is genuinely useful. We reviewed different tradeoffs before choosing a plan.",
      author: "J. Bennett",
      role: "Energy Advisor",
    },
    {
      quote:
        "The report export made it easy to share assumptions with our family decision group.",
      author: "S. Diaz",
      role: "Customer, Boston",
    },
  ];

  function escapeHtml(value) {
    const text = String(value ?? "");
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function showError(message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove("hidden");
    errorBanner.classList.remove("notice");
  }

  function showNotice(message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove("hidden");
    errorBanner.classList.add("notice");
    window.setTimeout(() => {
      clearError();
    }, 2600);
  }

  function setLiveStatus(context) {
    if (!liveStatusPill || !context) {
      return;
    }
    if (context.using_fallback) {
      liveStatusPill.textContent = "Data mode: fallback-safe";
      liveStatusPill.style.background = "#fff6e8";
      liveStatusPill.style.borderColor = "#f0d5a2";
      liveStatusPill.style.color = "#7f4a00";
      return;
    }
    liveStatusPill.textContent = "Data mode: live";
    liveStatusPill.style.background = "#eefcf3";
    liveStatusPill.style.borderColor = "#b7e2c8";
    liveStatusPill.style.color = "#18663c";
  }

  function clearError() {
    errorBanner.textContent = "";
    errorBanner.classList.add("hidden");
    errorBanner.classList.remove("notice");
  }

  function formatCurrency(value) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }).format(value);
  }

  function formatPercent(value) {
    return `${Math.round(Number(value || 0) * 100)}%`;
  }

  function trackEvent(eventName, metadata) {
    if (typeof window.solarshareTrackEvent === "function") {
      window.solarshareTrackEvent(eventName, metadata || {});
    }
  }

  function createIdempotencyKey(prefix) {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function readJsonStorage(key, fallbackValue) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallbackValue;
    } catch (error) {
      return fallbackValue;
    }
  }

  function saveJsonStorage(key, payload) {
    try {
      localStorage.setItem(key, JSON.stringify(payload));
    } catch (error) {
      // Ignore storage errors for private mode and constrained browsers.
    }
  }

  function readPreferences() {
    return readJsonStorage(STORAGE_KEY, null);
  }

  function savePreferences(payload) {
    saveJsonStorage(STORAGE_KEY, payload);
  }

  function readHistory() {
    return readJsonStorage(HISTORY_KEY, []);
  }

  function saveHistory(items) {
    saveJsonStorage(HISTORY_KEY, items.slice(0, 8));
  }

  function updateFilterLabels() {
    maxDistanceValue.textContent = String(maxDistanceInput.value);
    minReliabilityValue.textContent = `${Number(minReliabilityInput.value)}%`;
  }

  function updatePlannerLabels() {
    plannerYearsValue.textContent = String(plannerYears.value);
    plannerInflationValue.textContent = `${Number(plannerInflation.value).toFixed(1)}%`;
  }

  function setStep(step) {
    currentStep = step;
    stepPanels.forEach((panel) => {
      const panelStep = Number(panel.getAttribute("data-step-panel"));
      panel.classList.toggle("active", panelStep === step);
    });
    stepChips.forEach((chip) => {
      const chipStep = Number(chip.getAttribute("data-step-chip"));
      chip.classList.toggle("active", chipStep === step);
      chip.classList.toggle("completed", chipStep < step);
    });
  }

  function validateStep(step) {
    const location = document.getElementById("location").value.trim();
    const zipCode = document.getElementById("zip-code").value.trim();
    const usage = Number(document.getElementById("monthly-usage-kwh").value);

    if (step === 1) {
      if (!location && !zipCode) {
        showError("Please enter a location or ZIP code.");
        return false;
      }
      if (zipCode && !/^\d{5}(?:-\d{4})?$/.test(zipCode)) {
        showError("ZIP code must be 5 digits or ZIP+4 format.");
        return false;
      }
      return true;
    }

    if (step === 2) {
      if (!Number.isFinite(usage) || usage <= 0) {
        showError("Please enter a valid monthly usage number greater than 0.");
        return false;
      }
      return true;
    }
    return true;
  }

  function updateReviewSummary() {
    const location = document.getElementById("location").value.trim();
    const zipCode = document.getElementById("zip-code").value.trim();
    const usage = document.getElementById("monthly-usage-kwh").value.trim();
    const priority = document.getElementById("priority").value;
    const locationLabel = location || "Not provided";
    const zipLabel = zipCode || "Not provided";
    const usageLabel = usage || "Not provided";
    reviewSummary.textContent = `Location: ${locationLabel} | ZIP: ${zipLabel} | Usage: ${usageLabel} kWh | Priority: ${priority}`;
  }

  async function resolveLocationPreview() {
    const payload = {
      location: document.getElementById("location").value.trim(),
      zip_code: document.getElementById("zip-code").value.trim() || null,
    };
    if (!payload.location && !payload.zip_code) {
      showError("Enter a location or ZIP code to preview.");
      return;
    }
    if (payload.zip_code && !/^\d{5}(?:-\d{4})?$/.test(payload.zip_code)) {
      showError("ZIP code must be 5 digits or ZIP+4 format.");
      return;
    }
    try {
      const response = await fetch("/location-resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error("Unable to resolve location.");
      }
      const resolved = await response.json();
      const fallbackText = resolved.using_fallback ? "Fallback" : "Live";
      locationPreviewText.textContent = `${resolved.resolved_location} | ${resolved.city || "City n/a"}, ${
        resolved.county || "County n/a"
      }, ${resolved.state_code || "State n/a"} ${resolved.postal_code || ""} | Confidence: ${Math.round(
        Number(resolved.confidence || 0) * 100
      )}% | Source: ${fallbackText}`;
      locationPreviewCard.classList.remove("hidden");
      trackEvent("location_preview_success", { using_fallback: Boolean(resolved.using_fallback) });
    } catch (error) {
      locationPreviewText.textContent = "Unable to resolve location preview.";
      locationPreviewCard.classList.remove("hidden");
      trackEvent("location_preview_error", {});
    }
  }

  function renderInsights(options, recommendation, requestPayload) {
    const recommendationItem = recommendation.recommended_option;
    const annualSavings = recommendationItem.savings_vs_baseline * 12;
    const avgMonthlyCost =
      options.reduce((sum, item) => sum + item.monthly_cost, 0) / Math.max(options.length, 1);
    const bestReliability = Math.max(...options.map((item) => item.option.reliability_score));
    const nearestDistance = Math.min(...options.map((item) => item.option.distance_miles));

    insightsContent.innerHTML = `
      <article class="insight-card">
        <h3>Estimated Annual Savings</h3>
        <p>${formatCurrency(annualSavings)}</p>
      </article>
      <article class="insight-card">
        <h3>Average Monthly Cost</h3>
        <p>${formatCurrency(avgMonthlyCost)}</p>
      </article>
      <article class="insight-card">
        <h3>Best Reliability Available</h3>
        <p>${formatPercent(bestReliability)}</p>
      </article>
      <article class="insight-card">
        <h3>Closest Option Distance</h3>
        <p>${nearestDistance.toFixed(1)} miles</p>
      </article>
    `;
    insightsPanel.classList.remove("hidden");

    savePreferences({
      location: requestPayload.location,
      zip_code: requestPayload.zip_code,
      monthly_usage_kwh: requestPayload.monthly_usage_kwh,
      priority: requestPayload.priority,
      max_distance: Number(maxDistanceInput.value),
      min_reliability: Number(minReliabilityInput.value),
      sort: sortSelect.value,
    });
  }

  function renderMarketContext(context, resolutionConfidence, fallbackReason) {
    const sourceList = (context.data_sources || []).map((value) => escapeHtml(value)).join(" | ");
    const sourceLinks = (context.source_urls || [])
      .map((url) => {
        const safeUrl = escapeHtml(url);
        return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${safeUrl}</a>`;
      })
      .join("<br />");
    const fallbackLabel = context.using_fallback ? "Fallback mode active" : "Live data active";
    const observedAt = context.observed_at_utc
      ? new Date(context.observed_at_utc).toLocaleString()
      : "Not available";
    const utilityPeriod = context.utility_rate_period || "Latest available period";
    const freshnessLabel = context.observed_at_utc
      ? `${Math.max(0, Math.round((Date.now() - new Date(context.observed_at_utc).getTime()) / 60000))} min ago`
      : "n/a";
    const cityLabel = context.city || "Not resolved";
    const stateLabel = context.state_code || "Not resolved";
    const countyLabel = context.county || "Not resolved";
    const postalLabel = context.postal_code || "Not resolved";
    marketContextContent.innerHTML = `
      <article class="insight-card">
        <h3>Resolved Location</h3>
        <p>${escapeHtml(context.resolved_location)}</p>
      </article>
      <article class="insight-card">
        <h3>City</h3>
        <p>${escapeHtml(cityLabel)}</p>
      </article>
      <article class="insight-card">
        <h3>State</h3>
        <p>${escapeHtml(stateLabel)}</p>
      </article>
      <article class="insight-card">
        <h3>County</h3>
        <p>${escapeHtml(countyLabel)}</p>
      </article>
      <article class="insight-card">
        <h3>Postal Code</h3>
        <p>${escapeHtml(postalLabel)}</p>
      </article>
      <article class="insight-card">
        <h3>Utility Price Baseline</h3>
        <p>${formatCurrency(context.utility_price_per_kwh)} / kWh</p>
      </article>
      <article class="insight-card">
        <h3>Solar Irradiance</h3>
        <p>${Number(context.avg_shortwave_radiation).toFixed(1)} W/m2 avg</p>
      </article>
      <article class="insight-card">
        <h3>Cloud Cover</h3>
        <p>${Number(context.avg_cloud_cover_pct).toFixed(1)}%</p>
      </article>
      <article class="insight-card">
        <h3>Coordinates</h3>
        <p>${Number(context.latitude).toFixed(4)}, ${Number(context.longitude).toFixed(4)}</p>
      </article>
      <article class="insight-card">
        <h3>Data Mode</h3>
        <p>${fallbackLabel}</p>
      </article>
      <article class="insight-card">
        <h3>Resolution Confidence</h3>
        <p>${Math.round(Number(resolutionConfidence || 0) * 100)}%</p>
      </article>
      <article class="insight-card">
        <h3>Fallback Reason</h3>
        <p>${escapeHtml(fallbackReason || "None")}</p>
      </article>
      <article class="insight-card">
        <h3>Data Freshness</h3>
        <p>${escapeHtml(freshnessLabel)}</p>
      </article>
      <article class="insight-card">
        <h3>Utility Rate Period</h3>
        <p>${escapeHtml(utilityPeriod)}</p>
      </article>
      <article class="insight-card">
        <h3>Observed At (UTC)</h3>
        <p>${escapeHtml(observedAt)}</p>
      </article>
      <article class="insight-card market-source-card">
        <h3>Sources</h3>
        <p>${sourceList || "internal-fallback"}</p>
        <p class="source-link-list">${sourceLinks || "No source links available"}</p>
      </article>
    `;
    marketContextPanel.classList.remove("hidden");
  }

  function renderRecommendation(payload, factorBreakdown) {
    const item = payload.recommended_option;
    const factors = factorBreakdown || { price: 0, reliability: 0, distance: 0 };
    recommendationContent.innerHTML = `
      <div class="option-card recommended">
        <span class="rank-chip">Top Match</span>
        <h3>${escapeHtml(item.option.provider_name)}</h3>
        <p><strong>Reason:</strong> ${escapeHtml(payload.reason)}</p>
        <p><strong>Plan:</strong> ${escapeHtml(item.option.utility_plan_name)}</p>
        <p><strong>Reliability:</strong> ${formatPercent(item.option.reliability_score)}</p>
        <p><strong>Distance:</strong> ${item.option.distance_miles.toFixed(1)} miles</p>
        <p><strong>Effective Price:</strong> ${formatCurrency(item.effective_price)} / kWh</p>
        <p><strong>Monthly Cost:</strong> ${formatCurrency(item.monthly_cost)}</p>
        <p><strong>Savings vs Baseline:</strong> ${formatCurrency(item.savings_vs_baseline)}</p>
        <p><strong>Why this recommendation:</strong> Price ${Math.round(factors.price * 100)}%, Reliability ${Math.round(
      factors.reliability * 100
    )}%, Distance ${Math.round(factors.distance * 100)}%</p>
      </div>
    `;
    recommendationPanel.classList.remove("hidden");
  }

  function renderOptions(options) {
    if (!options.length) {
      optionsList.innerHTML = "";
      noResults.classList.remove("hidden");
      optionsPanel.classList.remove("hidden");
      return;
    }

    noResults.classList.add("hidden");
    optionsList.innerHTML = options
      .map((item) => {
        const optionId = Number(item.option.id);
        const isSelected = selectedOptionIds.has(optionId);
        const badges = item.badges.map((badge) => `<span class="badge">${escapeHtml(badge)}</span>`).join("");
        return `
          <article class="option-card ${item.is_recommended ? "recommended" : ""}">
            <span class="rank-chip">Rank ${item.rank}</span>
            <h3>${escapeHtml(item.option.provider_name)}</h3>
            <p><strong>Plan:</strong> ${escapeHtml(item.option.utility_plan_name)}</p>
            <p><strong>Distance:</strong> ${item.option.distance_miles.toFixed(1)} miles</p>
            <p><strong>Reliability:</strong> ${formatPercent(item.option.reliability_score)}</p>
            <p><strong>Effective Price:</strong> ${formatCurrency(item.effective_price)} / kWh</p>
            <p><strong>Monthly Cost:</strong> ${formatCurrency(item.monthly_cost)}</p>
            <p><strong>Savings:</strong> ${formatCurrency(item.savings_vs_baseline)}</p>
            <div class="badge-row">${badges}</div>
            <button type="button" class="compare-btn ${isSelected ? "selected" : ""}" data-compare-id="${optionId}">
              ${isSelected ? "Selected for Lab" : "Add to Comparison Lab"}
            </button>
          </article>
        `;
      })
      .join("");
    optionsPanel.classList.remove("hidden");
  }

  function getFilteredOptionsForCurrentControls() {
    const maxDistance = Number(maxDistanceInput.value);
    const minReliability = Number(minReliabilityInput.value) / 100;
    const sortBy = sortSelect.value;

    let filtered = cachedOptions.filter(
      (item) => item.option.distance_miles <= maxDistance && item.option.reliability_score >= minReliability
    );

    if (sortBy === "monthly_cost") {
      filtered = [...filtered].sort((a, b) => a.monthly_cost - b.monthly_cost);
    } else if (sortBy === "savings") {
      filtered = [...filtered].sort((a, b) => b.savings_vs_baseline - a.savings_vs_baseline);
    } else if (sortBy === "distance") {
      filtered = [...filtered].sort((a, b) => a.option.distance_miles - b.option.distance_miles);
    } else if (sortBy === "reliability") {
      filtered = [...filtered].sort((a, b) => b.option.reliability_score - a.option.reliability_score);
    }

    return filtered;
  }

  function renderCompareLab() {
    const selected = cachedOptions.filter((item) => selectedOptionIds.has(Number(item.option.id)));
    if (!selected.length) {
      compareContent.innerHTML = `<p class="muted">No options selected yet. Click "Add to Comparison Lab" on any ranked option.</p>`;
      comparePanel.classList.remove("hidden");
      return;
    }

    compareContent.innerHTML = selected
      .map(
        (item) => `
          <article class="insight-card">
            <h3>${escapeHtml(item.option.provider_name)}</h3>
            <p><strong>Monthly:</strong> ${formatCurrency(item.monthly_cost)}</p>
            <p><strong>Savings:</strong> ${formatCurrency(item.savings_vs_baseline)}</p>
            <p><strong>Reliability:</strong> ${formatPercent(item.option.reliability_score)}</p>
            <p><strong>Distance:</strong> ${item.option.distance_miles.toFixed(1)} miles</p>
          </article>
        `
      )
      .join("");
    comparePanel.classList.remove("hidden");
  }

  function renderPlanner() {
    if (!cachedRecommendation || !cachedRequestPayload) {
      return;
    }
    const years = Number(plannerYears.value);
    const inflation = Number(plannerInflation.value) / 100;
    const monthlySavings = Number(cachedRecommendation.recommended_option.savings_vs_baseline);
    const firstYearSavings = monthlySavings * 12;

    let cumulative = 0;
    for (let year = 0; year < years; year += 1) {
      cumulative += firstYearSavings * Math.pow(1 + inflation, year);
    }

    const annualUsage = Number(cachedRequestPayload.monthly_usage_kwh) * 12;
    const renewableDisplacement = annualUsage * 0.65 * years;
    const co2AvoidedLbs = renewableDisplacement * 0.85;
    const treesEquivalent = co2AvoidedLbs / 48.0;

    plannerInsights.innerHTML = `
      <article class="insight-card">
        <h3>Year-1 Savings</h3>
        <p>${formatCurrency(firstYearSavings)}</p>
      </article>
      <article class="insight-card">
        <h3>${years}-Year Cumulative Savings</h3>
        <p>${formatCurrency(cumulative)}</p>
      </article>
      <article class="insight-card">
        <h3>CO2 Avoided Estimate</h3>
        <p>${Math.round(co2AvoidedLbs).toLocaleString()} lbs</p>
      </article>
      <article class="insight-card">
        <h3>Tree Equivalent</h3>
        <p>${Math.round(treesEquivalent).toLocaleString()} trees</p>
      </article>
    `;
    renderPlannerChart(years, firstYearSavings, inflation);
    plannerPanel.classList.remove("hidden");
  }

  function renderPlannerChart(years, firstYearSavings, inflation) {
    if (!plannerChart) {
      return;
    }
    let maxValue = 0;
    const series = [];
    for (let year = 1; year <= years; year += 1) {
      const value = firstYearSavings * Math.pow(1 + inflation, year - 1);
      series.push({ year, value });
      if (value > maxValue) {
        maxValue = value;
      }
    }
    plannerChart.innerHTML = series
      .map((point) => {
        const width = maxValue > 0 ? (point.value / maxValue) * 100 : 0;
        return `
          <div class="planner-bar-row">
            <span>Year ${point.year}</span>
            <div class="planner-bar-track">
              <div class="planner-bar-fill" style="width: ${width.toFixed(1)}%"></div>
            </div>
            <strong>${formatCurrency(point.value)}</strong>
          </div>
        `;
      })
      .join("");
  }

  function applyFiltersAndRender() {
    if (!cachedOptions.length) {
      return;
    }
    const filtered = getFilteredOptionsForCurrentControls();
    renderOptions(
      filtered.map((item, index) => ({
        ...item,
        rank: index + 1,
      }))
    );
    renderCompareLab();
    renderPlanner();
  }

  function buildScenarioSummary() {
    if (!cachedRecommendation || !cachedMarketContext || !cachedRequestPayload) {
      return null;
    }
    return {
      captured_at: new Date().toISOString(),
      request: cachedRequestPayload,
      market_context: cachedMarketContext,
      top_recommendation: cachedRecommendation.recommended_option.option.provider_name,
      top_reason: cachedRecommendation.reason,
      monthly_cost: cachedRecommendation.recommended_option.monthly_cost,
      monthly_savings: cachedRecommendation.recommended_option.savings_vs_baseline,
      selected_compare_ids: Array.from(selectedOptionIds),
    };
  }

  function saveCurrentScenario() {
    const summary = buildScenarioSummary();
    if (!summary) {
      showError("Run a comparison before saving a scenario.");
      return;
    }
    const history = readHistory();
    history.unshift(summary);
    saveHistory(history);
    renderHistoryList();
    showNotice("Scenario saved.");
  }

  function downloadCurrentReport() {
    const summary = buildScenarioSummary();
    if (!summary) {
      showError("Run a comparison before downloading a report.");
      return;
    }
    const blob = new Blob([JSON.stringify(summary, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `solarshare-report-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    showNotice("Report downloaded.");
  }

  async function copyShareSummary() {
    const summary = buildScenarioSummary();
    if (!summary) {
      showError("Run a comparison before copying summary.");
      return;
    }
    const locationLabel = summary.request.location || summary.request.zip_code || "location not set";
    const text = `SolarShare summary: ${locationLabel}, ${summary.request.monthly_usage_kwh} kWh/month, top option ${summary.top_recommendation}, monthly savings ${formatCurrency(summary.monthly_savings)}, data mode ${summary.market_context.using_fallback ? "fallback-safe" : "live"}.`;
    try {
      await navigator.clipboard.writeText(text);
      showNotice("Share summary copied.");
    } catch (error) {
      showError("Unable to copy summary in this browser.");
    }
  }

  function renderHistoryList() {
    const history = readHistory();
    if (!history.length) {
      historyList.innerHTML = `<p class="muted">No saved scenarios yet.</p>`;
      return;
    }
    historyList.innerHTML = history
      .map((entry, index) => {
        const dateLabel = new Date(entry.captured_at).toLocaleString();
        return `
          <article class="insight-card history-item">
            <h3>${escapeHtml(entry.request.location || entry.request.zip_code || "Location")} - ${escapeHtml(entry.request.priority)}</h3>
            <p>${dateLabel}</p>
            <p><strong>Top:</strong> ${escapeHtml(entry.top_recommendation)}</p>
            <p><strong>Savings:</strong> ${formatCurrency(entry.monthly_savings)}</p>
            <button type="button" class="history-load-btn" data-history-index="${index}">Load Scenario</button>
          </article>
        `;
      })
      .join("");
  }

  function loadHistoryScenario(index) {
    const history = readHistory();
    const entry = history[index];
    if (!entry) {
      return;
    }
    document.getElementById("location").value = entry.request.location || "";
    document.getElementById("zip-code").value = entry.request.zip_code || "";
    document.getElementById("monthly-usage-kwh").value = entry.request.monthly_usage_kwh;
    document.getElementById("priority").value = entry.request.priority;
    form.requestSubmit();
  }

  async function submitRequest(payload) {
    const response = await fetch("/live-comparison", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let message = "Request failed. Please check your inputs and try again.";
      try {
        const errorPayload = await response.json();
        if (errorPayload.detail) {
          if (typeof errorPayload.detail === "string") {
            message = errorPayload.detail;
          } else if (Array.isArray(errorPayload.detail) && errorPayload.detail.length > 0) {
            message = errorPayload.detail.map((entry) => entry.msg).join(", ");
          }
        }
      } catch (error) {
        // Keep fallback message.
      }
      throw new Error(message || "Request failed. Please try again.");
    }

    return response.json();
  }

  function loadPreferencesIntoForm() {
    const saved = readPreferences();
    if (!saved) {
      return;
    }
    if (saved.location) {
      document.getElementById("location").value = saved.location;
    }
    if (saved.zip_code) {
      document.getElementById("zip-code").value = saved.zip_code;
    }
    if (saved.monthly_usage_kwh) {
      document.getElementById("monthly-usage-kwh").value = saved.monthly_usage_kwh;
    }
    if (saved.priority) {
      document.getElementById("priority").value = saved.priority;
    }
    if (saved.max_distance) {
      maxDistanceInput.value = saved.max_distance;
    }
    if (saved.min_reliability) {
      minReliabilityInput.value = saved.min_reliability;
    }
    if (saved.sort) {
      sortSelect.value = saved.sort;
    }
    updateFilterLabels();
    updatePlannerLabels();
  }

  function wirePresetButtons() {
    document.querySelectorAll("[data-location]").forEach((button) => {
      button.addEventListener("click", () => {
        document.getElementById("location").value = button.getAttribute("data-location") || "";
      });
    });
    document.querySelectorAll("[data-usage]").forEach((button) => {
      button.addEventListener("click", () => {
        document.getElementById("monthly-usage-kwh").value = button.getAttribute("data-usage") || "";
      });
    });
  }

  function wireFilters() {
    [maxDistanceInput, minReliabilityInput, sortSelect].forEach((input) => {
      input.addEventListener("input", () => {
        updateFilterLabels();
        applyFiltersAndRender();
      });
      input.addEventListener("change", () => {
        updateFilterLabels();
        applyFiltersAndRender();
      });
    });
  }

  function wirePlannerControls() {
    [plannerYears, plannerInflation].forEach((input) => {
      input.addEventListener("input", () => {
        updatePlannerLabels();
        renderPlanner();
      });
      input.addEventListener("change", () => {
        updatePlannerLabels();
        renderPlanner();
      });
    });
  }

  function renderTestimonial(index) {
    if (!testimonialCard) {
      return;
    }
    const safeIndex = ((index % TESTIMONIALS.length) + TESTIMONIALS.length) % TESTIMONIALS.length;
    testimonialIndex = safeIndex;
    const testimonial = TESTIMONIALS[safeIndex];
    testimonialCard.innerHTML = `
      <h3>${escapeHtml(testimonial.quote)}</h3>
      <p class="testimonial-meta">${escapeHtml(testimonial.author)} - ${escapeHtml(testimonial.role)}</p>
    `;
  }

  function startTestimonialRotation() {
    if (testimonialTimer) {
      window.clearInterval(testimonialTimer);
    }
    testimonialTimer = window.setInterval(() => {
      renderTestimonial(testimonialIndex + 1);
    }, 5200);
  }

  function wireTestimonials() {
    if (!testimonialPrev || !testimonialNext) {
      return;
    }
    testimonialPrev.addEventListener("click", () => {
      renderTestimonial(testimonialIndex - 1);
      startTestimonialRotation();
    });
    testimonialNext.addEventListener("click", () => {
      renderTestimonial(testimonialIndex + 1);
      startTestimonialRotation();
    });
    renderTestimonial(0);
    startTestimonialRotation();
  }

  function wireRevealAnimations() {
    const targets = document.querySelectorAll(".panel, .metrics-strip");
    targets.forEach((element) => element.classList.add("reveal"));

    if (!("IntersectionObserver" in window)) {
      targets.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    targets.forEach((element) => observer.observe(element));
  }

  function wireComparisonStepper() {
    if (!stepper) {
      return;
    }

    setStep(1);

    nextStepButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const nextStep = Number(button.getAttribute("data-next-step"));
        if (!Number.isFinite(nextStep)) {
          return;
        }
        clearError();
        if (!validateStep(currentStep)) {
          trackEvent("comparison_step_validation_error", { step: currentStep });
          return;
        }
        trackEvent(
          currentStep === 1
            ? "comparison_step_location_complete"
            : currentStep === 2
              ? "comparison_step_usage_complete"
              : "comparison_step_review_complete",
          { step: currentStep }
        );
        if (nextStep === 3) {
          updateReviewSummary();
        }
        setStep(nextStep);
      });
    });

    prevStepButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const prevStep = Number(button.getAttribute("data-prev-step"));
        if (!Number.isFinite(prevStep)) {
          return;
        }
        setStep(prevStep);
      });
    });
  }

  async function submitDemoRequest(payload, idempotencyKey) {
    const sessionId = localStorage.getItem("solarshare_session_id_v1") || "anonymous";
    const response = await fetch("/demo-requests", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-session-id": sessionId,
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let message = "Unable to submit demo request.";
      try {
        const errorPayload = await response.json();
        if (typeof errorPayload.detail === "string") {
          message = errorPayload.detail;
        }
      } catch (error) {
        // Keep fallback message.
      }
      throw new Error(message);
    }
    return response.json();
  }

  function wireDemoRequestForm() {
    if (!(demoRequestForm instanceof HTMLFormElement) || !demoStatus) {
      return;
    }
    const submitButton = demoRequestForm.querySelector("button[type='submit']");
    let isSubmitting = false;
    demoRequestForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (isSubmitting) {
        return;
      }
      isSubmitting = true;
      demoStatus.textContent = "";
      if (submitButton instanceof HTMLButtonElement) {
        submitButton.disabled = true;
        submitButton.textContent = "Submitting...";
      }
      const payload = {
        name: (document.getElementById("demo-name") || {}).value || "",
        email: (document.getElementById("demo-email") || {}).value || "",
        organization: (document.getElementById("demo-organization") || {}).value || "",
        message: (document.getElementById("demo-message") || {}).value || "",
      };
      try {
        await submitDemoRequest(payload, createIdempotencyKey("demo"));
        demoRequestForm.reset();
        demoStatus.textContent = "Demo request received. We will follow up shortly.";
        trackEvent("demo_request_submit", { has_organization: Boolean(payload.organization) });
      } catch (error) {
        demoStatus.textContent = error.message || "Unable to submit demo request.";
        trackEvent("demo_request_error", {});
      } finally {
        isSubmitting = false;
        if (submitButton instanceof HTMLButtonElement) {
          submitButton.disabled = false;
          submitButton.textContent = "Submit Demo Request";
        }
      }
    });
  }

  function wireHeroCtaTracking() {
    if (!(heroCompareCta instanceof HTMLElement)) {
      return;
    }
    heroCompareCta.addEventListener("click", () => {
      trackEvent("hero_cta_click", {});
    });
  }

  optionsList.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const optionButton = target.closest("[data-compare-id]");
    if (!optionButton) {
      return;
    }
    const rawId = optionButton.getAttribute("data-compare-id");
    const optionId = Number(rawId);
    if (!Number.isFinite(optionId)) {
      return;
    }

    if (selectedOptionIds.has(optionId)) {
      selectedOptionIds.delete(optionId);
    } else {
      if (selectedOptionIds.size >= 3) {
        showError("Comparison Lab supports up to 3 options at a time.");
        return;
      }
      selectedOptionIds.add(optionId);
    }
    applyFiltersAndRender();
  });

  historyList.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const loadButton = target.closest("[data-history-index]");
    if (!loadButton) {
      return;
    }
    const index = Number(loadButton.getAttribute("data-history-index"));
    if (Number.isFinite(index)) {
      loadHistoryScenario(index);
    }
  });

  saveScenarioButton.addEventListener("click", saveCurrentScenario);
  downloadReportButton.addEventListener("click", downloadCurrentReport);
  shareSummaryButton.addEventListener("click", () => {
    copyShareSummary();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    submitButton.disabled = true;
    submitButton.textContent = "Comparing...";
    loadingState.classList.remove("hidden");
    selectedOptionIds = new Set();

    const payload = {
      location: document.getElementById("location").value.trim(),
      zip_code: document.getElementById("zip-code").value.trim(),
      monthly_usage_kwh: Number(document.getElementById("monthly-usage-kwh").value),
      priority: document.getElementById("priority").value,
    };

    if (!payload.location && !payload.zip_code) {
      showError("Please enter a location or ZIP code.");
      submitButton.disabled = false;
      submitButton.textContent = "Run Live Comparison";
      loadingState.classList.add("hidden");
      return;
    }
    if (payload.zip_code && !/^\d{5}(?:-\d{4})?$/.test(payload.zip_code)) {
      showError("ZIP code must be 5 digits or ZIP+4 format.");
      submitButton.disabled = false;
      submitButton.textContent = "Run Live Comparison";
      loadingState.classList.add("hidden");
      return;
    }
    if (!Number.isFinite(payload.monthly_usage_kwh) || payload.monthly_usage_kwh <= 0) {
      showError("Please enter a valid monthly usage number greater than 0.");
      submitButton.disabled = false;
      submitButton.textContent = "Run Live Comparison";
      loadingState.classList.add("hidden");
      return;
    }

    trackEvent("comparison_run", { priority: payload.priority });
    try {
      const { options, recommendation, market_context, resolution_confidence, fallback_reason, factor_breakdown } =
        await submitRequest(payload);
      cachedOptions = options;
      cachedRecommendation = recommendation;
      cachedMarketContext = market_context;
      cachedRequestPayload = payload;
      filterPanel.classList.remove("hidden");
      renderRecommendation(recommendation, factor_breakdown);
      renderInsights(options, recommendation, payload);
      renderMarketContext(market_context, resolution_confidence, fallback_reason);
      setLiveStatus(market_context);
      applyFiltersAndRender();
      trackEvent("comparison_success", {
        using_fallback: Boolean(market_context.using_fallback),
        confidence: Number(resolution_confidence || 0),
      });
    } catch (error) {
      showError(error.message || "Unable to load recommendations right now.");
      trackEvent("comparison_error", {});
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Run Live Comparison";
      loadingState.classList.add("hidden");
    }
  });

  loadPreferencesIntoForm();
  wirePresetButtons();
  wireComparisonStepper();
  wireFilters();
  wirePlannerControls();
  wireTestimonials();
  wireRevealAnimations();
  wireHeroCtaTracking();
  wireDemoRequestForm();
  if (previewLocationButton instanceof HTMLElement) {
    previewLocationButton.addEventListener("click", () => {
      clearError();
      resolveLocationPreview();
    });
  }
  renderHistoryList();
})();
