import yfinance as yf
from datetime import datetime

ticker = yf.Ticker("0050.TW")
df = ticker.history(period=f"10d", interval="1d")
print(f"history daily:\n {df}")
    
    
# 抓取最近 1 分鐘的資料 (這會回傳包含最新一筆的時間)
df_now = ticker.history(period="1d", interval="1m")
print(f"history min:\n {df_now}")
if not df_now.empty:
    latest_time = df_now.index[-1]
    latest_price = df_now['Close'].iloc[-1]
    print(f"history 最新成交時間: {latest_time}")
    print(f"history 最新價格: {latest_price}")
else:
    print("history 目前非開盤時間或抓不到分鐘資料")
print("\n\n")
    
symbol = "0050.TW" 
# 1. 下載日 K 資料 (例如最近 5 天)
df_daily = yf.download(symbol, period="5d", interval="1d")
print(f"daily download:\n {df_daily}")
# 2. 下載最近 1 天的分鐘線 (用來取得「最後成交時間」)
# 因為只需要最後一筆時間，所以 period="1d", interval="1m" 負擔最小
df_min = yf.download(symbol, period="1d", interval="1m")
print(f"min download:\n\n {df_min}")
# 取得 1m 資料的最後一個索引 (即為該股目前的最新成交時間)
if not df_min.empty:
    last_update_time = df_min.index[-1]
else:
    last_update_time = "無法取得更新時間"


# 3. 整理輸出
print(f"=== {symbol} 查詢結果 ===")
# 取得今日日線的最末行資料
latest_row = df_daily.tail(1).copy()

# 把精確時間補進去 (新增一個欄位)
latest_row['Last_Update_Time'] = last_update_time

print(latest_row[['Open', 'High', 'Low', 'Close', 'Volume', 'Last_Update_Time']])

# 如果你想把這個時間套用到整張日線表的最後一列
df_daily.loc[df_daily.index[-1], 'Update_Timestamp'] = last_update_time
