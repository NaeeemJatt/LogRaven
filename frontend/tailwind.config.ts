import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        sans: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        void: '#030508',
        deep: '#080C14',
        surface: '#0F1422',
        elevated: '#161C2E',
        panel: '#1D2540',

        indigo: {
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
          950: '#1E1B4B',
        },

        sovereign: {
          glow: 'rgba(99,102,241,0.35)',
          border: 'rgba(99,102,241,0.18)',
          surface: 'rgba(99,102,241,0.07)',
        },

        threat: {
          critical: '#F43F5E',
          high: '#F97316',
          medium: '#FBBF24',
          low: '#14B8A6',
          info: '#818CF8',
        },

        // Keep severity aliases for backward compat with existing pages
        severity: {
          critical: '#F43F5E',
          high: '#F97316',
          medium: '#FBBF24',
          low: '#14B8A6',
          info: '#818CF8',
        },

        text: {
          primary: '#F1F5F9',
          secondary: '#94A3B8',
          muted: '#475569',
          ghost: '#1E293B',
        },

        border: {
          subtle: 'rgba(255,255,255,0.05)',
          DEFAULT: 'rgba(255,255,255,0.09)',
          bright: 'rgba(255,255,255,0.16)',
        },

        // PlayParser surfaces (keep for PlayParser page backward compat)
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
      backgroundImage: {
        'sovereign-gradient': 'linear-gradient(135deg, #6366F1 0%, #818CF8 50%, #A5B4FC 100%)',
        'sovereign-radial': 'radial-gradient(ellipse at center, rgba(99,102,241,0.15) 0%, transparent 70%)',
        'threat-gradient': 'linear-gradient(135deg, #F43F5E 0%, #F97316 100%)',
        'hero-mesh': `
          radial-gradient(ellipse 80% 50% at 50% -10%, rgba(99,102,241,0.25) 0%, transparent 60%),
          radial-gradient(ellipse 40% 30% at 80% 20%, rgba(244,63,94,0.08) 0%, transparent 50%),
          radial-gradient(ellipse 40% 30% at 20% 80%, rgba(20,184,166,0.06) 0%, transparent 50%)
        `,
      },
      boxShadow: {
        'sovereign': '0 0 0 1px rgba(99,102,241,0.2), 0 4px 24px rgba(99,102,241,0.12)',
        'sovereign-lg': '0 0 0 1px rgba(99,102,241,0.25), 0 8px 48px rgba(99,102,241,0.2)',
        'glow-indigo': '0 0 20px rgba(99,102,241,0.4), 0 0 60px rgba(99,102,241,0.15)',
        'glow-rose': '0 0 20px rgba(244,63,94,0.4)',
        'glow-teal': '0 0 20px rgba(20,184,166,0.4)',
        'card': '0 1px 0 rgba(255,255,255,0.05), 0 4px 16px rgba(0,0,0,0.4)',
        'card-hover': '0 1px 0 rgba(255,255,255,0.08), 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.2)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'scan': 'scan 3s linear infinite',
        'shimmer': 'shimmer 2.5s infinite',
        'fade-in': 'fadeIn 0.6s ease forwards',
        'slide-up': 'slideUp 0.5s ease forwards',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
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
