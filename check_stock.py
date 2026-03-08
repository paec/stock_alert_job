import os

import requests
import yfinance as yf

from flex_msg_tpl import build_bubble, build_carousel

API_URL = os.getenv("CONFIG_API_URL", "https://your-pythonanywhere-domain/api/config")
LINE_TOKEN = os.getenv("LINE_TOKEN", "")

def send_line(msg):
    if not LINE_TOKEN:
        print("LINE_TOKEN is not set. Skip sending message.")
        return

    url = "https://api.line.me/v2/bot/message/broadcast"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messages": [
            {
                "type": "flex",
                "altText": "股票漲跌報表",
                "contents": msg  # 這裡直接傳入 carousel or bubble 的內容
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data, timeout=20)
    if response.status_code >= 400:
        print(f"LINE API error: {response.status_code} {response.text}")
    print()(f"LINE API response: {response.status_code} {response.text}")

def check_stock(symbol, x_days, y_percent):
    # 1. 下載股票資料，取得最近 x_days+5 天的歷史收盤價
    data = yf.download(symbol, period=f"{x_days+5}d", progress=False, auto_adjust=False)

    # 2. 檢查資料量是否足夠
    if len(data) < x_days + 1:
        print(f"{symbol}: not enough data")
        return None

    # 3. 取得收盤價序列，計算今日與 x_days 前的收盤價
    print(data["Close"])
    today = float(data["Close"].iloc[-1].item())  # 今日收盤價
    past = float(data["Close"].iloc[-(x_days)].item())  # x_days 前收盤價
    print(f"{symbol} today: {today}, {x_days} days ago: {past}")

    # 4. 計算漲跌幅百分比
    drop = (today - past) / past * 100

    # 5. 判斷是否觸發警示，並印出結果
    alert = "ALERT" if drop <= -float(y_percent) else "not triggered"
    print(f"{symbol}: {drop:.2f}% in {x_days} days (threshold: {y_percent}%) - {alert}")

    # 6. 處理收盤價歷史資料，取最近 x_days 筆
    close_data = data["Close"].iloc[-x_days:]
    start_date = close_data.index[0].strftime("%m-%d")  # 起始日期
    end_date = close_data.index[-1].strftime("%m-%d")   # 結束日期

    # 7. 格式化收盤價歷史，一筆一個 row
    pairs = [(close_data.index[i].strftime("%m-%d"), float(close_data.iloc[i].item())) for i in range(len(close_data))]
    rows = [f"{date}: {price:.2f}" for date, price in pairs]
    history_text = "\n".join(rows)

    # 8. 回傳 bubble dict 給 flex message
    return build_bubble(symbol, start_date, end_date, x_days, drop, y_percent, history_text)


def main():
    default_rules = [
        {"symbol": "0050.TW", "x_days": 5, "y_percent": 5},
        {"symbol": "VOO", "x_days": 5, "y_percent": 5},
        {"symbol": "VT", "x_days": 5, "y_percent": 5}
    ]
    try:
        config = requests.get(API_URL, timeout=20).json()
        rules = config.get("rules", [])
    except Exception as e:
        print(f"API error: {e}, use default rule")
        rules = default_rules

    if not rules:
        rules = default_rules

    bubbles = []
    for rule in rules:
        symbol = str(rule.get("symbol", "")).strip().upper()
        x_days = int(rule["x_days"])
        y_percent = float(rule["y_percent"])
        if symbol:
            bubble = check_stock(symbol, x_days, y_percent)
            if bubble:
                bubbles.append(bubble)

    if bubbles:
        carousel = build_carousel(bubbles)
        send_line(carousel)


if __name__ == "__main__":
    main()
