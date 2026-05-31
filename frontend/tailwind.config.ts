import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // "Watchtower" SIEM identity — tactical HUD display, technical body, data mono
        display: ['Chakra Petch', 'sans-serif'],
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        // PlayParser sandbox fonts (font-play / font-play-mono utilities)
        play: ['Chakra Petch', 'sans-serif'],
        'play-mono': ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Neutral gunmetal / charcoal canvas (the SIEM dark console base)
        void: '#0B0B0D',
        deep: '#101015',
        surface: '#15151B',
        elevated: '#1C1C24',
        panel: '#25252F',

        // Primary accent — AMBER / GOLD (the raven's watchful eye, monitoring-terminal amber).
        // Keeps the `indigo` key name so existing utility classes remap automatically.
        indigo: {
          300: '#F3DCBC',
          400: '#EECFA3',
          500: '#E3B57E',
          600: '#C9974F',
          700: '#B5620C',
          800: '#854809',
          900: '#583009',
          950: '#2E1905',
        },

        // Built-in amber palette overridden with the SOFT sand-amber scale
        // (PlayParser and any literal amber-* utilities inherit the calm tone).
        amber: {
          50: '#FBF7F0',
          100: '#F6EBD8',
          200: '#EFDCBC',
          300: '#EECFA3',
          400: '#E3B57E',
          500: '#D4A05E',
          600: '#BC8A48',
          700: '#977038',
          800: '#6E5228',
          900: '#4A3720',
          950: '#2A1F13',
        },

        // Secondary — STEEL / SLATE for info, AI, system data (neutral, not a vibrant blue).
        // Keeps the `violet` key name so existing utility classes remap automatically.
        violet: {
          300: '#C3CDDC',
          400: '#9CACC4',
          500: '#7E90AD',
          600: '#63748F',
        },

        sovereign: {
          glow: 'rgba(227,181,126,0.38)',
          border: 'rgba(227,181,126,0.24)',
          surface: 'rgba(227,181,126,0.08)',
        },

        // Semantic severity — industry-standard SIEM scale (Elastic Borealis-aligned)
        threat: {
          critical: '#F0444E',
          high: '#F2853C',
          medium: '#E8B84B',
          low: '#3FB6A0',
          info: '#8A9CB8',
        },

        // Severity aliases for backward compat with existing pages
        severity: {
          critical: '#F0444E',
          high: '#F2853C',
          medium: '#E8B84B',
          low: '#3FB6A0',
          info: '#8A9CB8',
        },

        text: {
          primary: '#F6F4F0',
          secondary: '#AEB4BF',
          muted: '#767C88',
          ghost: '#4A4E58',
        },

        border: {
          subtle: 'rgba(255,255,255,0.06)',
          DEFAULT: 'rgba(255,255,255,0.12)',
          bright: 'rgba(255,255,255,0.22)',
        },

        // PlayParser surfaces — retuned to the Watchtower amber/charcoal system
        play: {
          base: '#0B0B0D',
          elevate: '#101015',
          panel: '#15151B',
          surface: '#1C1C24',
          'surface-2': '#25252F',
          border: '#2D2D38',
          'border-strong': '#3C3C49',
          fg: '#F4F2EE',
          muted: '#9DA3AE',
          subtle: '#5C616E',
          accent: '#E3B57E',
          'accent-muted': '#A9631E',
          'accent-hover': '#EECFA3',
          'accent-glow': 'rgba(227, 181, 126, 0.22)',
          warm: '#E8B84B',
          'warm-bright': '#F3DCBC',
        },
      },
      backgroundImage: {
        'sovereign-gradient': 'linear-gradient(135deg, #C9974F 0%, #E3B57E 50%, #F3DCBC 100%)',
        'sovereign-radial': 'radial-gradient(ellipse at center, rgba(227,181,126,0.14) 0%, transparent 70%)',
        'threat-gradient': 'linear-gradient(135deg, #F0444E 0%, #F2853C 100%)',
        'hero-mesh': `
          radial-gradient(ellipse 80% 50% at 50% -10%, rgba(227,181,126,0.18) 0%, transparent 60%),
          radial-gradient(ellipse 40% 30% at 82% 18%, rgba(240,68,78,0.07) 0%, transparent 50%),
          radial-gradient(ellipse 44% 32% at 18% 82%, rgba(138,156,184,0.05) 0%, transparent 50%)
        `,
        'grid-faint': `
          linear-gradient(to right, rgba(255,255,255,0.035) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255,255,255,0.035) 1px, transparent 1px)
        `,
      },
      backgroundSize: {
        'grid-cell': '40px 40px',
      },
      boxShadow: {
        'sovereign': '0 0 0 1px rgba(227,181,126,0.22), 0 4px 24px rgba(227,181,126,0.12)',
        'sovereign-lg': '0 0 0 1px rgba(227,181,126,0.28), 0 8px 48px rgba(227,181,126,0.2)',
        'glow-indigo': '0 0 16px rgba(227,181,126,0.18)',
        'glow-rose': '0 0 20px rgba(240,68,78,0.4)',
        'glow-teal': '0 0 20px rgba(63,182,160,0.4)',
        'card': '0 1px 0 rgba(255,255,255,0.05), 0 4px 16px rgba(0,0,0,0.45)',
        'card-hover': '0 1px 0 rgba(255,255,255,0.08), 0 8px 32px rgba(0,0,0,0.55), 0 0 0 1px rgba(227,181,126,0.22)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'scan': 'scan 7s linear infinite',
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
