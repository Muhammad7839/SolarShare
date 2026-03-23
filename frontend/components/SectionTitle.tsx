// Reusable section heading component for consistent visual hierarchy and spacing.
import { ReactNode } from "react";

interface SectionTitleProps {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  centered?: boolean;
}

export function SectionTitle({ eyebrow, title, subtitle, centered = false }: SectionTitleProps) {
  return (
    <div className={centered ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      {eyebrow ? (
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-solarBlue-700/80 dark:text-slate-300">{eyebrow}</p>
      ) : null}
      <h2 className="mt-2 text-3xl font-semibold tracking-tight text-solarBlue-900 dark:text-slate-100 md:text-4xl">{title}</h2>
      {subtitle ? <p className="mt-3 text-base leading-relaxed text-solarBlue-900/70 dark:text-slate-200 md:text-lg">{subtitle}</p> : null}
    </div>
  );
}
