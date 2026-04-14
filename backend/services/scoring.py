import time

def calculate_sentiment_score(news_items):
    """
    计算基于新闻的交易情绪评分
    sentiment_score = 加权(新闻权威性 + 时间衰减 + 情绪强度)
    
    news_items: list of dict {'title': str, 'timestamp': int, 'sentiment_res': dict}
    返回: float 综合情绪得分 (-100 到 100)
    """
    if not news_items:
        return 0.0
        
    current_time = int(time.time())
    total_score = 0.0
    total_weight = 0.0
    
    for item in news_items:
        # 1. 情绪强度 (-1, 0, 1) 乘以词汇分数
        s_res = item.get('sentiment_res', {})
        base_score = s_res.get('score', 0)
        sentiment_type = s_res.get('sentiment', 'neutral')
        
        if sentiment_type == 'positive':
            polarity = 1
        elif sentiment_type == 'negative':
            polarity = -1
        else:
            polarity = 0
            
        # 避免基础分数为0但有极性的情况
        intensity = abs(base_score) if base_score != 0 else 1
        raw_score = polarity * intensity * 10
        
        # 2. 时间衰减 (24小时内权重最高，超过7天权重极低)
        news_time = item.get('timestamp', current_time)
        hours_diff = (current_time - news_time) / 3600.0
        
        if hours_diff < 0:
            hours_diff = 0
            
        # 衰减函数: e^(-0.05 * hours) 
        # 0小时 -> 1.0, 24小时 -> 0.3, 48小时 -> 0.09
        import math
        time_weight = math.exp(-0.05 * hours_diff)
        
        # 3. 新闻权威性 (简单设定所有来源权重为 1.0)
        authority_weight = 1.0
        
        # 综合权重
        final_weight = time_weight * authority_weight
        
        total_score += raw_score * final_weight
        total_weight += final_weight
        
    if total_weight == 0:
        return 0.0
        
    # 归一化到 -100 到 100 之间
    normalized_score = (total_score / total_weight)
    
    # 限制边界
    normalized_score = max(-100.0, min(100.0, normalized_score))
    
    return round(normalized_score, 2)
