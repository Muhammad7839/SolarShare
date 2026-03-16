// How It Works page with a visual four-step flow and ecosystem-level explanation.
import { ArrowRight, Factory, House, Network, Power } from "lucide-react";
import { MotionReveal } from "@/components/MotionReveal";
import { SectionTitle } from "@/components/SectionTitle";

const steps = [
  { title: "Solar farms generate electricity", icon: Factory },
  { title: "Utilities calculate solar credits", icon: Power },
  { title: "SolarShare allocates credits", icon: Network },
  { title: "Households receive savings", icon: House }
];

export default function HowItWorksPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="How It Works"
        title="A clear four-step clean-energy workflow"
        subtitle="From generation to bill savings, SolarShare coordinates the financial allocation layer."
      />

      <section className="mt-10 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
        <div className="grid gap-5 xl:grid-cols-[repeat(4,minmax(0,1fr))] xl:items-center">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <MotionReveal key={step.title} delay={index * 0.08}>
                <article className="flex items-center gap-4 xl:block xl:text-center">
                  <div className="mx-auto inline-flex size-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-solarBlue-700 to-solarBlue-500 text-white shadow-glow">
                    <Icon className="size-6" />
                  </div>
                  <h3 className="mt-2 text-base font-semibold text-solarBlue-900">{step.title}</h3>
                  {index < steps.length - 1 ? <ArrowRight className="mx-auto mt-3 hidden text-solarBlue-500 xl:block" /> : null}
                </article>
              </MotionReveal>
            );
          })}
        </div>
      </section>

      <section className="mt-12 grid gap-5 md:grid-cols-2">
        <MotionReveal>
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-6 shadow-card">
            <h3 className="text-xl font-semibold text-solarBlue-900">Customer value</h3>
            <ul className="mt-4 space-y-2 text-sm text-solarBlue-900/70">
              <li>No rooftop installation required</li>
              <li>No utility provider switch required</li>
              <li>Transparent savings and risk visibility</li>
            </ul>
          </article>
        </MotionReveal>
        <MotionReveal delay={0.08}>
          <article className="rounded-2xl border border-solarBlue-100 bg-white p-6 shadow-card">
            <h3 className="text-xl font-semibold text-solarBlue-900">Platform value</h3>
            <ul className="mt-4 space-y-2 text-sm text-solarBlue-900/70">
              <li>Faster developer allocation velocity</li>
              <li>Repeatable utility-compatible workflow</li>
              <li>Scalable multi-territory operations</li>
            </ul>
          </article>
        </MotionReveal>
      </section>
    </main>
  );
}
