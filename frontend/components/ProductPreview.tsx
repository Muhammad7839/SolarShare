// High-fidelity SaaS-style UI preview section showing dashboard, comparison, and savings views.
import { SlidersHorizontal, Sparkles, TrendingUp } from "lucide-react";

export function ProductPreview() {
  return (
    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="tilt-card rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card transition-transform duration-500 hover:-translate-y-1 hover:rotate-[0.35deg]">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold text-solarBlue-900">Decision Score Dashboard</h3>
          <span className="rounded-full bg-energyGreen-100 px-3 py-1 text-xs font-bold text-energyGreen-700">Live Mode</span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl bg-solarBlue-50 p-4">
            <p className="text-sm font-semibold text-solarBlue-700">Price Score</p>
            <p className="metric-value mt-2 text-3xl font-semibold text-solarBlue-900">88</p>
          </article>
          <article className="rounded-2xl bg-energyGreen-100/70 p-4">
            <p className="text-sm font-semibold text-energyGreen-700">Reliability</p>
            <p className="metric-value metric-accent-green mt-2 text-3xl font-semibold text-solarBlue-900">92%</p>
          </article>
          <article className="rounded-2xl bg-sunOrange-100 p-4">
            <p className="text-sm font-semibold text-sunOrange-700">Distance Fit</p>
            <p className="metric-value metric-accent-orange mt-2 text-3xl font-semibold text-solarBlue-900">12 mi</p>
          </article>
        </div>

        <div className="mt-6 rounded-2xl border border-solarBlue-100 p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-solarBlue-900">Monthly Savings Projection</p>
            <TrendingUp className="size-4 text-energyGreen-700" />
          </div>
          <div className="space-y-3">
            {[28, 35, 42, 54, 63, 71].map((value, index) => (
              <div key={value} className="grid grid-cols-[44px_1fr] items-center gap-3">
                <span className="text-xs font-semibold text-solarBlue-900/60">M{index + 1}</span>
                <div className="h-2 rounded-full bg-solarBlue-50">
                  <div className="h-2 rounded-full bg-gradient-to-r from-solarBlue-500 to-energyGreen-500" style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-6">
        <article className="tilt-card rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card transition-transform duration-500 hover:-translate-y-1 hover:-rotate-[0.35deg]">
          <div className="flex items-center gap-2 text-solarBlue-700">
            <SlidersHorizontal className="size-5" />
            <p className="text-sm font-bold uppercase tracking-[0.14em]">Comparison Interface</p>
          </div>
          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-solarBlue-100 p-3">
              <p className="text-sm font-semibold text-solarBlue-900">Long Island Community Solar</p>
              <p className="text-sm text-solarBlue-900/60">$112/month • 93% reliability • 9.8 miles</p>
            </div>
            <div className="rounded-xl border border-solarBlue-100 p-3">
              <p className="text-sm font-semibold text-solarBlue-900">Northeast Shared Solar</p>
              <p className="text-sm text-solarBlue-900/60">$118/month • 90% reliability • 14.2 miles</p>
            </div>
          </div>
        </article>

        <article className="tilt-card rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card transition-transform duration-500 hover:-translate-y-1 hover:rotate-[0.35deg]">
          <div className="flex items-center gap-2 text-energyGreen-700">
            <Sparkles className="size-5" />
            <p className="text-sm font-bold uppercase tracking-[0.14em]">Savings Calculator</p>
          </div>
          <p className="metric-value metric-accent-green mt-3 text-2xl font-semibold text-solarBlue-900">$740/year estimated savings</p>
          <input type="range" min="1" max="10" value="6" readOnly className="mt-5 w-full accent-energyGreen-500" />
          <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-solarBlue-900/60">Projection confidence: high</p>
        </article>
      </div>
    </section>
  );
}
