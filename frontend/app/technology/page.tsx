// Technology page presenting decision engine logic through visual weighted scoring cards.
import { Gauge, MapPin, ShieldCheck, Triangle } from "lucide-react";
import { MotionReveal } from "@/components/MotionReveal";
import { SectionTitle } from "@/components/SectionTitle";

const factors = [
  { name: "Price", icon: Gauge, weight: "45%", color: "from-solarBlue-500 to-solarBlue-700" },
  { name: "Reliability", icon: ShieldCheck, weight: "35%", color: "from-energyGreen-500 to-energyGreen-700" },
  { name: "Distance", icon: MapPin, weight: "20%", color: "from-sunOrange-500 to-sunOrange-700" }
];

export default function TechnologyPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="Technology"
        title="Decision intelligence built for transparency"
        subtitle="SolarShare evaluates options across three core factors and exposes the logic directly to users."
      />

      <section className="mt-10 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div className="grid place-items-center">
            <div className="relative size-72">
              <div className="absolute inset-0 grid place-items-center rounded-full bg-solarBlue-50 text-solarBlue-700">
                <Triangle className="size-32" />
              </div>
              <span className="absolute left-5 top-5 rounded-full bg-solarBlue-700 px-3 py-1 text-xs font-bold text-white">Price</span>
              <span className="absolute right-5 top-5 rounded-full bg-energyGreen-700 px-3 py-1 text-xs font-bold text-white">Reliability</span>
              <span className="absolute bottom-5 left-1/2 -translate-x-1/2 rounded-full bg-sunOrange-700 px-3 py-1 text-xs font-bold text-white">Distance</span>
            </div>
          </div>

          <div className="grid gap-4">
            {factors.map((factor, index) => {
              const Icon = factor.icon;
              return (
                <MotionReveal key={factor.name} delay={index * 0.07}>
                  <article className="rounded-2xl border border-solarBlue-100 bg-solarBlue-50/60 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex rounded-xl bg-gradient-to-br p-2 text-white ${factor.color}`}>
                          <Icon className="size-5" />
                        </span>
                        <h3 className="text-lg font-semibold text-solarBlue-900">{factor.name}</h3>
                      </div>
                      <span className="metric-value rounded-full bg-white px-3 py-1 text-sm font-bold text-solarBlue-700">
                        {factor.weight}
                      </span>
                    </div>
                  </article>
                </MotionReveal>
              );
            })}
          </div>
        </div>
      </section>
    </main>
  );
}
