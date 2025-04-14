import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
from sklearn.ensemble import IsolationForest
from telegram_bot import send_telegram_alert
from datetime import datetime

ASSETS = {
    "US Stocks": ["AAPL", "MSFT", "GOOGL"],
    "ETFs": ["SPY", "QQQ", "VTI"],
    "Bonds": ["TLT", "IEF"],
    "FX": ["JPY=X", "EURUSD=X"]
}

conn = sqlite3.connect("liquidity_cache.db")
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS asset_data (
    symbol TEXT,
    date TEXT,
    adj_close REAL,
    volume INTEGER,
    return REAL,
    amihud REAL,
    z_score REAL,
    if_anomaly INTEGER,
    PRIMARY KEY (symbol, date)
)
''')
conn.commit()

def process_asset(symbol):
    df = yf.download(symbol, period="6mo", interval="1d")
    if df.empty or len(df) < 30:
        print(f"❌ {symbol} 無足夠資料")
        return

    df['Return'] = df['Adj Close'].pct_change()
    df['Amihud'] = (abs(df['Return']) / df['Volume']).replace([np.inf, -np.inf], np.nan).fillna(0)
    df['Z_Score'] = (df['Amihud'] - df['Amihud'].rolling(20).mean()).fillna(0) / df['Amihud'].rolling(20).std().replace(0, np.nan).fillna(1)
    model = IsolationForest(contamination=0.05, random_state=42)
    df['IF_Anomaly'] = model.fit_predict(df[['Amihud']].fillna(0))

    df = df.reset_index()
    df.rename(columns={'Date': 'date', 'Adj Close': 'adj_close', 'Volume': 'volume'}, inplace=True)
    df = df[['date', 'adj_close', 'volume', 'Return', 'Amihud', 'Z_Score', 'IF_Anomaly']]

    for _, row in df.iterrows():
        cursor.execute('''
            INSERT OR REPLACE INTO asset_data (symbol, date, adj_close, volume, return, amihud, z_score, if_anomaly)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, row['date'], row['adj_close'], row['volume'], row['Return'], row['Amihud'], row['Z_Score'], row['IF_Anomaly']))

    conn.commit()

    # 推播邏輯
    latest = df.iloc[-1]
    r = latest['Return']
    z = latest['Z_Score']
    a = latest['Amihud']

    if abs(z) > 2.5 or a > 0.007 or r < -0.05:
        alert_msg = f"""
📣 財經儀表板異常警示
🔸 資產：{symbol}
📅 日期：{latest['date'].strftime('%Y-%m-%d') if isinstance(latest['date'], pd.Timestamp) else latest['date']}
📈 Amihud：{a:.4f}（Z={z:+.2f}）
📉 報酬率：{r * 100:.2f}%
🚨 狀態：*異常流動性 或 價格劇烈變動*
"""
        send_telegram_alert(alert_msg.strip())

if __name__ == '__main__':
    for category, symbols in ASSETS.items():
        print(f"📦 分類：{category}")
        for symbol in symbols:
            print(f"⏳ 處理資產：{symbol}")
            process_asset(symbol)
    print("✅ 所有資產更新完成並檢查推播！")
