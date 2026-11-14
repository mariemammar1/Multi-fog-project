/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fogA: { light: '#e0f2fe', DEFAULT: '#0284c7', dark: '#0369a1' },
        fogB: { light: '#dcfce7', DEFAULT: '#16a34a', dark: '#15803d' },
        fogC: { light: '#fef3c7', DEFAULT: '#d97706', dark: '#b45309' },
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
      boxShadow: {
        'glow-cyan':    '0 0 24px -4px rgba(6,182,212,0.25)',
        'glow-emerald': '0 0 24px -4px rgba(16,185,129,0.25)',
        'card':  '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04)',
        'card-hover': '0 2px 6px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.07)',
      },
      animation: {
        'fadeIn':  'fadeIn 0.28s ease both',
        'slideUp': 'slideUp 0.32s ease both',
        'ping-soft': 'ping-soft 1.8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0, transform: 'translateY(6px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        'ping-soft': { '0%,100%': { transform: 'scale(1)', opacity: 0.8 }, '50%': { transform: 'scale(1.4)', opacity: 0.3 } },
      },
    },
  },
  plugins: [],
}

