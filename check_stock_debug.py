import yfinance as yf
from datetime import datetime

ticker = yf.Ticker("0050.TW")
df = ticker.history(period=f"10d", interval="1d")
close_series = df["Close"].squeeze() # 只取 Close 欄位並 squeeze 成 series (index 是date，value 是Close)

print(df)
try:
    ts_ms = ticker.fast_info['last_price_timestamp'] # 有些版本回傳毫秒 (ms)
    
    # 如果數字太大（毫秒級），除以 1000 轉為秒
    if ts_ms > 1e11: 
        ts = ts_ms / 1000
    else:
        ts = ts_ms
        
    last_time = datetime.fromtimestamp(ts)
    print(f"資料更新時間: {last_time}")
except KeyError:
    # 如果還是不行，印出所有可用欄位檢查
    print("可用欄位有:", ticker.fast_info.keys())
