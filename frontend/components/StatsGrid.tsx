// Visual statistic cards used for market opportunity and credibility proof sections.
import { BarChart3, Building2, Home, SunMedium } from "lucide-react";
import { MotionReveal } from "@/components/MotionReveal";

const stats = [
  {
    value: "130M+",
    label: "U.S. households",
    note: "Addressable customer base",
    icon: Home
  },
  {
    value: "44%",
    label: "Renter households",
    note: "Limited rooftop access",
    icon: Building2
  },
  {
    value: "2-5%",
    label: "Allocation margin",
    note: "Developer-paid model",
    icon: BarChart3
  },
  {
    value: "2026",
    label: "Platform-ready UX",
    note: "Live source-backed workflow",
    icon: SunMedium
  }
];

export function StatsGrid() {
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
      {stats.map((item, index) => {
        const Icon = item.icon;
        return (
          <MotionReveal key={item.label} delay={index * 0.07}>
            <article className="tilt-card rounded-2xl border border-solarBlue-100 bg-white p-5 shadow-card transition-transform duration-500 hover:-translate-y-1">
              <div className="mb-3 inline-flex rounded-xl bg-solarBlue-50 p-2 text-solarBlue-700">
                <Icon className="size-5" />
              </div>
              <p className="text-4xl font-semibold text-solarBlue-900">{item.value}</p>
              <p className="mt-1 text-base font-semibold text-solarBlue-900/85">{item.label}</p>
              <p className="mt-1 text-sm text-solarBlue-900/60">{item.note}</p>
            </article>
          </MotionReveal>
        );
      })}
    </div>
  );
}
