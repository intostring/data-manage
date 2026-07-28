/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#FAFAFA',
        panel: '#FFFFFF',
        ink: {
          DEFAULT: '#0A0A0A',
          muted: '#6B7280',
          faint: '#9CA3AF',
        },
        line: '#E5E7EB',
        accent: {
          DEFAULT: '#C2410C',
          hover: '#9A3412',
          soft: '#FED7AA',
        },
        success: '#166534',
        danger: '#991B1B',
      },
      fontFamily: {
        sans: ['-apple-system', 'SF Pro Display', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['SF Mono', 'JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
      },
      boxShadow: {
        float: '0 4px 12px rgba(0,0,0,0.04)',
        pop: '0 8px 24px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}
