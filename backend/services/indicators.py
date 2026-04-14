import pandas as pd
import pandas_ta as ta

def calculate_indicators(klines_data):
    """
    计算技术指标
    :param klines_data: list of dict, 每个dict包含 {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
    :return: dict 包含各指标结果的列表
    """
    if not klines_data:
        return {}

    # 转换为 DataFrame
    df = pd.DataFrame(klines_data)
    # 确保数据类型正确
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    # 1. 趋势类指标 (Trend)
    # EMA
    df.ta.ema(length=5, append=True)
    df.ta.ema(length=10, append=True)
    df.ta.ema(length=20, append=True)
    
    # MACD
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    
    # ADX
    df.ta.adx(length=14, append=True)

    # 2. 动量类指标 (Momentum)
    # RSI
    df.ta.rsi(length=14, append=True)
    
    # Stochastic Oscillator
    df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
    
    # Momentum
    df.ta.mom(length=10, append=True)

    # 3. 波动类指标 (Volatility)
    # Bollinger Bands
    df.ta.bbands(length=20, std=2, append=True)
    
    # ATR
    df.ta.atr(length=14, append=True)

    # 4. 成交类指标 (Volume)
    # OBV
    df.ta.obv(append=True)
    
    # Volume MA
    df['VOL_MA10'] = ta.sma(df['volume'], length=10)

    import numpy as np
    # 处理 NaN 值，替换为 None (以便 JSON 序列化为 null)
    df = df.replace({np.nan: None})

    # 提取特征结构化输出
    features = {
        "timestamp": df["timestamp"].tolist(),
        
        "trend": {
            "EMA_5": df.get("EMA_5", pd.Series([None]*len(df))).tolist(),
            "EMA_10": df.get("EMA_10", pd.Series([None]*len(df))).tolist(),
            "EMA_20": df.get("EMA_20", pd.Series([None]*len(df))).tolist(),
            "MACD": df.get("MACD_12_26_9", pd.Series([None]*len(df))).tolist(),
            "MACD_signal": df.get("MACDs_12_26_9", pd.Series([None]*len(df))).tolist(),
            "MACD_hist": df.get("MACDh_12_26_9", pd.Series([None]*len(df))).tolist(),
            "ADX": df.get("ADX_14", pd.Series([None]*len(df))).tolist()
        },
        
        "momentum": {
            "RSI_14": df.get("RSI_14", pd.Series([None]*len(df))).tolist(),
            "STOCH_k": df.get("STOCHk_14_3_3", pd.Series([None]*len(df))).tolist(),
            "STOCH_d": df.get("STOCHd_14_3_3", pd.Series([None]*len(df))).tolist(),
            "MOM_10": df.get("MOM_10", pd.Series([None]*len(df))).tolist()
        },
        
        "volatility": {
            "BB_lower": df.get("BBL_20_2.0_2.0", pd.Series([None]*len(df))).tolist(),
            "BB_middle": df.get("BBM_20_2.0_2.0", pd.Series([None]*len(df))).tolist(),
            "BB_upper": df.get("BBU_20_2.0_2.0", pd.Series([None]*len(df))).tolist(),
            "ATR_14": df.get("ATRr_14", pd.Series([None]*len(df))).tolist()
        },
        
        "volume": {
            "OBV": df.get("OBV", pd.Series([None]*len(df))).tolist(),
            "VOL_MA10": df.get("VOL_MA10", pd.Series([None]*len(df))).tolist()
        }
    }
    
    return features
