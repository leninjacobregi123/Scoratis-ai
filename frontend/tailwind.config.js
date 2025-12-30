/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Athenian Agora Theme - Warm & Elegant
        'bg-primary': '#f5f0e6',
        'bg-secondary': '#faf6ed',
        'bg-tertiary': '#ebe5d8',
        'bg-card': '#ffffff',
        'bg-dark': '#e5e0d4',
        'border-color': '#d4cfb8',

        // Gold accents (warm olive-gold)
        'accent-gold': '#b8860b',
        'accent-gold-light': '#daa520',
        'accent-gold-dark': '#8b6914',

        // Olive green accents for Athenian elegance
        'accent-olive': '#6b7c5e',
        'accent-olive-light': '#8a9a7a',
        'accent-olive-dark': '#4a5a40',

        // Warm accents
        'accent-white': '#4a5a40',
        'accent-light': '#6b7c5e',
        'accent-gray': '#8a8a7a',

        // Legacy support (map to new theme)
        'accent-cyan': '#6b7c5e',
        'accent-orange': '#b8860b',
        'accent-purple': '#6b7c5e',
        'accent-blue': '#8a8a7a',
        'accent-pink': '#8a9a7a',

        'text-primary': '#3d4a35',
        'text-secondary': '#5a6b52',
        'text-muted': '#8a8a7a',
      },
      fontFamily: {
        'sans': ['Georgia', 'Times New Roman', 'serif'],
        'serif': ['Georgia', 'Times New Roman', 'serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'grid-move': 'gridMove 20s linear infinite',
        'marquee': 'marquee 30s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-out forwards',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(107, 124, 94, 0.15), 0 0 40px rgba(107, 124, 94, 0.1)' },
          '50%': { boxShadow: '0 0 40px rgba(107, 124, 94, 0.25), 0 0 80px rgba(107, 124, 94, 0.2)' },
        },
        gridMove: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '50px 50px' },
        },
        marquee: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        fadeIn: {
          'from': { opacity: '0', transform: 'translateY(20px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
