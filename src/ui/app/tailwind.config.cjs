/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Geist"',
          '"Segoe UI Variable"',
          '"Segoe UI"',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Helvetica Neue"',
          'sans-serif',
        ],
        mono: [
          '"Geist Mono"',
          'ui-monospace',
          '"Cascadia Mono"',
          '"JetBrains Mono"',
          'Consolas',
          '"SF Mono"',
          'monospace',
        ],
        display: [
          '"Geist"',
          '"Segoe UI Variable Display"',
          '"Segoe UI"',
          'Inter',
          'sans-serif',
        ],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(125, 211, 252, .22), 0 20px 50px rgba(0,0,0,.45)',
        'glow-ready':
          '0 0 0 1px rgba(74, 222, 128, .28), 0 12px 36px rgba(0,0,0,.45)',
        'glow-paused':
          '0 0 0 1px rgba(192, 132, 252, .28), 0 12px 36px rgba(0,0,0,.45)',
        'glow-error':
          '0 0 0 1px rgba(248, 113, 113, .28), 0 12px 36px rgba(0,0,0,.45)',
        'inset-hairline': 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      },
      colors: {
        ink: {
          0: '#06070a',
          1: '#0a0b10',
          2: '#0e1016',
          3: '#14161e',
        },
      },
      keyframes: {
        slideUpFade: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '.7', transform: 'scale(1.05)', filter: 'brightness(1.2)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'slide-up-fade': 'slideUpFade 360ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shimmer: 'shimmer 2s infinite',
      },
    },
  },
  plugins: [],
};
