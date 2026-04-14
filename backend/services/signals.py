def generate_signals(klines_data, indicators):
    """
    根据行情数据和指标生成交易信号
    klines_data: list of dict {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
    indicators: dict 从 calculate_indicators 返回的结果
    
    返回 signals: list of dict, 每个信号包含 timestamp, type, name, description
    """
    signals = []
    
    if not klines_data or not indicators or len(klines_data) < 2:
        return signals
        
    trend = indicators.get("trend", {})
    momentum = indicators.get("momentum", {})
    volatility = indicators.get("volatility", {})
    volume_ind = indicators.get("volume", {})
    
    for i in range(1, len(klines_data)):
        current_kline = klines_data[i]
        prev_kline = klines_data[i-1]
        ts = current_kline['timestamp']
        close_p = current_kline['close']
        volume = current_kline['volume']
        
        # 1. 技术因子 - RSI 超买超卖
        rsi = momentum.get("RSI_14", [])[i]
        if rsi is not None:
            if rsi > 70:
                signals.append({"timestamp": ts, "type": "bearish", "category": "technical", "name": "RSI超买", "desc": f"RSI达到 {rsi:.1f}，存在回调风险"})
            elif rsi < 30:
                signals.append({"timestamp": ts, "type": "bullish", "category": "technical", "name": "RSI超卖", "desc": f"RSI降至 {rsi:.1f}，存在反弹机会"})
                
        # 2. 技术因子 - 均线多空 (MA5 和 MA10 交叉)
        ma5_curr = trend.get("EMA_5", [])[i]
        ma10_curr = trend.get("EMA_10", [])[i]
        ma5_prev = trend.get("EMA_5", [])[i-1]
        ma10_prev = trend.get("EMA_10", [])[i-1]
        
        if ma5_curr is not None and ma10_curr is not None and ma5_prev is not None and ma10_prev is not None:
            if ma5_prev <= ma10_prev and ma5_curr > ma10_curr:
                signals.append({"timestamp": ts, "type": "bullish", "category": "technical", "name": "均线金叉", "desc": "MA5上穿MA10，短期看涨"})
            elif ma5_prev >= ma10_prev and ma5_curr < ma10_curr:
                signals.append({"timestamp": ts, "type": "bearish", "category": "technical", "name": "均线死叉", "desc": "MA5下穿MA10，短期看跌"})
                
        # 3. 技术因子 - MACD 金叉死叉
        macd_curr = trend.get("MACD", [])[i]
        signal_curr = trend.get("MACD_signal", [])[i]
        macd_prev = trend.get("MACD", [])[i-1]
        signal_prev = trend.get("MACD_signal", [])[i-1]
        
        if macd_curr is not None and signal_curr is not None and macd_prev is not None and signal_prev is not None:
            if macd_prev <= signal_prev and macd_curr > signal_curr:
                signals.append({"timestamp": ts, "type": "bullish", "category": "technical", "name": "MACD金叉", "desc": "MACD线上穿信号线"})
            elif macd_prev >= signal_prev and macd_curr < signal_curr:
                signals.append({"timestamp": ts, "type": "bearish", "category": "technical", "name": "MACD死叉", "desc": "MACD线下穿信号线"})
                
        # 4. 结构因子 - 布林带突破 (支撑/阻力)
        bb_upper = volatility.get("BB_upper", [])[i]
        bb_lower = volatility.get("BB_lower", [])[i]
        
        if bb_upper is not None and close_p > bb_upper:
            signals.append({"timestamp": ts, "type": "bullish", "category": "structural", "name": "向上突破", "desc": "价格突破布林带上轨阻力"})
        elif bb_lower is not None and close_p < bb_lower:
            signals.append({"timestamp": ts, "type": "bearish", "category": "structural", "name": "向下突破", "desc": "价格跌破布林带下轨支撑"})
            
        # 5. 市场行为因子 - 异常波动/成交量放大
        vol_ma10 = volume_ind.get("VOL_MA10", [])[i]
        if vol_ma10 is not None and vol_ma10 > 0:
            if volume > vol_ma10 * 2.5:
                # 区分放量上涨还是放量下跌
                if close_p > current_kline['open']:
                    signals.append({"timestamp": ts, "type": "bullish", "category": "market", "name": "放量上涨", "desc": "成交量超过10日均量2.5倍且收阳"})
                else:
                    signals.append({"timestamp": ts, "type": "bearish", "category": "market", "name": "放量下跌", "desc": "成交量超过10日均量2.5倍且收阴"})

    return signals