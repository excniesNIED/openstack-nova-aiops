# OpenStack AIOps 看板（对接 `pipeline/service` 后端）

一个科幻风格的监控看板前端应用（AIOps Demo），使用 Vue 3 + TypeScript 构建，采用 [Vue DevUI](https://github.com/DevCloudFE/vue-devui) 作为 UI 组件库，[vue-data-ui](https://github.com/graphieros/vue-data-ui) 作为数据可视化组件库。

## ✨ 特性

- 🎨 **科幻主题设计** - 赛博朋克风格的深色主题，霓虹色彩搭配
- 🌟 **动态视觉效果** - 流光边框、脉冲动画、扫描线效果
- 📊 **丰富的数据可视化** - 折线图、雷达图、环形图、仪表盘等
- 🔄 **实时数据更新** - 轮询 FastAPI `/alerts`，动态刷新图表与告警列表
- 📱 **响应式布局** - 适配不同屏幕尺寸
- ⚡ **Bun 包管理** - 使用 Bun 作为包管理器，更快的安装和构建速度

## 🛠️ 技术栈

- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite 7
- **UI 组件库**: Vue DevUI
- **图表组件**: vue-data-ui
- **包管理器**: Bun
- **代码检查**: ESLint + Oxlint

## 📦 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── DashboardHeader.vue    # 顶部导航栏
│   │   ├── StatsCard.vue          # 统计卡片组件
│   │   ├── LineChart.vue          # 折线图组件
│   │   ├── RadarChart.vue         # 雷达图组件
│   │   ├── DonutChart.vue         # 环形图组件
│   │   ├── GaugePanel.vue         # 仪表盘面板
│   │   ├── ActivityLog.vue        # 活动日志组件
│   │   └── SystemStatus.vue       # 系统状态组件
│   ├── assets/
│   │   └── main.css               # 全局样式（科幻主题）
│   ├── App.vue                    # 主应用组件
│   └── main.ts                    # 应用入口
├── eslint.config.js               # ESLint 配置
├── package.json                   # 项目配置
└── vite.config.ts                 # Vite 配置
```

## 🚀 快速开始

### 环境要求

- Node.js >= 20.19.0 或 >= 22.12.0
- [Bun](https://bun.sh/) >= 1.0

### 安装依赖

```bash
bun install
```

### 开发模式

```bash
bun run dev
```

访问 http://localhost:5173 查看应用。

## 🔌 与后端联调（按 `pipeline/` 全链路）

后端来自 `pipeline/service`（FastAPI），默认端口 `8000`，提供：

- `GET /health`
- `GET /alerts?limit=200`
- `GET /alerts/{alert_id}`

前端默认通过 Vite 代理访问后端：

- 浏览器请求 `GET /api/alerts`
- Vite 代理转发到 `http://localhost:8000/alerts`

如果你的后端不是 `localhost:8000`，可用两种方式指定：

1) 启动 dev server 时设置环境变量（影响 Vite 代理）：

```bash
VITE_API_PROXY_TARGET=http://localhost:8000 bun run dev
```

2) 运行后，在页面右上角「设置」里修改 `API Base URL`：

- 推荐：`/api`（走代理）
- 或直接写：`http://<host>:8000`（直连，后端已开启 CORS）

### 生产构建

```bash
bun run build
```

构建产物将输出到 `dist/` 目录。

### 预览构建结果

```bash
bun run preview
```

## 🔍 代码检查

### 运行 Lint

```bash
bun run lint
```

使用 Oxlint 和 ESLint 进行代码检查。

### 自动修复

```bash
bun run lint:fix
```

### 类型检查

```bash
bun run type-check
```

## 📊 组件说明

### DashboardHeader
顶部导航栏，包含 Logo、系统状态指示器和实时时钟。

### StatsCard
统计卡片，展示关键指标数据，支持多种颜色主题和动态变化指示。

### LineChart
基于 vue-data-ui 的折线图，展示近 15 分钟告警趋势（P1/P2/P3）。

### RadarChart
雷达图组件，用于展示多维度性能指标对比。

### DonutChart
环形图组件，展示告警等级分布。

### GaugePanel
仪表盘面板，展示由告警派生的健康度/压力/置信度（0-100）。

### ActivityLog
活动流组件，展示最新告警摘要（时间、等级、类型、实体、置信度）。

### SystemStatus
系统状态面板，展示后端 API 连通性与延迟（其余链路组件目前标记为“未检测”）。

## 🎨 主题定制

主题变量定义在 `src/assets/main.css` 中：

```css
:root {
  --primary-color: #00f0ff;      /* 主色调 - 青色 */
  --secondary-color: #ff00ff;    /* 次要色 - 品红 */
  --accent-color: #00ff88;       /* 强调色 - 绿色 */
  --bg-dark: #0a0a1a;            /* 深色背景 */
  --bg-card: rgba(10, 20, 40, 0.85);  /* 卡片背景 */
  --border-glow: rgba(0, 240, 255, 0.3);  /* 发光边框 */
  --text-primary: #e0e0ff;       /* 主要文字 */
  --text-secondary: #8888aa;     /* 次要文字 */
}
```

## 📝 开发指南

### 添加新图表

1. 在 `src/components/` 下创建新的 Vue 组件
2. 导入 vue-data-ui 的图表组件
3. 配置图表样式以匹配科幻主题
4. 在 `App.vue` 中引入并使用

### 样式规范

- 使用 CSS 变量保持主题一致性
- 添加适当的动画效果增强视觉体验
- 确保响应式布局在不同设备上正常显示

## 📄 许可证

MIT License
