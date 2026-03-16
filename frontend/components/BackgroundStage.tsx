// Animated background stage with layered 3D-like gradient orbs and subtle parallax motion.
"use client";

import { motion } from "framer-motion";

export function BackgroundStage() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <motion.div
        className="stage-orb stage-orb-a"
        animate={{ x: [0, 20, -12, 0], y: [0, -22, 8, 0], scale: [1, 1.07, 0.96, 1] }}
        transition={{ repeat: Infinity, duration: 14, ease: "easeInOut" }}
      />
      <motion.div
        className="stage-orb stage-orb-b"
        animate={{ x: [0, -22, 10, 0], y: [0, 18, -14, 0], scale: [1, 0.95, 1.06, 1] }}
        transition={{ repeat: Infinity, duration: 16, ease: "easeInOut" }}
      />
      <motion.div
        className="stage-orb stage-orb-c"
        animate={{ x: [0, 14, -10, 0], y: [0, 10, -20, 0], scale: [1, 1.08, 0.92, 1] }}
        transition={{ repeat: Infinity, duration: 12, ease: "easeInOut" }}
      />
      <div className="stage-grid" />
    </div>
  );
}
