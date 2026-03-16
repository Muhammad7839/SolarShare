// Contact page with clean information architecture and backend-connected inquiry form.
import { ContactForm } from "@/components/ContactForm";
import { MotionReveal } from "@/components/MotionReveal";
import { SectionTitle } from "@/components/SectionTitle";

export default function ContactPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-16">
      <SectionTitle
        eyebrow="Contact"
        title="Connect with SolarShare"
        subtitle="Questions, partnerships, and support in one clean channel."
      />

      <section className="mt-10 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <MotionReveal>
          <article className="rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
            <h3 className="text-xl font-semibold text-solarBlue-900">Contact channels</h3>
            <div className="mt-4 space-y-3 text-sm text-solarBlue-900/70">
              <p>
                Email: <a className="font-semibold text-solarBlue-700" href="mailto:hello@solarshare.dev">hello@solarshare.dev</a>
              </p>
              <p>
                Partnerships: <a className="font-semibold text-solarBlue-700" href="mailto:invest@solarshare.dev">invest@solarshare.dev</a>
              </p>
              <p>Hours: Monday-Friday, 9:00 AM-6:00 PM ET</p>
              <p>Response target: within one business day.</p>
            </div>
          </article>
        </MotionReveal>

        <MotionReveal delay={0.08}>
          <ContactForm />
        </MotionReveal>
      </section>
    </main>
  );
}
