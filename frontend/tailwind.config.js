/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Athenian Agora Theme - Warm & Elegant (Default/Philosophy)
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

        // ============================================
        // SUBJECT-SPECIFIC COLOR PALETTES
        // ============================================

        // Physics - Cosmic Blue (Einstein)
        'physics': {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
          950: '#0F172A',
        },

        // Chemistry - Laboratory Emerald (Curie)
        'chemistry': {
          50: '#ECFDF5',
          100: '#D1FAE5',
          200: '#A7F3D0',
          300: '#6EE7B7',
          400: '#34D399',
          500: '#10B981',
          600: '#059669',
          700: '#047857',
          800: '#065F46',
          900: '#064E3B',
          950: '#022C22',
        },

        // Biology - Organic Pink (Darwin)
        'biology': {
          50: '#FDF2F8',
          100: '#FCE7F3',
          200: '#FBCFE8',
          300: '#F9A8D4',
          400: '#F472B6',
          500: '#EC4899',
          600: '#DB2777',
          700: '#BE185D',
          800: '#9D174D',
          900: '#831843',
          950: '#1A0F14',
        },

        // Mathematics - Geometric Violet (Pythagoras)
        'mathematics': {
          50: '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
          700: '#6D28D9',
          800: '#5B21B6',
          900: '#4C1D95',
          950: '#0C0A1D',
        },

        // Computer Science - Digital Cyan (Turing)
        'cs': {
          50: '#ECFEFF',
          100: '#CFFAFE',
          200: '#A5F3FC',
          300: '#67E8F9',
          400: '#22D3EE',
          500: '#06B6D4',
          600: '#0891B2',
          700: '#0E7490',
          800: '#155E75',
          900: '#164E63',
          950: '#042F2E',
        },

        // English - Theatrical Amber (Shakespeare)
        'english': {
          50: '#FFFBEB',
          100: '#FEF3C7',
          200: '#FDE68A',
          300: '#FCD34D',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
          700: '#B45309',
          800: '#92400E',
          900: '#78350F',
          950: '#1C1917',
        },

        // History - Ancient Stone (Herodotus)
        'history': {
          50: '#FAFAF9',
          100: '#F5F5F4',
          200: '#E7E5E4',
          300: '#D6D3D1',
          400: '#A8A29E',
          500: '#78716C',
          600: '#57534E',
          700: '#44403C',
          800: '#292524',
          900: '#1C1917',
          950: '#0C0A09',
        },

        // Philosophy - Athenian Indigo (Socrates)
        'philosophy': {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
          950: '#1E1B4B',
        },

        // Psychology - Victorian Rose (Freud)
        'psychology': {
          50: '#FDF2F8',
          100: '#FCE7F3',
          200: '#FBCFE8',
          300: '#F9A8D4',
          400: '#F472B6',
          500: '#EC4899',
          600: '#DB2777',
          700: '#BE185D',
          800: '#9D174D',
          900: '#831843',
          950: '#18181B',
        },

        // Economics - Georgian Green (Adam Smith)
        'economics': {
          50: '#F0FDF4',
          100: '#DCFCE7',
          200: '#BBF7D0',
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          700: '#15803D',
          800: '#166534',
          900: '#14532D',
          950: '#052E16',
        },
      },
      fontFamily: {
        'sans': ['Georgia', 'Times New Roman', 'serif'],
        'serif': ['Georgia', 'Times New Roman', 'serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        // Subject-specific gradient patterns
        'cosmic': 'radial-gradient(ellipse at top, #1E40AF 0%, #0F172A 50%, #000000 100%)',
        'laboratory': 'radial-gradient(ellipse at bottom, #065F46 0%, #022C22 60%, #011815 100%)',
        'organic': 'radial-gradient(ellipse at center, #2D1F26 0%, #1A0F14 50%, #0F0A0C 100%)',
        'geometric': 'radial-gradient(ellipse at top left, #4338CA 0%, #1E1B4B 40%, #0C0A1D 100%)',
        'digital': 'linear-gradient(180deg, #042F2E 0%, #0F172A 50%, #020617 100%)',
        'theatrical': 'radial-gradient(ellipse at bottom right, #44403C 0%, #292524 40%, #1C1917 100%)',
        'ancient': 'radial-gradient(ellipse at center, #44403C 0%, #292524 50%, #1C1917 100%)',
        'marble': 'radial-gradient(ellipse at top, #FFFFFF 0%, #FAF6ED 50%, #F5F0E6 100%)',
        'mind': 'radial-gradient(ellipse at center, #3F3F46 0%, #27272A 50%, #18181B 100%)',
        'financial': 'radial-gradient(ellipse at bottom, #166534 0%, #14532D 50%, #052E16 100%)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'floatSlow 8s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'grid-move': 'gridMove 20s linear infinite',
        'marquee': 'marquee 30s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        // Particle animations
        'star-twinkle': 'starTwinkle 3s ease-in-out infinite',
        'star-drift': 'starDrift 60s linear infinite',
        'bubble-rise': 'bubbleRise 8s ease-in-out infinite',
        'cell-float': 'cellFloat 10s ease-in-out infinite',
        'shape-rotate': 'shapeRotate 8s linear infinite',
        'binary-fall': 'binaryFall 8s linear infinite',
        'quill-float': 'quillFloat 6s ease-in-out infinite',
        'dust-drift': 'dustDrift 20s linear infinite',
        'ray-pulse': 'rayPulse 5s ease-in-out infinite',
        'neuron-pulse': 'neuronPulse 4s ease-in-out infinite',
        'coin-spin': 'coinSpin 4s linear infinite',
        'coin-float': 'coinFloat 3s ease-in-out infinite',
        'spin-slow': 'spinSlow 20s linear infinite',
        'spin-very-slow': 'spinVerySlow 60s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        floatSlow: {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '50%': { transform: 'translateY(-15px) rotate(3deg)' },
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
        // Particle-specific keyframes
        starTwinkle: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.3)' },
        },
        starDrift: {
          '0%': { transform: 'translateY(0) translateX(0)' },
          '100%': { transform: 'translateY(-100vh) translateX(20px)' },
        },
        bubbleRise: {
          '0%': { transform: 'translateY(100vh) scale(0.5)', opacity: '0' },
          '10%': { opacity: '0.7' },
          '90%': { opacity: '0.7' },
          '100%': { transform: 'translateY(-100px) scale(1.2)', opacity: '0' },
        },
        cellFloat: {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '25%': { transform: 'translateY(-20px) rotate(90deg)' },
          '50%': { transform: 'translateY(0) rotate(180deg)' },
          '75%': { transform: 'translateY(20px) rotate(270deg)' },
        },
        shapeRotate: {
          '0%': { transform: 'rotate(0deg) scale(1)' },
          '50%': { transform: 'rotate(180deg) scale(1.1)' },
          '100%': { transform: 'rotate(360deg) scale(1)' },
        },
        binaryFall: {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '5%': { opacity: '1' },
          '95%': { opacity: '1' },
          '100%': { transform: 'translateY(100vh)', opacity: '0' },
        },
        quillFloat: {
          '0%, 100%': { transform: 'translateY(0) rotate(-5deg)' },
          '50%': { transform: 'translateY(-30px) rotate(5deg)' },
        },
        dustDrift: {
          '0%': { transform: 'translateX(0) translateY(0)' },
          '100%': { transform: 'translateX(100px) translateY(50px)' },
        },
        rayPulse: {
          '0%, 100%': { opacity: '0.1', transform: 'scaleY(1)' },
          '50%': { opacity: '0.3', transform: 'scaleY(1.2)' },
        },
        neuronPulse: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '0.8', transform: 'scale(1.05)' },
        },
        coinSpin: {
          '0%': { transform: 'rotateY(0deg)' },
          '100%': { transform: 'rotateY(360deg)' },
        },
        coinFloat: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        spinSlow: {
          'from': { transform: 'rotate(0deg)' },
          'to': { transform: 'rotate(360deg)' },
        },
        spinVerySlow: {
          'from': { transform: 'rotate(0deg)' },
          'to': { transform: 'rotate(360deg)' },
        },
      },
      // Box shadow utilities for theme accents
      boxShadow: {
        'glow-blue': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.3)',
        'glow-pink': '0 0 20px rgba(236, 72, 153, 0.3)',
        'glow-violet': '0 0 20px rgba(139, 92, 246, 0.3)',
        'glow-cyan': '0 0 20px rgba(6, 182, 212, 0.3)',
        'glow-amber': '0 0 20px rgba(245, 158, 11, 0.3)',
        'glow-stone': '0 0 20px rgba(120, 113, 108, 0.3)',
        'glow-indigo': '0 0 20px rgba(99, 102, 241, 0.3)',
        'glow-rose': '0 0 20px rgba(244, 114, 182, 0.3)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.3)',
      },
    },
  },
  plugins: [],
}
