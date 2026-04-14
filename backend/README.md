# 虚拟币趋势预测后端 (Crypto Prediction Backend)

本目录为项目的 FastAPI Python 后端服务。它负责整合币安历史 K 线数据、计算多种技术指标（依赖 `pandas-ta`）、抓取分析新闻与巨鲸动向（依赖 `requests`、`BeautifulSoup`），并生成综合交易指南与风险策略评分。此外，它还承担着全栈应用的统一服务端口代理与静态资源托管职责。

## 技术栈
- **框架**: FastAPI (高性能 API 服务)
- **数据库**: SQLite (`klines.db` 存储历史 K线、技术指标定义、提示词模板)
- **核心计算**: `pandas`, `pandas-ta` (支持自定义评估公式 `eval`)
- **数据爬取**: `requests`, `BeautifulSoup` (Chaincatcher 资讯抓取、Whale Alert API 反向工程)
- **工具**: `httpx` (异步请求), `uvicorn` (ASGI 服务器)

## 环境配置

1. **创建并激活虚拟环境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # MacOS/Linux
   # venv\Scripts\activate   # Windows
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **数据库初始化**
   运行初始化脚本以生成 `klines.db`，并导入默认的币种、指标公式与新闻源。
   ```bash
   python init_db.py
   python update_db.py  # 更新智能提示词模板
   ```
   *(可选)* 遇到 Binance 接口限制时，可以运行本地种子拉取进行测试数据的准备：
   ```bash
   python seed_data.py
   ```

## 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
启动后：
- `http://localhost:8000/api/klines` 提供 K线图与技术指标数据。
- `http://localhost:8000/api/news` 提供新闻情绪分析与巨鲸动向数据。
- 若 `../frontend/dist` 存在，后端会自动托管前端页面。此时访问 `http://localhost:8000/` 即可进入主看板。

## 目录说明

- `main.py`: 后端入口。注册了所有的 `/api/*` 路由，处理跨域 (CORS)，并挂载 `../frontend/dist` 下的静态文件与 SPA (Single Page Application) 回退处理。
- `init_db.py` & `update_db.py`: SQLite 数据库结构初始化和配置预置数据的脚本。
- `schemas.py`: Pydantic 数据验证模型，用于 `/admin` 接口。
- `seed_data.py`: 用于下载/缓存历史数据至本地，以便于在没有网络的离线环境下测试。
- `services/`: 核心业务模块。
  - `indicators.py`: 利用 `pandas-ta` 解析数据库中的动态公式字符串。
  - `news_scraper.py`: 负责抓取 Chaincatcher 的内容、Whale Alert 的链上资金大额转移 (含 JSON 伪装破解)。支持 `local://` 协议解析。
  - `sentiment.py`: 关键词匹配、实体识别及情绪归类 (positive/neutral/negative)。
  - `scoring.py`: 交易评分模型，基于新闻权威性、时间衰减加权、情绪强度，生成 -100 到 100 分。
  - `guide.py`: 交易指南模块。通过动态模板 `safe_format` 将评分结果 (技术面/情绪面/总分) 和指标值转换为文本操作建议和止盈止损位。
- `tests/backtest.py`: T+1 趋势验证脚本。提取 T0 开盘前的 K线，生成预测，并在未来 30 天进行 T+1 对比以评估胜率。