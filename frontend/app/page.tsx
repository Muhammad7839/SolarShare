// Home page combining investor storytelling with visual product credibility.
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EnergyScene3D } from "@/components/EnergyScene3D";
import { LogoOrbit3D } from "@/components/LogoOrbit3D";
import { MotionReveal } from "@/components/MotionReveal";
import { ProductPreview } from "@/components/ProductPreview";
import { SectionTitle } from "@/components/SectionTitle";
import { SystemFlow } from "@/components/SystemFlow";

export default function HomePage() {
  return (
    <main>
      <section className="hero-beam overflow-hidden px-5 py-14 md:py-16">
        <div className="mx-auto grid w-full max-w-7xl items-center gap-8 xl:grid-cols-[1.05fr_0.95fr]">
          <MotionReveal>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-solarBlue-50/80">SolarShare platform</p>
            <h1 className="mt-3 max-w-xl text-4xl font-semibold leading-[1.05] text-white md:text-5xl">
              Choose cleaner power with confidence and clarity.
            </h1>
            <p className="mt-4 max-w-xl text-base text-solarBlue-50/85 md:text-lg">
              SolarShare connects households to community solar through utility billing systems without rooftop installs.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/product"
                className="inline-flex items-center gap-2 rounded-full bg-sunOrange-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-sunOrange-700"
              >
                Start Comparison
                <ArrowRight className="size-4" />
              </Link>
              <Link
                href="/how-it-works"
                className="rounded-full border border-white/45 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                See How It Works
              </Link>
            </div>
          </MotionReveal>

          <MotionReveal delay={0.08} className="rounded-3xl border border-white/20 bg-white/10 p-4 backdrop-blur-xl">
            <div className="mb-4 flex justify-center">
              <LogoOrbit3D />
            </div>
            <SystemFlow />
            <div className="mt-4">
              <EnergyScene3D />
            </div>
          </MotionReveal>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 py-14">
        <div className="grid gap-5 md:grid-cols-3">
          {[
            "Enter location or ZIP and monthly usage",
            "Compare real options by cost, reliability, and distance",
            "Get a recommendation with trust signals"
          ].map((step, index) => (
            <MotionReveal key={step} delay={index * 0.06}>
              <article className="rounded-2xl border border-solarBlue-100 bg-white p-5 shadow-card">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-solarBlue-700/75">Step {index + 1}</p>
                <h2 className="mt-3 text-lg font-semibold text-solarBlue-900">{step}</h2>
              </article>
            </MotionReveal>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 pb-20">
        <SectionTitle
          eyebrow="Live Product Preview"
          title="Run comparison from the Product page"
          subtitle="Home is intentionally lightweight. Product, Technology, Pricing, and About now hold their own details."
        />
        <div className="mt-8">
          <ProductPreview />
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/product"
            className="inline-flex items-center gap-2 rounded-full bg-solarBlue-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-solarBlue-900"
          >
            Go to Product
            <ArrowRight className="size-4" />
          </Link>
          <Link
            href="/contact"
            className="rounded-full border border-solarBlue-200 bg-white px-6 py-3 text-sm font-semibold text-solarBlue-700 transition hover:bg-solarBlue-50"
          >
            Contact Team
          </Link>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 pb-24">
        <MotionReveal>
          <article className="rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
            <h2 className="text-2xl font-semibold text-solarBlue-900">Need details?</h2>
            <p className="mt-2 text-sm text-solarBlue-900/70">
              Product, Technology, Pricing, and About now hold all deep-dive content. Home stays action-first.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/technology"
                className="rounded-full border border-solarBlue-200 bg-white px-5 py-2.5 text-sm font-semibold text-solarBlue-700 transition hover:bg-solarBlue-50"
              >
                View Technology
              </Link>
              <Link
                href="/pricing"
                className="rounded-full border border-solarBlue-200 bg-white px-5 py-2.5 text-sm font-semibold text-solarBlue-700 transition hover:bg-solarBlue-50"
              >
                View Pricing
              </Link>
            </div>
          </article>
        </MotionReveal>
      </section>
    </main>
  );
}
