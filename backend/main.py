from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
import sqlite3
import os
from datetime import datetime

# 导入指标计算模块
from services.indicators import calculate_indicators
from services.signals import generate_signals
from services.news_scraper import fetch_news_from_sources, fetch_whale_alert
from services.sentiment import analyze_sentiment, analyze_sentiments_batch_ai
from services.scoring import calculate_sentiment_score
from services.guide import generate_trading_guide
from schemas import Coin, Indicator, NewsSource, PromptsUpdate, AIConfigUpdate

app = FastAPI(title="Kline Data API")

# 配置CORS，允许前端应用访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 实际生产环境中应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/klines")
async def get_klines(symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 100):
    """
    获取Binance K线历史数据
    symbol: 交易对，默认 BTCUSDT
    interval: 时间间隔，默认 1d
    limit: 数据条数，默认 100
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
    
    try:
        conn = sqlite3.connect('klines.db')
        cursor = conn.cursor()
        
        # 查询本地数据库获取数据
        cursor.execute('''
            SELECT timestamp, open, high, low, close, volume 
            FROM klines 
            WHERE symbol=? AND interval=? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (symbol.upper(), interval, limit))
        
        rows = cursor.fetchall()
        
        # 如果本地数据库没有数据，尝试从 Binance API 实时获取并存入数据库
        if not rows:
            print(f"No local data for {symbol} {interval}, fetching from Binance...")
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": symbol.upper(), "interval": interval, "limit": 200}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    new_records = []
                    for item in data:
                        new_records.append((symbol.upper(), interval, item[0], float(item[1]), float(item[2]), float(item[3]), float(item[4]), float(item[5])))
                    cursor.executemany('''
                        INSERT INTO klines (symbol, interval, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', new_records)
                    conn.commit()
                    
                    # 重新查询
                    cursor.execute('''
                        SELECT timestamp, open, high, low, close, volume 
                        FROM klines 
                        WHERE symbol=? AND interval=? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (symbol.upper(), interval, limit))
                    rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return {"categoryData": [], "values": [], "indicators": {}}
            
        # 按照时间升序排列
        rows.reverse()
        
        category_data = []
        values = []
        raw_klines = []
        
        # 判断时间格式：如果是1天及以上，仅显示日期；如果是日内级别（15m, 1h, 4h），显示时间
        if interval in ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h']:
            time_format = '%Y-%m-%d %H:%M'
        else:
            time_format = '%Y-%m-%d'

        for row in rows:
            timestamp, open_p, high_p, low_p, close_p, volume = row
            # 转换时间戳为日期字符串
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime(time_format)
            category_data.append(date_str)
            
            # ECharts 蜡烛图需要的数据格式: [开盘, 收盘, 最低, 最高]
            values.append([
                float(open_p),
                float(close_p),
                float(low_p),
                float(high_p)
            ])
            
            # 组装用于计算指标的原始数据
            raw_klines.append({
                "timestamp": date_str,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume
            })
            
        # 计算技术指标
        indicators = calculate_indicators(raw_klines)
        
        # 计算自定义技术指标
        cursor = conn.cursor()
        cursor.execute('SELECT name, calc_method FROM custom_indicators')
        custom_inds = cursor.fetchall()
        if custom_inds:
            import pandas as pd
            import pandas_ta as ta
            import numpy as np
            
            df = pd.DataFrame(raw_klines)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            if "custom" not in indicators:
                indicators["custom"] = {}
                
            for ind_name, calc_method in custom_inds:
                try:
                    # 使用 eval 动态执行 pandas_ta 计算 (需小心安全性，这里为内部工具信任输入)
                    res = eval(calc_method)
                    if isinstance(res, pd.Series):
                        # 处理 NaN 值
                        res = res.replace({np.nan: None})
                        indicators["custom"][ind_name] = res.tolist()
                    elif isinstance(res, pd.DataFrame):
                        res = res.replace({np.nan: None})
                        # 取 DataFrame 的最后一列或指定列
                        indicators["custom"][ind_name] = res.iloc[:, -1].tolist()
                except Exception as e:
                    print(f"Error calculating custom indicator {ind_name}: {e}")
        
        conn.close()# 计算交易信号
        signals = generate_signals(raw_klines, indicators)
            
        conn.close()
        return {
            "categoryData": category_data,
            "values": values,
            "indicators": indicators,
            "signals": signals
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching from local db: {str(e)}")

@app.get("/api/analysis")
async def get_analysis(symbol: str = "BTCUSDT", interval: str = "1d"):
    """
    获取交易指南和新闻情绪分析
    """
    try:
        conn = sqlite3.connect('klines.db')
        cursor = conn.cursor()
        
        # 查询最近的数据
        cursor.execute('''
            SELECT timestamp, open, high, low, close, volume 
            FROM klines 
            WHERE symbol=? AND interval=? 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''', (symbol.upper(), interval))
        
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return {"error": "No data found for the given symbol and interval"}
            
        rows.reverse()
        
        raw_klines = []
        for row in rows:
            timestamp, open_p, high_p, low_p, close_p, volume = row
            raw_klines.append({
                "timestamp": timestamp,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume
            })
            
        # 计算技术指标
        indicators = calculate_indicators(raw_klines)
        
        # 计算自定义技术指标
        cursor = conn.cursor()
        cursor.execute('SELECT name, calc_method FROM custom_indicators')
        custom_inds = cursor.fetchall()
        if custom_inds:
            import pandas as pd
            import pandas_ta as ta
            import numpy as np
            
            df = pd.DataFrame(raw_klines)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            if "custom" not in indicators:
                indicators["custom"] = {}
                
            for ind_name, calc_method in custom_inds:
                try:
                    # 使用 eval 动态执行 pandas_ta 计算 (需小心安全性，这里为内部工具信任输入)
                    res = eval(calc_method)
                    if isinstance(res, pd.Series):
                        # 处理 NaN 值
                        res = res.replace({np.nan: None})
                        indicators["custom"][ind_name] = res.tolist()
                    elif isinstance(res, pd.DataFrame):
                        res = res.replace({np.nan: None})
                        # 取 DataFrame 的最后一列或指定列
                        indicators["custom"][ind_name] = res.iloc[:, -1].tolist()
                except Exception as e:
                    print(f"Error calculating custom indicator {ind_name}: {e}")
                    
        # 获取新闻源配置
        cursor = conn.cursor()
        cursor.execute('SELECT name, url FROM news_sources')
        sources_rows = cursor.fetchall()
        news_sources = [{'name': r[0], 'url': r[1]} for r in sources_rows]
        
        # 获取提示词配置
        cursor.execute('SELECT key, value FROM prompts')
        prompts_dict = dict(cursor.fetchall())
        
        # 默认回退（如果没有配置源）
        if not news_sources:
            news_sources = [{'name': 'ChainCatcher', 'url': 'https://www.chaincatcher.com/'}]
                    
        # 动态分发爬取新闻
        news_list = fetch_news_from_sources(news_sources)
        analyzed_news = []
        
        # 获取目标币种名称 (如 BTC)
        target_coin = symbol.upper().replace('USDT', '')
        
        # 批量 AI 情绪分析
        if news_list:
            news_titles = [item['title'] for item in news_list]
            ai_sentiments = await analyze_sentiments_batch_ai(news_titles)
        else:
            ai_sentiments = []
        
        for i, item in enumerate(news_list):
            s_res = ai_sentiments[i] if i < len(ai_sentiments) else analyze_sentiment(item['title'])
            item['sentiment_res'] = s_res
            item['type'] = 'news' # 标记为普通新闻
            # 过滤出包含目标币种的新闻，如果列表为空则可能是宏观新闻，也保留计算
            if target_coin in s_res.get('coins', []) or not s_res.get('coins', []):
                analyzed_news.append(item)
                
        # 抓取并追加 Whale Alert 巨鲸动态 (仅目标币种)
        whale_alerts = fetch_whale_alert(target_coin)
        
        # 将新闻与巨鲸动态合并
        all_sentiments = analyzed_news + whale_alerts
        
        # 计算综合情绪得分
        sentiment_score = calculate_sentiment_score(all_sentiments)
        
        # 生成交易指南
        signals = generate_signals(raw_klines, indicators)
        guide = generate_trading_guide(raw_klines, indicators, signals, sentiment_score, prompts_dict, whale_alerts)
        
        conn.close()
        
        return {
            "guide": guide,
            "sentiment_score": sentiment_score,
            "news": analyzed_news,
            "whale_alerts": whale_alerts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during analysis: {str(e)}")

@app.get("/api/admin/coins")
async def get_coins():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, name FROM coins')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": row[0], "name": row[1]} for row in rows]

@app.post("/api/admin/coins")
async def add_coin(coin: Coin):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO coins (symbol, name) VALUES (?, ?)', (coin.symbol.upper(), coin.name))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Coin already exists")
    finally:
        conn.close()
    return {"message": "success"}

@app.delete("/api/admin/coins/{symbol}")
async def delete_coin(symbol: str):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM coins WHERE symbol=?', (symbol.upper(),))
    conn.commit()
    conn.close()
    return {"message": "success"}

@app.get("/api/admin/indicators")
async def get_indicators():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, calc_method, description FROM custom_indicators')
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "calc_method": row[2], "description": row[3]} for row in rows]

@app.post("/api/admin/indicators")
async def add_indicator(indicator: Indicator):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO custom_indicators (name, calc_method, description) VALUES (?, ?, ?)',
                       (indicator.name, indicator.calc_method, indicator.description))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Indicator name already exists")
    finally:
        conn.close()
    return {"message": "success"}

@app.delete("/api/admin/indicators/{id}")
async def delete_indicator(id: int):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM custom_indicators WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return {"message": "success"}

@app.get("/api/admin/sources")
async def get_sources():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, url FROM news_sources')
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "url": row[2]} for row in rows]

@app.post("/api/admin/sources")
async def add_source(source: NewsSource):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO news_sources (name, url) VALUES (?, ?)', (source.name, source.url))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Source already exists")
    finally:
        conn.close()
    return {"message": "success"}

@app.delete("/api/admin/sources/{id}")
async def delete_source(id: int):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM news_sources WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return {"message": "success"}

@app.get("/api/admin/prompts")
async def get_prompts():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('SELECT key, value, description FROM prompts')
    rows = cursor.fetchall()
    conn.close()
    return [{"key": row[0], "value": row[1], "description": row[2]} for row in rows]

@app.put("/api/admin/prompts")
async def update_prompts(payload: PromptsUpdate):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    for key, value in payload.prompts.items():
        cursor.execute('UPDATE prompts SET value=? WHERE key=?', (value, key))
    conn.commit()
    conn.close()
    return {"message": "success"}

@app.get("/api/admin/ai_config")
async def get_ai_config():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM ai_config')
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

@app.put("/api/admin/ai_config")
async def update_ai_config(payload: AIConfigUpdate):
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    for key, value in payload.configs.items():
        cursor.execute('UPDATE ai_config SET value=? WHERE key=?', (value, key))
        if cursor.rowcount == 0:
            cursor.execute('INSERT INTO ai_config (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
    return {"message": "success"}

# 配置前端静态文件服务
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
        # API 路由已经被上方捕获，剩余的非API路由返回 index.html 支持SPA
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        file_path = os.path.join(frontend_dist, catchall)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)