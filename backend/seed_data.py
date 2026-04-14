import sqlite3
import time
import random
import httpx

def seed():
    conn = sqlite3.connect('klines.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            interval TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL
        )
    ''')
    cursor.execute('DELETE FROM klines')
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    intervals = ['15m', '1h', '4h', '1d', '1w', '1M']
    
    for symbol in symbols:
        for interval in intervals:
            print(f"Fetching {symbol} {interval}...")
            try:
                url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
                resp = httpx.get(url, timeout=5.0)
                resp.raise_for_status()
                data = resp.json()
                
                records = []
                for item in data:
                    records.append((symbol, interval, item[0], float(item[1]), float(item[2]), float(item[3]), float(item[4]), float(item[5])))
                    
                cursor.executemany('''
                    INSERT INTO klines (symbol, interval, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', records)
            except Exception as e:
                print(f"Failed to fetch real data for {symbol} {interval}: {e}. Generating mock data...")
                # Mock data generation
                base_prices = {'BTCUSDT': 70000, 'ETHUSDT': 3500, 'BNBUSDT': 600, 'SOLUSDT': 150}
                ms_map = {'15m': 15*60*1000, '1h': 60*60*1000, '4h': 4*60*60*1000, '1d': 24*60*60*1000, '1w': 7*24*60*60*1000, '1M': 30*24*60*60*1000}
                
                now = int(time.time() * 1000)
                ms = ms_map[interval]
                current_time = now - (200 * ms)
                current_price = base_prices[symbol]
                
                records = []
                for _ in range(200):
                    volatility = current_price * 0.005
                    open_p = current_price
                    close_p = open_p + random.uniform(-volatility, volatility)
                    high_p = max(open_p, close_p) + random.uniform(0, volatility/2)
                    low_p = min(open_p, close_p) - random.uniform(0, volatility/2)
                    volume = random.uniform(10, 1000)
                    
                    records.append((symbol, interval, current_time, open_p, high_p, low_p, close_p, volume))
                    
                    current_price = close_p
                    current_time += ms
                    
                cursor.executemany('''
                    INSERT INTO klines (symbol, interval, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', records)
                
    conn.commit()
    conn.close()
    print("Data seeded successfully.")

if __name__ == '__main__':
    seed()
