/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f14",
        panel: "#121823",
        border: "#1f2937",
        accent: "#22d3ee",
        danger: "#ef4444",
        warn: "#f59e0b",
        ok: "#22c55e",
      },
    },
  },
  plugins: [],
}
