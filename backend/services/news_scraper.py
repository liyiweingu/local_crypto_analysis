import requests
from bs4 import BeautifulSoup
import re
import time
import sqlite3

import random
import csv
from io import StringIO

def fetch_whale_alert(target_coin):
    """
    抓取 Whale Alert 巨鲸动态 (真实数据源)
    使用 whale-alert.io 的内部 public API
    严格根据 target_coin 过滤，避免出现无关币种。
    """
    url = "https://whale-alert.io/data.json?alerts=200"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    alerts = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        raw_alerts = data.get("alerts", [])
        
        # 目标币种标签，例如 "#BTC"
        target_tag = f"#{target_coin.upper()}"
        
        for line in raw_alerts:
            # 使用 csv reader 解析含有双引号的 CSV 行
            reader = csv.reader(StringIO(line))
            parts = list(reader)[0]
            
            if len(parts) < 6:
                continue
                
            timestamp_str = parts[0]
            emojis = parts[1]
            amount_and_coin = parts[2]
            value_usd = parts[3]
            action_text = parts[4]
            link = parts[5]
            
            # 严格过滤：只保留目标币种
            # 必须匹配如 "#BTC" 或 "#USDT"，避免子串匹配错误
            if target_tag not in amount_and_coin.upper():
                continue
                
            ts = int(timestamp_str)
            
            # 判断方向决定情绪
            action_lower = action_text.lower()
            
            # 简单的自然语言推断：
            # 如果是 unknown wallet -> 某交易所 (通常预示抛售，利空)
            # 如果是 某交易所 -> unknown wallet (通常预示囤币，利多)
            # 这里的 action_text 形如 " transferred from unknown wallet to #Coinbase"
            
            is_from_unknown = "unknown" in action_lower and "from unknown" in action_lower
            is_to_unknown = "unknown" in action_lower and "to unknown" in action_lower
            
            # 交易所名字往往带有 #，比如 #Coinbase, #Binance 等
            if is_from_unknown and not is_to_unknown:
                sentiment = "negative"
                action_zh = action_text.replace("transferred from", "从").replace("to", "转移至").replace("unknown wallet", "未知钱包")
                title = f"{emojis} {amount_and_coin} ({value_usd}){action_zh} (可能砸盘)"
            elif is_to_unknown and not is_from_unknown:
                sentiment = "positive"
                action_zh = action_text.replace("transferred from", "从").replace("to", "转移至").replace("unknown wallet", "未知钱包")
                title = f"{emojis} {amount_and_coin} ({value_usd}){action_zh} (可能是囤币)"
            else:
                sentiment = "neutral"
                action_zh = action_text.replace("transferred from", "从").replace("to", "转移至").replace("unknown wallet", "未知钱包")
                title = f"{emojis} {amount_and_coin} ({value_usd}){action_zh}"
                
            alerts.append({
                "title": title,
                "link": link,
                "timestamp": ts,
                "type": "whale_alert",
                "sentiment_res": {
                    "coins": [target_coin],
                    "sentiment": sentiment,
                    "score": 5 if sentiment == "positive" else (-5 if sentiment == "negative" else 0)
                }
            })
            
    except Exception as e:
        print(f"Error fetching whale alerts: {e}")
        
    # 按时间降序
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    return alerts

def fetch_local_news():
    """
    从本地内容库获取新闻文章
    """
    try:
        conn = sqlite3.connect('klines.db')
        cursor = conn.cursor()
        cursor.execute('SELECT title, link, timestamp FROM local_news ORDER BY timestamp DESC LIMIT 20')
        rows = cursor.fetchall()
        conn.close()
        return [{'title': r[0], 'link': r[1], 'timestamp': r[2]} for r in rows]
    except Exception as e:
        print(f"Error fetching local news: {e}")
        return []

def fetch_news_from_sources(sources):
    """
    根据配置的源列表分发爬取任务
    sources: [{'name': '...', 'url': '...'}]
    """
    all_news = []
    for src in sources:
        url = src.get('url', '').lower()
        if 'chaincatcher.com' in url:
            all_news.extend(fetch_chaincatcher_news())
        elif url.startswith('local://'):
            all_news.extend(fetch_local_news())
        # 可以根据需要扩展其他源
            
    # 按时间降序排列并去重
    seen_titles = set()
    unique_news = []
    for news in sorted(all_news, key=lambda x: x['timestamp'], reverse=True):
        if news['title'] not in seen_titles:
            seen_titles.add(news['title'])
            unique_news.append(news)
            
    return unique_news

def fetch_chaincatcher_news():
    """
    抓取 ChainCatcher 首页新闻
    返回去重后的新闻列表 [{'title': '...', 'link': '...', 'timestamp': ...}]
    """
    url = 'https://www.chaincatcher.com/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    news_list = []
    seen_titles = set()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取新闻链接
        # ChainCatcher 的新闻链接通常是 /article/xxx 或 /news/xxx
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            title = a_tag.get_text(strip=True)
            
            # 清理标题中的换行符和多余空格
            title = re.sub(r'\s+', ' ', title)
            # 去除前缀如 "文章 " 或 "快讯"
            title = re.sub(r'^(文章|快讯|深度|专题)\s*', '', title)
            
            if ('/article/' in href or '/news/' in href) and len(title) > 5:
                # 如果去重后仍有重复，根据 url 判断，如果同样 url 已经有了，则不重复加
                # 这里简化处理：直接使用链接或标题作为唯一键
                if title not in seen_titles:
                    seen_titles.add(title)
                    
                    full_link = href if href.startswith('http') else f"https://www.chaincatcher.com{href}"
                    
                    news_list.append({
                        'title': title,
                        'link': full_link,
                        'timestamp': int(time.time()) # 简单起见使用当前时间
                    })
                    
        return news_list
        
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

if __name__ == "__main__":
    news = fetch_chaincatcher_news()
    for n in news[:5]:
        print(n)