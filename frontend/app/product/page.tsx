// Product page featuring live app interaction and dashboard-style interface storytelling.
import { ComparisonTool } from "@/components/ComparisonTool";
import { MotionReveal } from "@/components/MotionReveal";
import { ProductPreview } from "@/components/ProductPreview";
import { SectionTitle } from "@/components/SectionTitle";

export default function ProductPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="Product"
        title="A modern clean-energy decision platform"
        subtitle="Built for customer conversion, operational clarity, and investor confidence."
      />

      <div className="mt-10">
        <ComparisonTool />
      </div>

      <div className="mt-14">
        <SectionTitle
          eyebrow="UI Preview"
          title="Dashboard views that feel like real SaaS"
          subtitle="Decision score, comparison engine, and savings projection in one polished interface."
        />
        <div className="mt-8">
          <ProductPreview />
        </div>
      </div>

      <MotionReveal className="mt-12 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-solarBlue-700/70">Designed for speed</p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl bg-solarBlue-50 p-4">
            <h3 className="text-base font-semibold text-solarBlue-900">Fast onboarding</h3>
            <p className="mt-1 text-sm text-solarBlue-900/70">Location + usage + priority in under one minute.</p>
          </article>
          <article className="rounded-2xl bg-energyGreen-100/70 p-4">
            <h3 className="text-base font-semibold text-solarBlue-900">Transparent outputs</h3>
            <p className="mt-1 text-sm text-solarBlue-900/70">See source-backed context and recommendation reason.</p>
          </article>
          <article className="rounded-2xl bg-sunOrange-100 p-4">
            <h3 className="text-base font-semibold text-solarBlue-900">Conversion-ready UX</h3>
            <p className="mt-1 text-sm text-solarBlue-900/70">Exportable summaries for household and advisor decisions.</p>
          </article>
        </div>
      </MotionReveal>
    </main>
  );
}
