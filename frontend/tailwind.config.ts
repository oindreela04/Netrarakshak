import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0B1F3A", 900: "#071528", 800: "#0B1F3A", 700: "#14304F", 600: "#1E4066" },
        teal: { DEFAULT: "#3E8E8A", 50: "#EEF6F5", 100: "#D6EAE8", 500: "#3E8E8A", 600: "#2F7471", 700: "#245B58" },
        clinical: { DEFAULT: "#1F6FB2", 50: "#EDF4FB", 100: "#D3E5F5", 500: "#1F6FB2", 600: "#185A92" },
        ink: "#14202E",
        abyss: "#050B18",
        glow: "#8EC1FF",
        slate: { DEFAULT: "#5B6B7F" },
        mist: "#F3F6FA",
        line: "#D7DEE8",
        ok: "#2E7D5B",
        warn: "#B26B00",
        danger: "#B42318",
      },
      fontFamily: {
        sans: ["'Public Sans'", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["'Newsreader'", "Georgia", "serif"],
        hero: ["'Saira'", "'Public Sans'", "system-ui", "sans-serif"],
        tech: ["'Saira'", "'Public Sans'", "system-ui", "sans-serif"],
      },
      borderRadius: { lg: "10px", md: "7px", sm: "5px" },
      boxShadow: { panel: "0 1px 0 rgba(11,31,58,0.04), 0 1px 3px rgba(11,31,58,0.06)" },
    },
  },
  plugins: [],
} satisfies Config;
