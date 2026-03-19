/** @type {import('tailwindcss').Config} */
export default {
  // Tell Tailwind which files to scan for class names.
  // It only includes CSS for classes it actually finds here — keeps bundle small.
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        sand: {
          DEFAULT: '#c9a84c',
          light: '#e8c96d',
          dark: '#8b6914',
        },
        spice: '#d97706',
        surface: '#1c1a14',
        border: '#3a3020',
      },
    },
  },
  plugins: [],
}
