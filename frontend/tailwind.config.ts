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
        // PlayParser “Obsidian lab” — slightly lifted surfaces so UI isn’t “black + white outlines”
        play: {
          base: '#06080d',
          elevate: '#0c1018',
          panel: '#141a24',
          surface: '#1a2230',
          'surface-2': '#222b3d',
          border: '#2e3a4d',
          'border-strong': '#3d4d63',
          fg: '#eef1f6',
          muted: '#9ca8b8',
          subtle: '#6b7c90',
          accent: '#2dd4bf',
          'accent-muted': '#0d9488',
          'accent-hover': '#5eead4',
          'accent-glow': 'rgba(45, 212, 191, 0.22)',
          warm: '#e8b86a',
          'warm-bright': '#fbbf24',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"Courier New"', 'Courier', 'monospace'],
        play: ['"DM Sans"', 'system-ui', 'sans-serif'],
        'play-mono': ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
  // PlayParser: keep custom palette utilities in the bundle (covers opacity modifiers like bg-play-panel/95)
  safelist: [
    { pattern: /^bg-play-/ },
    { pattern: /^text-play-/ },
    { pattern: /^border-play-/ },
    { pattern: /^ring-play-/ },
    { pattern: /^from-play-/ },
    { pattern: /^to-play-/ },
    { pattern: /^via-play-/ },
  ],
} satisfies Config
