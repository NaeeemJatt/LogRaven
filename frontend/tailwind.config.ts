// LogRaven — Tailwind CSS Configuration
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // LogRaven brand colors
        raven: {
          50:  '#f0f4ff',
          100: '#e0e9ff',
          500: '#3B82F6',  // electric blue
          600: '#2563EB',
          700: '#1d4ed8',
          900: '#0D0F14',  // raven black
        },
        violet: {
          500: '#7C3AED',  // raven purple
          600: '#6d28d9',
        }
      }
    }
  },
  plugins: []
} satisfies Config
