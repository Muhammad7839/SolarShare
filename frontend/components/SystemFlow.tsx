// Animated ecosystem diagram for explaining the SolarShare value chain in one glance.
"use client";

import { motion } from "framer-motion";
import { ArrowRight, Factory, House, Network, Power } from "lucide-react";

const flow = [
  { title: "Solar Farm", subtitle: "Generates clean electricity", icon: Factory },
  { title: "Utility Grid", subtitle: "Calculates bill credits", icon: Power },
  { title: "SolarShare", subtitle: "Allocates and optimizes", icon: Network },
  { title: "Household", subtitle: "Receives monthly savings", icon: House }
];

export function SystemFlow() {
  return (
    <div className="rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card dark:border-slate-700 dark:bg-slate-900/70">
      <div className="grid gap-5 md:grid-cols-[repeat(4,minmax(0,1fr))] md:items-center">
        {flow.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.title} className="flex items-center gap-3 md:block md:text-center">
              <motion.div
                initial={{ scale: 0.96, opacity: 0.7 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.08 }}
                className="mx-auto inline-flex size-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-solarBlue-700 to-solarBlue-500 text-white shadow-glow"
              >
                <Icon className="size-6" />
              </motion.div>
              <div>
                <h3 className="mt-3 text-base font-semibold text-solarBlue-900 dark:text-slate-100">{step.title}</h3>
                <p className="text-sm text-solarBlue-900/60 dark:text-slate-300">{step.subtitle}</p>
              </div>
              {index < flow.length - 1 ? (
                <ArrowRight className="hidden size-5 text-solarBlue-500 md:mx-auto md:mt-3 md:block" />
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
