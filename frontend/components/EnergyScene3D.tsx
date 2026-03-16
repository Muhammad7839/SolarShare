// Animated 3D-styled ecosystem scene showing SolarShare between utilities and households.
"use client";

import { motion } from "framer-motion";
import { Factory, House, Network, Power } from "lucide-react";

const sceneNodes = [
  { label: "Solar Farm", icon: Factory, className: "scene-node node-farm", delay: 0.02 },
  { label: "Utility Grid", icon: Power, className: "scene-node node-grid", delay: 0.08 },
  { label: "SolarShare", icon: Network, className: "scene-node node-core", delay: 0.14 },
  { label: "Households", icon: House, className: "scene-node node-home", delay: 0.2 }
];

export function EnergyScene3D() {
  return (
    <div className="energy-scene">
      <div className="scene-link link-a" />
      <div className="scene-link link-b" />
      <div className="scene-link link-c" />
      {sceneNodes.map((node) => {
        const Icon = node.icon;
        return (
          <motion.article
            key={node.label}
            className={node.className}
            initial={{ opacity: 0, y: 14, scale: 0.96 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.45, delay: node.delay, ease: "easeOut" }}
          >
            <span className="scene-icon-wrap">
              <Icon className="size-4" />
            </span>
            <span>{node.label}</span>
          </motion.article>
        );
      })}
    </div>
  );
}
