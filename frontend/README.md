# 虚拟币趋势预测前端 (Crypto Prediction Frontend)

本目录为项目的 React 18 前端部分。它使用 Vite 构建，采用 ECharts 渲染 K线图和技术指标。

## 技术栈
- **框架**: React 18 + Vite
- **路由**: React Router DOM (用于主看板 `/` 与管理后台 `/admin` 的切换)
- **图表**: ECharts (K线渲染、均线、自定义 Tooltip)
- **样式**: 原生 CSS + Flex/Grid 布局 (支持响应式卡片与两列时间轴)
- **请求**: Axios (与 FastAPI 后端交互)

## 开发指南

1. **安装依赖**
   ```bash
   npm install
   ```

2. **本地开发**
   ```bash
   npm run dev
   ```
   默认运行在 `http://localhost:5173`。开发环境下的 `vite.config.js` 已配置代理，会将 `/api` 的请求转发至后端的 `http://localhost:8000`。

3. **生产构建**
   ```bash
   npm run build
   ```
   构建产物会生成在 `dist/` 目录下。
   *注意*: 在本项目的架构中，FastAPI 后端 (`backend/main.py`) 会直接挂载前端的 `dist` 目录。所以在生产环境下，只需要运行一次后端服务（`uvicorn main:app --port 8000`）即可统一访问前后端。

## 目录说明
- `src/App.jsx`: 主看板核心代码。包含 ECharts 渲染逻辑、时间粒度选择、指标数据展示、新闻与巨鲸动态的 Timeline 组件。
- `src/App.css`: 主看板的样式定义（K线控制栏、双列信息流、文本折叠）。
- `src/Admin.jsx`: 管理后台核心代码。提供币种、指标、新闻源、智能提示词模板的增删改查 UI。
- `src/Admin.css`: 管理后台的样式定义。
- `src/main.jsx`: React 渲染入口和 Router 路由挂载。
- `vite.config.js`: Vite 配置文件（内含 Proxy 代理设置）。