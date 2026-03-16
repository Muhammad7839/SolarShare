// About page highlighting team, strategy, and venture-grade execution narrative.
import { MotionReveal } from "@/components/MotionReveal";
import { SectionTitle } from "@/components/SectionTitle";

const team = [
  {
    name: "Muhammad Imran",
    role: "Backend systems and platform architecture"
  },
  {
    name: "Dieunie Gousse",
    role: "Product and frontend experience"
  },
  {
    name: "Stefanie Karayoff",
    role: "Strategy and regulatory coordination"
  }
];

export default function AboutPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="About"
        title="A cross-functional team for clean-energy allocation infrastructure"
        subtitle="Product, technology, and market strategy built in one integrated operating model."
      />

      <section className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {team.map((member, index) => (
          <MotionReveal key={member.name} delay={index * 0.07}>
            <article className="rounded-3xl border border-solarBlue-100 bg-white p-6 text-center shadow-card">
              <div className="mx-auto inline-flex size-16 items-center justify-center rounded-full border border-solarBlue-200 bg-solarBlue-50 text-xl font-semibold text-solarBlue-700">
                {member.name
                  .split(" ")
                  .slice(0, 2)
                  .map((item) => item[0])
                  .join("")}
              </div>
              <h3 className="mt-4 text-lg font-semibold text-solarBlue-900">{member.name}</h3>
              <p className="mt-1 text-sm text-solarBlue-900/65">{member.role}</p>
            </article>
          </MotionReveal>
        ))}
      </section>

      <section className="mt-10 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
        <h3 className="text-xl font-semibold text-solarBlue-900">Execution roadmap</h3>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl bg-solarBlue-50 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-700/70">Phase 1</p>
            <p className="mt-2 text-sm text-solarBlue-900/70">Launch in first CDG territory with initial subscriber validation.</p>
          </article>
          <article className="rounded-2xl bg-energyGreen-100/70 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-700/70">Phase 2</p>
            <p className="mt-2 text-sm text-solarBlue-900/70">Expand utility adapters and standardize cross-state operations.</p>
          </article>
          <article className="rounded-2xl bg-sunOrange-100 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-solarBlue-700/70">Phase 3</p>
            <p className="mt-2 text-sm text-solarBlue-900/70">Scale nationally as clean-energy allocation infrastructure.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
