// Tailwind theme definitions aligned with SolarShare logo and climate-tech brand language.
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        solarBlue: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#2a66c8",
          700: "#1f4b95",
          900: "#11294a"
        },
        energyGreen: {
          100: "#e6f6de",
          500: "#76be43",
          700: "#4d8b28"
        },
        sunOrange: {
          100: "#fff3e1",
          500: "#f0a52b",
          700: "#c77b09"
        },
        aquaMist: "#e7f5f2"
      },
      boxShadow: {
        card: "0 12px 40px rgba(17, 41, 74, 0.12)",
        glow: "0 0 0 1px rgba(42, 102, 200, 0.16), 0 10px 32px rgba(17, 41, 74, 0.18)"
      },
      backgroundImage: {
        mesh:
          "radial-gradient(circle at 10% 10%, rgba(42, 102, 200, 0.16), transparent 40%), radial-gradient(circle at 80% 0%, rgba(118, 190, 67, 0.15), transparent 42%), radial-gradient(circle at 90% 70%, rgba(240, 165, 43, 0.12), transparent 35%)"
      }
    }
  },
  plugins: []
};

export default config;
