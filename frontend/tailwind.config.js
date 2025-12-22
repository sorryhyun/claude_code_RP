/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    screens: {
      // Three-tier responsive system:
      // Mobile: 0-479px (default styles, no prefix)
      // Tablet: 480-1023px (sm: prefix)
      // Desktop: 1024px+ (lg: prefix)
      'sm': '480px',
      'lg': '1024px',
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
