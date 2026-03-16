// Pricing page communicating business model and customer economics with visual cards.
import { ArrowRightLeft, ChartNoAxesCombined, WalletCards } from "lucide-react";
import { MotionReveal } from "@/components/MotionReveal";
import { SectionTitle } from "@/components/SectionTitle";

const pricingCards = [
  {
    title: "Customer Experience",
    value: "$0",
    detail: "No fee for comparison workflow",
    icon: WalletCards
  },
  {
    title: "Platform Margin",
    value: "2-5%",
    detail: "Allocation margin paid by developers",
    icon: ChartNoAxesCombined
  },
  {
    title: "Credit Flow",
    value: "90-95%",
    detail: "Household payment share of credit value",
    icon: ArrowRightLeft
  }
];

export default function PricingPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="Pricing"
        title="A scalable, asset-light business model"
        subtitle="Designed for household value and developer-aligned infrastructure revenue."
      />

      <section className="mt-10 grid gap-5 md:grid-cols-3">
        {pricingCards.map((card, index) => {
          const Icon = card.icon;
          return (
            <MotionReveal key={card.title} delay={index * 0.07}>
              <article className="rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
                <div className="inline-flex rounded-xl bg-solarBlue-50 p-2 text-solarBlue-700">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-3 text-lg font-semibold text-solarBlue-900">{card.title}</h3>
                <p className="metric-value metric-accent-green mt-2 text-4xl font-semibold text-energyGreen-700">{card.value}</p>
                <p className="mt-2 text-sm text-solarBlue-900/65">{card.detail}</p>
              </article>
            </MotionReveal>
          );
        })}
      </section>

      <section className="mt-10 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
        <h3 className="text-xl font-semibold text-solarBlue-900">Assumptions and disclosure</h3>
        <div className="mt-4 grid gap-3 text-sm text-solarBlue-900/70 md:grid-cols-2">
          <p>Output estimates depend on utility tariffs and territory program rules.</p>
          <p>Live data availability may vary by external API uptime and update cycles.</p>
          <p>Fallback-safe mode remains transparent whenever live sources are unavailable.</p>
          <p>Final enrollment outcomes depend on eligibility and developer supply constraints.</p>
        </div>
      </section>
    </main>
  );
}
