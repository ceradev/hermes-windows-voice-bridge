/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      boxShadow: {
        glow: '0 0 0 1px rgba(59,130,246,.18), 0 20px 50px rgba(15,23,42,.45)',
      },
    },
  },
  plugins: [],
};
