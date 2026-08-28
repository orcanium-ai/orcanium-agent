/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0F19',
        card: '#151D30',
        border: '#1F2C47',
        accent: '#3B82F6',
        textMuted: '#94A3B8'
      }
    },
  },
  plugins: [],
}
