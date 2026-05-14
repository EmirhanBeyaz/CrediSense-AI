import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0d0f",
        surface: "#111317",
        "surface-low": "#171a1f",
        "surface-high": "#24272d",
        primary: "#ffc107",
        "primary-soft": "#ffe4af",
        secondary: "#4edea3",
        danger: "#ff796f",
        muted: "#b9af9b",
        line: "rgba(255,255,255,0.1)",
      },
      fontFamily: {
        sans: ["Manrope", "Inter", "system-ui", "sans-serif"],
        display: ["Plus Jakarta Sans", "Manrope", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 48px rgba(255, 193, 7, 0.16)",
        emerald: "0 0 34px rgba(78, 222, 163, 0.14)",
      },
    },
  },
  plugins: [],
};

export default config;
