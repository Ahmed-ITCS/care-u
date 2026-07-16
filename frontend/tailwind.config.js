/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../templates/**/*.html',
    '../apps/**/templates/**/*.html',
    '../static/src/**/*.css',
  ],
  safelist: [
    'filter-input',
    'filter-select',
    'filter-input-search',
    'filter-checkbox',
    'filter-bar-primary',
    'filter-field',
    'filter-field-wide',
    'filter-field-checkbox',
    'filter-label',
    'filter-control',
    'filter-actions',
    'filter-advanced',
    'filter-advanced-grid',
    'filter-group-label',
    'filter-search-icon',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'premium': '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.05), 0 12px 32px rgba(0,0,0,0.04)',
        'premium-lg': '0 4px 6px rgba(0,0,0,0.04), 0 12px 32px rgba(0,0,0,0.08), 0 24px 64px rgba(0,0,0,0.06)',
        'premium-xl': '0 8px 12px rgba(0,0,0,0.05), 0 24px 64px rgba(0,0,0,0.12), 0 48px 96px rgba(0,0,0,0.08)',
        'glow': '0 0 40px -10px rgba(13,148,136,0.5)',
        'glow-sm': '0 0 20px -5px rgba(13,148,136,0.35)',
        'inner-soft': 'inset 0 1px 0 rgba(255,255,255,0.08)',
        'inner-highlight': 'inset 0 1px 0 rgba(255,255,255,0.12)',
        'btn-primary': '0 4px 14px rgba(14,90,167,0.35), 0 1px 3px rgba(14,90,167,0.2)',
        'btn-primary-hover': '0 6px 20px rgba(14,90,167,0.45), 0 2px 6px rgba(14,90,167,0.25)',
        'card-hover': '0 4px 6px rgba(0,0,0,0.04), 0 16px 48px rgba(0,0,0,0.1)',
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #0E5AA7 0%, #0D9488 100%)',
        'gradient-primary-hover': 'linear-gradient(135deg, #0A4A85 0%, #0B7C72 100%)',
        'gradient-sidebar': 'linear-gradient(180deg, #04101C 0%, #071A2E 40%, #0A2E3F 100%)',
        'gradient-hero': 'linear-gradient(135deg, #03101E 0%, #0A3A66 50%, #0C5A6E 100%)',
        'mesh': 'radial-gradient(at 40% 20%, rgba(14,90,167,0.18) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(13,148,136,0.14) 0px, transparent 50%), radial-gradient(at 0% 50%, rgba(14,116,144,0.1) 0px, transparent 50%)',
        'mesh-dark': 'radial-gradient(at 40% 20%, rgba(14,90,167,0.3) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(13,148,136,0.2) 0px, transparent 50%)',
        'mesh-subtle': 'radial-gradient(at 70% 30%, rgba(14,90,167,0.06) 0px, transparent 60%), radial-gradient(at 20% 80%, rgba(13,148,136,0.04) 0px, transparent 60%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.35s ease-out',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in': 'slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'float': 'float 6s ease-in-out infinite',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'shimmer': 'shimmer 2.5s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(-8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      colors: {
        gph: {
          50: '#EAF5FB',
          primary: '#0E5AA7',
          dark: '#04101C',
          accent: '#0D9488',
        },
      },
      letterSpacing: {
        'tighter-xl': '-0.04em',
        'tighter-lg': '-0.03em',
        'tighter': '-0.02em',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        gph: {
          /* --- Core palette (deep blue + teal) --- */
          primary: '#0E5AA7',
          'primary-content': '#FFFFFF',
          secondary: '#0E7490',
          'secondary-content': '#FFFFFF',
          accent: '#0D9488',
          'accent-content': '#FFFFFF',

          /* --- Neutral (sidebar) --- */
          neutral: '#071A2E',
          'neutral-content': '#DCE9F5',

          /* --- Base surfaces --- */
          'base-100': '#FFFFFF',
          'base-200': '#F2F7FB',
          'base-300': '#E2ECF3',
          'base-content': '#0A1B2B',

          /* --- Semantic --- */
          info: '#0EA5E9',
          'info-content': '#FFFFFF',
          success: '#0D9488',
          'success-content': '#FFFFFF',
          warning: '#D97706',
          'warning-content': '#FFFFFF',
          error: '#E11D48',
          'error-content': '#FFFFFF',
        },
        'gph-dark': {
          /* --- Core palette (deep blue + teal) --- */
          primary: '#49A6E0',
          'primary-content': '#04101C',
          secondary: '#22D3EE',
          'secondary-content': '#04101C',
          accent: '#2DD4BF',
          'accent-content': '#04101C',

          /* --- Neutral (sidebar) --- */
          neutral: '#05111F',
          'neutral-content': '#DCE9F5',

          /* --- Base surfaces --- */
          'base-100': '#0A1622',
          'base-200': '#0F1E2E',
          'base-300': '#1A2E42',
          'base-content': '#E6F0F7',

          /* --- Semantic --- */
          info: '#38BDF8',
          'info-content': '#04101C',
          success: '#2DD4BF',
          'success-content': '#04101C',
          warning: '#FCD34D',
          'warning-content': '#04101C',
          error: '#FB7185',
          'error-content': '#04101C',
        },
      },
    ],
  },
};
