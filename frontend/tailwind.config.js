/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F5F6F8',
        panel: '#FFFFFF',
        canvasDark: '#EEF1F4',
        panelLight: '#F8FAFB',
        ink: {
          DEFAULT: '#1F2933',
          muted: '#667085',
          faint: '#98A2B3',
        },
        line: '#D9DEE5',
        lineStrong: '#B8C0CC',
        accent: {
          DEFAULT: '#256B5B',
          hover: '#1F5A4D',
          soft: '#E5F0EC',
        },
        success: '#2F855A',
        danger: '#D92D20',
        warning: '#F59E0B',
        sidebar: {
          DEFAULT: '#25313D',
          hover: '#303D49',
          active: '#3B4A56',
          text: '#E4E7EC',
          muted: '#AAB2BD',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'SF Pro Display', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['SF Mono', 'JetBrains Mono', 'Menlo', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
      },
      boxShadow: {
        float: '0 8px 24px rgba(31,41,51,0.10)',
        pop: '0 16px 40px rgba(31,41,51,0.14)',
        card: '0 1px 2px rgba(31,41,51,0.06)',
      },
    },
  },
  plugins: [],
}
