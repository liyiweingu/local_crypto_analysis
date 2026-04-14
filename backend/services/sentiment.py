import re
import json
import sqlite3
import httpx
import asyncio

# 简单的币种字典
COIN_KEYWORDS = {
    'BTC': ['BTC', 'Bitcoin', '比特币', '大饼'],
    'ETH': ['ETH', 'Ethereum', '以太坊', '以太'],
    'BNB': ['BNB', 'Binance', '币安币'],
    'SOL': ['SOL', 'Solana', '索拉纳'],
    'DOT': ['DOT', 'Polkadot', '波卡'],
    'UNI': ['UNI', 'Uniswap']
}

# 情感词典（极简版）
POSITIVE_WORDS = ['大涨', '利好', '通过', '批准', '合作', '投资', '突破', '增长', '看涨', '创新', '生态', '活跃']
NEGATIVE_WORDS = ['大跌', '利空', '驳回', '拒绝', '黑客', '攻击', '漏洞', '起诉', '罚款', '困境', '下跌', '破产', '清算', '风险']

def get_ai_config():
    """获取数据库中的 AI 配置"""
    try:
        conn = sqlite3.connect('klines.db')
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM ai_config')
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}

def analyze_sentiment(text):
    """
    对文本（新闻标题/摘要）进行极简情绪分析和实体提取
    :param text: str
    :return: dict {'coins': list, 'sentiment': str, 'score': int}
    """
    if not text:
        return {'coins': [], 'sentiment': 'neutral', 'score': 0}
        
    text_lower = text.lower()
    found_coins = set()
    
    # 1. 提取币种
    for symbol, aliases in COIN_KEYWORDS.items():
        for alias in aliases:
            if alias.lower() in text_lower:
                found_coins.add(symbol)
                break
                
    # 2. 计算情感得分
    pos_score = sum(1 for word in POSITIVE_WORDS if word in text)
    neg_score = sum(1 for word in NEGATIVE_WORDS if word in text)
    
    # 简单评分机制：正向词数 - 负向词数
    score = pos_score - neg_score
    
    if score > 0:
        sentiment = 'positive'
    elif score < 0:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
        
    return {
        'coins': list(found_coins),
        'sentiment': sentiment,
        'score': score
    }

async def analyze_sentiments_batch_ai(texts):
    """
    使用配置的 AI 大模型批量分析情绪。如果未配置或调用失败，回退到本地词典分析。
    """
    config = get_ai_config()
    api_key = config.get('api_key', '')
    base_url = config.get('base_url', 'https://api.openai.com/v1')
    model_name = config.get('model_name', 'gpt-3.5-turbo')
    
    # 如果未配置 API Key，直接回退到本地规则分析
    if not api_key:
        return [analyze_sentiment(t) for t in texts]
        
    prompt = "请对以下每一条加密货币新闻标题进行情绪分析（仅限 positive, neutral, negative），并提取相关的币种符号（如 BTC, ETH，如无则返回空列表）。\n\n"
    for i, text in enumerate(texts):
        prompt += f"[{i}] {text}\n"
        
    prompt += "\n请严格以 JSON 数组格式返回结果，格式示例：\n"
    prompt += '[{"coins": ["BTC"], "sentiment": "positive", "score": 1}, {"coins": [], "sentiment": "neutral", "score": 0}]'
    prompt += "\n其中 score: positive 为 1, neutral 为 0, negative 为 -1。不要输出任何 Markdown 标记(如 ```json)或多余解释，只输出合法的 JSON 数组。"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "你是一个专业的加密货币市场情绪分析助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        # 使用 httpx 进行异步调用
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 兼容带有 /chat/completions 后缀或没有后缀的 base_url
            url = base_url if base_url.endswith('/chat/completions') else f"{base_url.rstrip('/')}/chat/completions"
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            # 清理可能的 markdown 标记
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
                
            results = json.loads(content)
            
            # 验证结果长度
            if len(results) == len(texts):
                return results
    except Exception as e:
        print(f"AI Sentiment Analysis Error: {e}, falling back to rule-based method.")
        
    # 如果失败，回退到本地词典
    return [analyze_sentiment(t) for t in texts]

if __name__ == "__main__":
    # 测试脚本
    test_cases = [
        "10 亿枚 DOT 凭空铸造，黑客却只赚了 23 万美元",
        "比特币突破 70000 美元，市场看涨情绪浓厚",
        "Uniswap 陷入创新困境",
        "以太坊生态活跃度增长，与多家机构达成合作"
    ]
    
    for tc in test_cases:
        res = analyze_sentiment(tc)
        print(f"Title: {tc}\nResult: {res}\n")
