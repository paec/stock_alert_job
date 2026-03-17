import yfinance as yf
from datetime import datetime

ticker = yf.Ticker("0050.TW")
df = ticker.history(period=f"10d", interval="1d")
print(df)
# 取得最後一筆交易發生的時間戳記 (UTC)
last_time_utc = ticker.fast_info['last_trade_timestamp']
print(f"last_time_utc: {last_time_utc}")

# 轉換成可讀的本地時間
last_time_local = datetime.fromtimestamp(last_time_utc)

print(f"資料最後更新日期與時間: {last_time_local}")
