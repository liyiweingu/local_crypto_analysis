def generate_trading_guide(klines_data, indicators, signals, sentiment_score, prompts_dict=None, whale_alerts=None):
    """
    生成交易指南
    """
    if prompts_dict is None:
        prompts_dict = {}
        
    if whale_alerts is None:
        whale_alerts = []
        
    whale_count = len(whale_alerts)
    whale_bullish = sum(1 for w in whale_alerts if w.get('sentiment_res', {}).get('sentiment') == 'positive')
    whale_bearish = sum(1 for w in whale_alerts if w.get('sentiment_res', {}).get('sentiment') == 'negative')
    
    whale_count_str = str(whale_count)
    whale_bullish_str = str(whale_bullish)
    whale_bearish_str = str(whale_bearish)
        
    def get_prompt(key, default_text):
        return prompts_dict.get(key, default_text)
        
    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'
            
    def safe_format(template, **kwargs):
        if not template: return ""
        return template.format_map(SafeDict(**kwargs))
        
    if not klines_data or not indicators:
        return {
            "status": "未知",
            "action": "观望",
            "risk": "数据不足，无法评估",
            "stop_loss": "-",
            "take_profit": "-"
        }
        
    last_kline = klines_data[-1]
    current_price = last_kline['close']
    
    # 提取最新指标
    trend = indicators.get("trend", {})
    momentum = indicators.get("momentum", {})
    volatility = indicators.get("volatility", {})
    
    ema5 = trend.get("EMA_5", [-1])[-1]
    ema20 = trend.get("EMA_20", [-1])[-1]
    rsi = momentum.get("RSI_14", [-1])[-1]
    macd = trend.get("MACD", [-1])[-1]
    
    bb_upper = volatility.get("BB_upper", [-1])[-1]
    bb_lower = volatility.get("BB_lower", [-1])[-1]
    atr = volatility.get("ATR_14", [-1])[-1]
    
    ema5_str = f"{ema5:.2f}" if ema5 is not None else "-"
    ema20_str = f"{ema20:.2f}" if ema20 is not None else "-"
    
    # 分析市场状态 (仅计算逻辑)
    status = "震荡"
    if ema5 is not None and ema20 is not None:
        if ema5 > ema20 * 1.01:
            status = "上升"
        elif ema5 < ema20 * 0.99:
            status = "下跌"
            
    # 计算技术面得分 (-10 到 10)
    tech_score = 0
    if rsi is not None:
        if rsi < 35: tech_score += 3
        elif rsi > 65: tech_score -= 3
        
    if macd is not None:
        if macd > 0: tech_score += 2
        else: tech_score -= 2
        
    if status == "上升": tech_score += 3
    elif status == "下跌": tech_score -= 3
    
    # 结合新闻情绪得分 (-100 到 100)
    # 将情绪得分缩放到 -10 到 10
    news_score = sentiment_score / 10.0
    
    total_score = tech_score + news_score
    
    tech_score_str = f"{tech_score}"
    news_score_str = f"{news_score:.2f}"
    total_score_str = f"{total_score:.2f}"
    sentiment_score_str = f"{sentiment_score}"
    
    current_price_str = f"{current_price:.2f}"
    rsi_str = f"{rsi:.2f}" if rsi is not None else "-"
    macd_str = f"{macd:.2f}" if macd is not None else "-"
    bb_upper_str = f"{bb_upper:.2f}" if bb_upper is not None else "-"
    bb_lower_str = f"{bb_lower:.2f}" if bb_lower is not None else "-"
    atr_str = f"{atr:.2f}" if atr is not None else "-"

    # 操作建议与止盈止损计算
    if total_score > 5:
        action = "买入"
    elif total_score < -5:
        action = "卖出"
    else:
        action = "观望"
        
    # 止盈止损计算 (基于ATR波动率)
    stop_loss = "-"
    take_profit = "-"
    
    if atr is not None and atr > 0:
        if action == "买入":
            stop_loss = f"{round(current_price - (1.5 * atr), 2):.2f}"
            take_profit = f"{round(current_price + (3.0 * atr), 2):.2f}"
        elif action == "卖出":
            stop_loss = f"{round(current_price + (1.5 * atr), 2):.2f}"
            take_profit = f"{round(current_price - (3.0 * atr), 2):.2f}"

    # 完善 format_kwargs 变量集合
    format_kwargs = {
        "status": status,
        "action": action,
        "ema5": ema5_str,
        "ema20": ema20_str,
        "current_price": current_price_str,
        "rsi": rsi_str,
        "macd": macd_str,
        "bb_upper": bb_upper_str,
        "bb_lower": bb_lower_str,
        "atr": atr_str,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "tech_score": tech_score_str,
        "news_score": news_score_str,
        "sentiment_score": sentiment_score_str,
        "total_score": total_score_str,
        "whale_count": whale_count_str,
        "whale_bullish": whale_bullish_str,
        "whale_bearish": whale_bearish_str
    }
    
    # 生成各部分的文案
    if status == "上升":
        status_reason = safe_format(get_prompt("status_up", "短期均线(EMA5: {ema5})高于中期均线(EMA20: {ema20})超过1%，呈现明确的上升趋势。"), **format_kwargs)
    elif status == "下跌":
        status_reason = safe_format(get_prompt("status_down", "短期均线(EMA5: {ema5})低于中期均线(EMA20: {ema20})超过1%，呈现明确的下跌趋势。"), **format_kwargs)
    else:
        status_reason = safe_format(get_prompt("status_neutral", "短期均线与中期均线纠缠，市场处于震荡整理区间。"), **format_kwargs)
            
    # 评分过程
    total_score_process = safe_format(
        get_prompt("total_score_process", "技术面得分({tech_score}分) + 情绪面折算得分({news_score}分，含新闻与巨鲸动作) = {total_score}分。"),
        **format_kwargs
    )
    sentiment_score_process = safe_format(
        get_prompt("sentiment_score_process", "基于近期新闻资讯与{whale_count}笔巨鲸链上转移(利多{whale_bullish}笔/利空{whale_bearish}笔)，经时间衰减加权得出综合情绪得分 {sentiment_score} 分 (满分±100)。"),
        **format_kwargs
    )
    
    # 操作建议生成文案
    if action == "买入":
        action_reason = safe_format(
            get_prompt("action_buy", "综合评分({total_score})大于5分。技术面得分{tech_score}，情绪面得分{news_score} (含新闻与{whale_count}笔巨鲸动向，其中{whale_bullish}笔利多)。各项因子共振向好，建议寻找低点买入。"),
            **format_kwargs
        )
    elif action == "卖出":
        action_reason = safe_format(
            get_prompt("action_sell", "综合评分({total_score})小于-5分。技术面得分{tech_score}，情绪面得分{news_score} (含新闻与{whale_count}笔巨鲸动向，其中{whale_bearish}笔利空)。各项因子偏向空头，建议逢高卖出或减仓。"),
            **format_kwargs
        )
    else:
        action_reason = safe_format(
            get_prompt("action_neutral", "综合评分({total_score})处于中性区间。技术面得分{tech_score}，情绪面得分{news_score} (含新闻与{whale_count}笔巨鲸动向)。目前市场未见明确方向，建议结合链上数据持币观望。"),
            **format_kwargs
        )
            
    # 风险提示
    risk = "本次汇总结果仅供参考，不做任何交易指导。"
        
    return {
        "status": status,
        "status_reason": status_reason,
        "action": action,
        "action_reason": action_reason,
        "risk": risk,
        "stop_loss": stop_loss if stop_loss == "-" else float(stop_loss),
        "take_profit": take_profit if take_profit == "-" else float(take_profit),
        "sentiment_score": sentiment_score,
        "sentiment_score_process": sentiment_score_process,
        "total_score": round(total_score, 2),
        "total_score_process": total_score_process
    }
