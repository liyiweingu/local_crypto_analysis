# 虚拟币趋势预测工具 (Crypto Trend Prediction Tool)

## 简介
这是一个全栈虚拟币趋势预测与看板工具。项目集成了币安 (Binance) K线数据、技术指标计算 (Pandas-TA)、新闻情绪分析、巨鲸链上动向追踪，并基于这些维度生成智能交易指南（评分、买卖建议、止损止盈）。同时附带一个管理后台用于动态调整指标、新闻源和提示词模板，并支持历史数据回测以验证模型胜率。
##页面展示
### 前端

<img width="415" height="423" alt="image" src="https://github.com/user-attachments/assets/5d02ac4a-5bfc-44ce-b5f6-b4be6e9dd8e5" />
<img width="766" height="646" alt="image" src="https://github.com/user-attachments/assets/5d68533f-b41a-47e6-b92a-081a234677ce" />

### 后台
<img width="366" height="462" alt="image" src="https://github.com/user-attachments/assets/aa267de0-43c0-4b58-9522-392ed4a1d4d3" />
<img width="314" height="473" alt="image" src="https://github.com/user-attachments/assets/69d8322c-347f-4987-b700-abbaf28ede9e" />


## 技术栈
*   **前端**：React 18 + Vite + React Router + ECharts (K线及技术指标可视化)
*   **后端**：FastAPI + Python 3.x + SQLite
*   **核心库**：`pandas`, `pandas-ta` (技术指标), `BeautifulSoup` (爬虫), `httpx`/`requests` (API请求)

## 目录结构
```text
fullstack-kline-project/
├── backend/            # FastAPI 后端服务
│   ├── main.py         # 核心 API 服务及路由 (处理前后端统一端口托管)
│   ├── klines.db       # SQLite 数据库
│   ├── init_db.py      # 数据库初始化脚本
│   ├── update_db.py    # 提示词更新脚本
│   ├── seed_data.py    # 种子数据拉取脚本
│   ├── services/       # 业务逻辑服务层 (计算指标、爬虫、情绪分析、指南生成)
│   └── tests/          # 测试与回测脚本 (backtest.py)
└── frontend/           # React 前端页面
    ├── src/
    │   ├── App.jsx     # 主看板页面 (图表、指标、新闻、指南)
    │   ├── Admin.jsx   # 后台管理页面
    │   └── main.jsx    # 入口及路由配置
    └── vite.config.js  # Vite 配置 (开发环境下代理到 8000 端口)
```

## 快速开始

### 1. 后端环境配置
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 初始化数据库结构和默认数据
python init_db.py
python update_db.py
```

### 2. 前端环境配置与构建
```bash
cd frontend
npm install

# 构建前端静态资源 (构建后将存入 dist 目录，供后端托管)
npm run build
```

### 3. 运行服务
项目配置了单端口整合（后端会自动挂载前端构建产物），只需启动 FastAPI 服务即可同时访问前端页面和后端 API：
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**访问地址：**
*   **主看板**：http://localhost:8000/
*   **管理后台**：http://localhost:8000/admin
*   **API 接口文档**：http://localhost:8000/docs

---

## 详细使用说明

### 1. 前端主看板 (Dashboard)
*   **K线图表与行情数据**：
    *   展示从 Binance 获取的 OHLCV（开高低收及成交量）数据。
    *   支持 `1m`, `15m`, `1h`, `4h`, `1d`, `7d`, `30d` 等不同时间维度的快速切换。
    *   K线左上角展示当前 MA5 和 MA10 均线数值。
*   **技术指标明细展示**：
    *   动态计算并以网格形式展示三大类指标：**趋势类** (MACD/EMA)、**动量类** (RSI)、**波动类** (ATR/Bollinger Bands)。
    *   支持鼠标悬浮到每个指标名称后的“气泡按钮”查看详细的指标定义和说明。
*   **风险与策略提示 (核心交易指南)**：
    *   基于当前技术指标评分（`tech_score`）及新闻情绪折算评分（`news_score`），生成综合评分。
    *   系统会根据综合评分给出智能操作建议（**买入 / 卖出 / 观望**）。
    *   基于 ATR 波动率提供明确的**建议止损价**与**建议止盈价**。
*   **新闻与巨鲸动向双轨信息流**：
    *   **左侧**：展示相关币种的新闻资讯（目前默认抓取 Chaincatcher），自动进行情绪分类 (positive/neutral/negative)。
    *   **右侧**：展示 Whale Alert 抓取的链上巨鲸动向，实时监控大额资金转移。
    *   支持文本长折叠限制（两行），以及底部的“加载更多”按钮进行双列分页。

### 2. 管理后台 (Admin Panel)
通过访问 `/admin` 路径进入。后台配置修改后，主看板将实时生效。
*   **币种管理**：添加/删除要监控的交易对（如 `BTCUSDT`, `ETHUSDT`）。添加后主页将自动同步至下拉菜单。
*   **技术指标管理**：支持自定义配置 `pandas-ta` 指标公式。例如：
    *   名称: `EMA_50`
    *   计算方法: `ta.ema(df['close'], length=50)`
*   **新闻源管理**：添加自定义新闻爬取源，除了常规网址，还支持本地数据库拉取协议（如 `local://` 协议，可从本地库查询文章内容作为新闻源）。
*   **提示词模板管理**：
    *   这是智能交易指南生成逻辑的核心。您可以自由修改买入、卖出、观望的文案。
    *   支持强大的动态变量注入：`{rsi}`, `{macd}`, `{total_score}`, `{whale_count}`, `{current_price}`, `{stop_loss}`, `{take_profit}`, `{bb_lower}`, `{bb_upper}` 等。

### 3. 策略回测 (Backtesting)
如果您需要验证当前评分模型与策略的准确性，可以运行后端的回测脚本。该脚本会自动倒推最近 30 天的数据进行模拟推演。
```bash
回测结果（默认配置）：针对最近 30 天（24h 趋势预测）的模拟回测结果如下：

- 测试周期 ：最近 30 天
- 有效信号天数 ：28 天（买入/卖出信号触发频率较高）
- 成功预测天数 ：12 天
- 预测胜率 ： 42.86% (基于纯技术面规则 + 情绪加权)
- 回测观察 ：
  - 在 3 月中旬的震荡行情中，模型表现出较强的“观望”保护机制。
  - 3 月底至 4 月初的下跌趋势中，模型成功捕捉到了多次“卖出”信号，有效规避了回调。
  - 近期（4 月 10 日 - 11 日）的上涨行情中，模型给出的“买入”建议均实现了收盘浮盈。

cd backend
source venv/bin/activate
python tests/backtest.py
```
**回测原理**：
*   提取 T0 日（开盘前）的 150 根历史 K 线数据，模拟当时的市场环境。
*   将历史数据喂给交易评分模型，计算出“买入/卖出/观望”操作建议。
*   将该建议与 T+1 日的实际高低点及收盘价进行验证（例如买入建议需在 T+1 日收盘浮盈或触及止盈线）。
*   最后输出详细的每天预测结果及 30 天的总预测胜率。
  
