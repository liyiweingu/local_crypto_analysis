import sqlite3

def update_db():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    
    updates = [
        (
            'action_buy', 
            '综合评分达到 {total_score} 分。技术面得分 {tech_score} 分 (RSI: {rsi}, MACD: {macd})，情绪面折算得分 {news_score} 分 (含新闻情绪与 {whale_count} 笔巨鲸动向，其中 {whale_bullish} 笔利多)。各项因子共振向好，建议以当前价 {current_price} 为基准寻找低点买入，并在 {stop_loss} 处设置止损，目标止盈位 {take_profit}。', 
            '操作建议(买入)，可用变量: {total_score}, {tech_score}, {news_score}, {whale_count}, {whale_bullish}, {whale_bearish}, {rsi}, {macd}, {current_price}, {stop_loss}, {take_profit}'
        ),
        (
            'action_sell', 
            '综合评分低至 {total_score} 分。技术面得分 {tech_score} 分 (RSI: {rsi}, MACD: {macd})，情绪面折算得分 {news_score} 分 (含新闻情绪与 {whale_count} 笔巨鲸动向，其中 {whale_bearish} 笔利空)。各项因子偏向空头，建议以当前价 {current_price} 为基准逢高卖出或减仓，上方止损参考 {stop_loss}，目标回调位 {take_profit}。', 
            '操作建议(卖出)，可用变量: {total_score}, {tech_score}, {news_score}, {whale_count}, {whale_bullish}, {whale_bearish}, {rsi}, {macd}, {current_price}, {stop_loss}, {take_profit}'
        ),
        (
            'action_neutral', 
            '综合评分为 {total_score} 分，处于中性区间。技术面得分 {tech_score} 分，情绪面折算得分 {news_score} 分 (含新闻与 {whale_count} 笔巨鲸动向)。目前市场(当前价 {current_price})未见明确方向，布林带上下轨区间为 [{bb_lower}, {bb_upper}]，建议结合链上数据持币观望。', 
            '操作建议(观望)，可用变量: {total_score}, {tech_score}, {news_score}, {whale_count}, {bb_lower}, {bb_upper}, {current_price}'
        ),
        (
            'status_up', 
            '短期均线(EMA5: {ema5})上穿中期均线(EMA20: {ema20})，且当前价格 {current_price} 运行在均线之上，呈现明确的上升趋势。', 
            '市场状态(上升)，可用变量: {ema5}, {ema20}, {current_price}'
        ),
        (
            'status_down', 
            '短期均线(EMA5: {ema5})下穿中期均线(EMA20: {ema20})，且当前价格 {current_price} 运行在均线之下，呈现明确的下跌趋势。', 
            '市场状态(下跌)，可用变量: {ema5}, {ema20}, {current_price}'
        ),
        (
            'status_neutral', 
            '短期均线(EMA5: {ema5})与中期均线(EMA20: {ema20})相互纠缠，当前价格 {current_price} 暂无明确突破，市场处于震荡整理区间。', 
            '市场状态(震荡)，可用变量: {ema5}, {ema20}, {current_price}'
        ),
        (
            'total_score_process', 
            '综合评分 = 技术面得分({tech_score}分，参考RSI/MACD/均线) + 情绪面折算得分({news_score}分，含新闻与巨鲸动作) = {total_score} 分。', 
            '综合评分过程，可用变量: {tech_score}, {news_score}, {total_score}'
        ),
        (
            'sentiment_score_process', 
            '基于近期新闻资讯与 {whale_count} 笔巨鲸链上转移 (利多 {whale_bullish} 笔 / 利空 {whale_bearish} 笔)，经时间衰减加权得出综合情绪得分 {sentiment_score} 分 (满分±100)。', 
            '情绪得分过程，可用变量: {sentiment_score}, {whale_count}, {whale_bullish}, {whale_bearish}'
        )
    ]
    
    for key, value, desc in updates:
        cursor.execute('UPDATE prompts SET value=?, description=? WHERE key=?', (value, desc, key))
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_db()
    print("Prompts Updated")
