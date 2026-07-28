/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 暗色主题风：深色背景 + 亮色文字 + 蓝色强调
        canvas: '#0F172A',         // 页面背景：深蓝黑（slate-900）
        panel: '#1E293B',          // 卡片/面板：深蓝灰（slate-800）
        canvasDark: '#334155',     // 更深一层，用于表头/悬停（slate-700）
        panelLight: '#273449',     // 稍亮的面板，用于输入框背景
        ink: {
          DEFAULT: '#F1F5F9',      // 主文字：亮白（slate-100）
          muted: '#94A3B8',        // 次要文字：浅蓝灰（slate-400）
          faint: '#64748B',        // 占位/弱化：灰蓝（slate-500）
        },
        line: '#334155',            // 分割线/边框（slate-700）
        lineStrong: '#475569',      // 更强的边框（slate-600）
        accent: {
          DEFAULT: '#3B82F6',      // 主色：亮蓝（blue-500）
          hover: '#2563EB',        // 悬停：更深蓝（blue-600）
          soft: '#1E3A5F',         // 浅蓝背景（暗色版）
        },
        success: '#10B981',         // 绿色（emerald-500）
        danger: '#EF4444',          // 红色（red-500）
        warning: '#F59E0B',
        // 侧边栏更深一层
        sidebar: {
          DEFAULT: '#0B1120',      // 侧边栏背景：更深的蓝黑
          hover: '#1E293B',        // 悬停
          active: '#1D4ED8',       // 选中：深蓝
          text: '#CBD5E1',         // 文字
          muted: '#64748B',        // 弱化文字
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
        float: '0 4px 12px rgba(0,0,0,0.3)',
        pop: '0 8px 24px rgba(0,0,0,0.4)',
        card: '0 2px 8px rgba(0,0,0,0.2)',
      },
    },
  },
  plugins: [],
}
