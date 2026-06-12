/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../templates/**/*.html',
    '../apps/**/templates/**/*.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'premium': '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 10px 30px -5px rgb(30 64 175 / 0.12)',
        'premium-lg': '0 10px 40px -10px rgb(0 0 0 / 0.12), 0 20px 50px -15px rgb(30 64 175 / 0.15)',
        'glow': '0 0 40px -10px rgb(59 130 246 / 0.35)',
        'inner-soft': 'inset 0 1px 0 0 rgb(255 255 255 / 0.08)',
      },
      backgroundImage: {
        'mesh': 'radial-gradient(at 40% 20%, rgb(59 130 246 / 0.18) 0px, transparent 50%), radial-gradient(at 80% 0%, rgb(16 185 129 / 0.12) 0px, transparent 50%), radial-gradient(at 0% 50%, rgb(30 64 175 / 0.1) 0px, transparent 50%)',
        'mesh-dark': 'radial-gradient(at 40% 20%, rgb(59 130 246 / 0.25) 0px, transparent 50%), radial-gradient(at 80% 0%, rgb(16 185 129 / 0.15) 0px, transparent 50%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },
      colors: {
        gph: {
          primary: '#1E40AF',
          dark: '#0F172A',
          accent: '#059669',
        },
      },
    },
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        gph: {
          primary: '#1E40AF',
          'primary-content': '#FFFFFF',
          secondary: '#0F766E',
          'secondary-content': '#FFFFFF',
          accent: '#059669',
          'accent-content': '#FFFFFF',
          neutral: '#0F172A',
          'neutral-content': '#F8FAFC',
          'base-100': '#FFFFFF',
          'base-200': '#F1F5F9',
          'base-300': '#E2E8F0',
          'base-content': '#0F172A',
          info: '#0EA5E9',
          success: '#059669',
          warning: '#D97706',
          error: '#DC2626',
        },
        'gph-dark': {
          primary: '#3B82F6',
          'primary-content': '#FFFFFF',
          secondary: '#14B8A6',
          'secondary-content': '#FFFFFF',
          accent: '#10B981',
          'accent-content': '#FFFFFF',
          neutral: '#1E293B',
          'neutral-content': '#F1F5F9',
          'base-100': '#0F172A',
          'base-200': '#1E293B',
          'base-300': '#334155',
          'base-content': '#F1F5F9',
          info: '#38BDF8',
          success: '#10B981',
          warning: '#FBBF24',
          error: '#F87171',
        },
      },
    ],
  },
};
