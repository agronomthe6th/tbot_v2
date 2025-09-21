/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",  // ← ДОБАВИТЬ ЭТО!
  ],
  theme: {
    extend: {
      colors: {
        // Цвета для торгового терминала
        'trading': {
          'bg': '#1a1a1a',
          'card': '#2d2d2d', 
          'border': '#404040',
          'green': '#00d4aa',
          'red': '#ff4747',
          'yellow': '#ffb020'
        }
      }
    },
  },
  plugins: [],
}