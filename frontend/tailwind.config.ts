import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        raven: {
          950: '#05070D',
          900: '#0D0F14',
          800: '#111827',
          700: '#1F2937',
          600: '#374151',
          400: '#9CA3AF',
          200: '#E5E7EB',
        },
        electric: {
          500: '#3B82F6',
          400: '#60A5FA',
          900: '#1E3A5F',
        },
        severity: {
          critical: '#EF4444',
          high:     '#F97316',
          medium:   '#EAB308',
          low:      '#3B82F6',
          info:     '#6B7280',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"Courier New"', 'Courier', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
