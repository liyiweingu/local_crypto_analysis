import sqlite3

def init_db():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    
    # 币种表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            symbol TEXT PRIMARY KEY,
            name TEXT
        )
    ''')
    
    # 自定义指标表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            calc_method TEXT,
            description TEXT
        )
    ''')
    
    # 新闻源表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            url TEXT
        )
    ''')
    
    # 本地内容库表 (用于模拟本地文章作为新闻源)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS local_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT,
            timestamp INTEGER
        )
    ''')
    
    # 提示词模板表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT
        )
    ''')
    
    # AI 配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # 插入默认数据
    default_coins = [
        ('BTCUSDT', 'BTC/USDT'),
        ('ETHUSDT', 'ETH/USDT'),
        ('BNBUSDT', 'BNB/USDT'),
        ('SOLUSDT', 'SOL/USDT')
    ]
    cursor.executemany('INSERT OR IGNORE INTO coins (symbol, name) VALUES (?, ?)', default_coins)
    
    default_sources = [
        ('ChainCatcher', 'https://www.chaincatcher.com/'),
        ('本地内容库', 'local://db')
    ]
    cursor.executemany('INSERT OR IGNORE INTO news_sources (name, url) VALUES (?, ?)', default_sources)
    
    import time
    now = int(time.time())
    mock_local_news = [
        ('BTC突破历史新高，本地分析师强烈看涨', 'local://article/1', now),
        ('ETH网络拥堵导致手续费飙升，引发社区不满', 'local://article/2', now - 3600),
        ('SOL生态持续繁荣，多个项目宣布空投', 'local://article/3', now - 7200),
        ('BNB智能链进行安全升级，防范潜在风险', 'local://article/4', now - 86400),
        ('加密市场迎来大调整，比特币短线下挫5%', 'local://article/5', now - 2 * 86400)
    ]
    # 清空并重新插入模拟数据以保持最新时间戳
    cursor.execute('DELETE FROM local_news')
    cursor.executemany('INSERT INTO local_news (title, link, timestamp) VALUES (?, ?, ?)', mock_local_news)
    
    default_prompts = [
        ('status_up', '短期均线(EMA5: {ema5})高于中期均线(EMA20: {ema20})超过1%，呈现明确的上升趋势。', '市场状态(上升)，可用变量: {ema5}, {ema20}'),
        ('status_down', '短期均线(EMA5: {ema5})低于中期均线(EMA20: {ema20})超过1%，呈现明确的下跌趋势。', '市场状态(下跌)，可用变量: {ema5}, {ema20}'),
        ('status_neutral', '短期均线与中期均线纠缠，市场处于震荡整理区间。', '市场状态(震荡)'),
        ('action_buy', '综合评分({total_score})大于5分。技术面得分{tech_score}，情绪面得分{news_score} (含新闻与{whale_count}笔巨鲸动向，其中{whale_bullish}笔利多)。各项因子共振向好，建议寻找低点买入。', '操作建议(买入)，可用变量: {total_score}, {tech_score}, {news_score}, {whale_count}, {whale_bullish}, {whale_bearish}'),
        ('action_sell', '综合评分({total_score})小于-5分。技术面得分{tech_score}，情绪面得分{news_score} (含新闻与{whale_count}笔巨鲸动向，其中{whale_bearish}笔利空)。各项因子偏向空头，建议逢高卖出或减仓。', '操作建议(卖出)，可用变量: {total_score}, {tech_score}, {news_score}, {whale_count}, {whale_bullish}, {whale_bearish}'),
        ('action_neutral', '综合评分({total_score})处于中性区间。技术面得分{tech_score}，情绪面得分{news_score} (含新闻与{whale_count}笔巨鲸动向)。目前市场未见明确方向，建议结合链上数据持币观望。', '操作建议(观望)，可用变量: {total_score}, {tech_score}, {news_score}, {whale_count}, {whale_bullish}, {whale_bearish}'),
        ('total_score_process', '技术面得分({tech_score}分) + 情绪面折算得分({news_score}分，含新闻与巨鲸动作) = {total_score}分。', '综合评分过程，可用变量: {tech_score}, {news_score}, {total_score}, {whale_count}, {whale_bullish}, {whale_bearish}'),
        ('sentiment_score_process', '基于近期新闻资讯与{whale_count}笔巨鲸链上转移(利多{whale_bullish}笔/利空{whale_bearish}笔)，经时间衰减加权得出综合情绪得分 {sentiment_score} 分 (满分±100)。', '情绪得分过程，可用变量: {sentiment_score}, {whale_count}, {whale_bullish}, {whale_bearish}')
    ]
    cursor.executemany('INSERT OR IGNORE INTO prompts (key, value, description) VALUES (?, ?, ?)', default_prompts)
    
    default_ai_config = [
        ('api_key', ''),
        ('base_url', 'https://api.openai.com/v1'),
        ('model_name', 'gpt-3.5-turbo')
    ]
    cursor.executemany('INSERT OR IGNORE INTO ai_config (key, value) VALUES (?, ?)', default_ai_config)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("DB Initialized")