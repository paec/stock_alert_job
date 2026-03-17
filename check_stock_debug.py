import yfinance as yf
from datetime import datetime

ticker = yf.Ticker("0050.TW")
df = ticker.history(period=f"10d", interval="1d")
print(df)

# 嘗試從 basic_info 抓取
try:
    # 這裡通常是最後成交時間 (秒級或毫秒級)
    ts = ticker.basic_info['last_price_timestamp'] 
    
    # 判斷是秒還是毫秒 (10位 vs 13位)
    if ts > 1e11: ts /= 1000 
    
    print(f"更新時間: {datetime.fromtimestamp(ts)}")
except Exception as e:
    print("basic_info 也不支援時間戳記")
    
    
# 抓取最近 1 分鐘的資料 (這會回傳包含最新一筆的時間)
df_now = ticker.history(period="1d", interval="1m")

if not df_now.empty:
    latest_time = df_now.index[-1]
    latest_price = df_now['Close'].iloc[-1]
    print(f"最新成交時間: {latest_time}")
    print(f"最新價格: {latest_price}")
else:
    print("目前非開盤時間或抓不到分鐘資料")
