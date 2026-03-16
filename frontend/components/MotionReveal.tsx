// Small animation wrapper to provide consistent section entrance motion across pages.
"use client";

import { motion } from "framer-motion";
import { PropsWithChildren } from "react";

interface MotionRevealProps extends PropsWithChildren {
  delay?: number;
  className?: string;
}

export function MotionReveal({ children, delay = 0, className }: MotionRevealProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 18, scale: 0.98, filter: "blur(8px)" }}
      whileInView={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
      viewport={{ once: true, amount: 0.24 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
