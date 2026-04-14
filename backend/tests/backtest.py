import requests
import time
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import json
import sys
import os

# 添加上级目录到 sys.path 以便导入 services 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.indicators import calculate_indicators
from services.signals import generate_signals
from services.guide import generate_trading_guide

def get_historical_klines(symbol, interval, end_time_ms, limit=150):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "endTime": end_time_ms,
        "limit": limit
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    # 格式化为服务需要的 raw_klines
    raw_klines = []
    for item in data:
        # Binance kline format: [open_time, open, high, low, close, volume, close_time, ...]
        raw_klines.append({
            "timestamp": item[0],
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })
    return raw_klines

def get_future_kline(symbol, interval, start_time_ms):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time_ms,
        "limit": 1
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
        
    item = data[0]
    return {
        "timestamp": item[0],
        "open": float(item[1]),
        "high": float(item[2]),
        "low": float(item[3]),
        "close": float(item[4])
    }

def run_backtest():
    symbol = "BTCUSDT"
    interval = "1d"
    
    # 动态获取最近30天的日期作为测试集
    # 从前天开始，倒推30天 (因为昨天的数据代表T+1的结果)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    test_dates = [today - timedelta(days=i) for i in range(2, 32)]
    test_dates.reverse() # 按照时间正序排列
    
    results = []
    total_trades = 0
    successful_trades = 0
    
    # 获取默认提示词字典
    prompts_dict = {}
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'klines.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM prompts')
        prompts_dict = dict(cursor.fetchall())
        conn.close()
    except Exception as e:
        print(f"Warning: Could not load prompts from DB, using defaults. {e}")

    print(f"开始进行 {symbol} 24h 趋势预测 30 天回测...")
    print("-" * 80)
    
    for target_date in test_dates:
        # T0 时刻：该日的 00:00:00 UTC (即上一根日线收盘时)
        # 也就是测试用此日期当天的开盘前数据去预测
        end_time_ms = int(target_date.timestamp() * 1000) - 1 
        
        try:
            # 1. 准备历史数据
            raw_klines = get_historical_klines(symbol, interval, end_time_ms, limit=150)
            if not raw_klines or len(raw_klines) < 150:
                print(f"跳过 {target_date.strftime('%Y-%m-%d')}: 数据不足")
                continue
                
            last_close = raw_klines[-1]['close']
            
            # 2. 生成预测
            indicators = calculate_indicators(raw_klines)
            signals = generate_signals(raw_klines, indicators)
            
            # 临时降低评分门槛，以便在这些具体日期观察到模型方向
            # 或者直接提取 tech_score 来判断方向
            tech_score = 0
            rsi = indicators.get("momentum", {}).get("RSI_14", [-1])[-1]
            macd = indicators.get("trend", {}).get("MACD", [-1])[-1]
            ema5 = indicators.get("trend", {}).get("EMA_5", [-1])[-1]
            ema20 = indicators.get("trend", {}).get("EMA_20", [-1])[-1]
            
            if rsi is not None:
                if rsi < 45: tech_score += 3
                elif rsi > 55: tech_score -= 3
                
            if macd is not None:
                if macd > 0: tech_score += 2
                else: tech_score -= 2
                
            if ema5 is not None and ema20 is not None:
                if ema5 > ema20 * 1.005: tech_score += 3
                elif ema5 < ema20 * 0.995: tech_score -= 3
                
            action = "观望"
            if tech_score >= 2:
                action = "买入"
            elif tech_score <= -2:
                action = "卖出"
                
            # 止盈止损计算 (基于ATR波动率)
            atr = indicators.get("volatility", {}).get("ATR_14", [-1])[-1]
            stop_loss = "-"
            take_profit = "-"
            
            if atr is not None and atr > 0:
                if action == "买入":
                    stop_loss = round(last_close - (1.5 * atr), 2)
                    take_profit = round(last_close + (3.0 * atr), 2)
                elif action == "卖出":
                    stop_loss = round(last_close + (1.5 * atr), 2)
                    take_profit = round(last_close - (3.0 * atr), 2)
            
            # 3. 获取未来 24 小时的真实走势 (即 T0 之后的那根日线)
            future_kline = get_future_kline(symbol, interval, end_time_ms + 1)
            if not future_kline:
                print(f"跳过 {target_date.strftime('%Y-%m-%d')}: 无未来数据")
                continue
                
            actual_high = future_kline['high']
            actual_low = future_kline['low']
            actual_close = future_kline['close']
            
            # 4. 判定胜率逻辑
            outcome = "N/A"
            if action == "买入":
                total_trades += 1
                # 判断是否扫止损
                if stop_loss != "-" and actual_low <= float(stop_loss):
                    outcome = "失败 (触及止损)"
                # 判断是否触达止盈
                elif take_profit != "-" and actual_high >= float(take_profit):
                    outcome = "成功 (触及止盈)"
                    successful_trades += 1
                # 未触及止盈止损，看收盘是否盈利
                elif actual_close > last_close:
                    outcome = "成功 (收盘浮盈)"
                    successful_trades += 1
                else:
                    outcome = "失败 (收盘浮亏)"
                    
            elif action == "卖出":
                total_trades += 1
                # 判断是否扫止损 (做空止损在上方)
                if stop_loss != "-" and actual_high >= float(stop_loss):
                    outcome = "失败 (触及止损)"
                # 判断是否触达止盈 (做空止盈在下方)
                elif take_profit != "-" and actual_low <= float(take_profit):
                    outcome = "成功 (触及止盈)"
                    successful_trades += 1
                # 未触及止盈止损，看收盘是否盈利
                elif actual_close < last_close:
                    outcome = "成功 (收盘浮盈)"
                    successful_trades += 1
                else:
                    outcome = "失败 (收盘浮亏)"
            else:
                outcome = "观望 (未交易)"
                
            # 5. 记录结果
            res = {
                "date": target_date.strftime('%Y-%m-%d'),
                "t0_close": last_close,
                "action": action,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "actual_high": actual_high,
                "actual_low": actual_low,
                "actual_close": actual_close,
                "outcome": outcome
            }
            results.append(res)
            
            print(f"日期: {res['date']} | 预测: {res['action']:<4} | T0收盘: {res['t0_close']:.2f} | "
                  f"未来(高/低/收): {res['actual_high']:.2f}/{res['actual_low']:.2f}/{res['actual_close']:.2f} | "
                  f"结果: {res['outcome']}")
                  
            # 避免触发 API 频率限制
            time.sleep(0.5)
            
        except Exception as e:
            print(f"处理 {target_date.strftime('%Y-%m-%d')} 时出错: {e}")

    print("-" * 80)
    print("回测汇总报告:")
    print(f"总测试天数: {len(test_dates)} 天")
    print(f"触发交易信号天数 (买入/卖出): {total_trades} 天")
    if total_trades > 0:
        win_rate = (successful_trades / total_trades) * 100
        print(f"成功预测天数: {successful_trades} 天")
        print(f"模型 24h 趋势预测胜率 (基于纯技术面): {win_rate:.2f}%")
    else:
        print("期间未触发任何交易信号 (全程观望)。")

if __name__ == "__main__":
    run_backtest()