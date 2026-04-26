/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Bebas Neue"', "sans-serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          950: "#070712",
          900: "#0c0c1a",
          800: "#13132a",
          700: "#1c1c3a",
        },
        gold: {
          400: "#f5d061",
          500: "#e6b942",
          600: "#bf9420",
        },
      },
      boxShadow: {
        glow: "0 0 40px rgba(245, 208, 97, 0.15)",
        glowStrong: "0 0 60px rgba(245, 208, 97, 0.35)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-1000px 0" },
          "100%": { backgroundPosition: "1000px 0" },
        },
      },
      animation: {
        shimmer: "shimmer 2s infinite linear",
      },
    },
  },
  plugins: [],
};
