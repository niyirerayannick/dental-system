module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./**/*.py"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfeff",
          100: "#cffafe",
          700: "#0f766e",
          800: "#115e59"
        }
      }
    }
  },
  plugins: [
    require("@tailwindcss/forms")
  ]
};
