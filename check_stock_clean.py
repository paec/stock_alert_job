import datetime
import os
from dataclasses import dataclass
from typing import Any

import pytz
import requests
import yfinance as yf

from flex_msg_tpl import build_bubble, build_carousel

API_URL = os.getenv("CONFIG_API_URL", "https://your-pythonanywhere-domain/api/config")
LINE_TOKEN = os.getenv("LINE_TOKEN", "")
LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
DEFAULT_LOOKBACK_PADDING_DAYS = 5

@dataclass(frozen=True)
class Rule:
    symbol: str
    x_days: int
    y_percent: float


def send_line(msg: dict[str, Any], token: str = LINE_TOKEN) -> None:
    if not token:
        print("LINE_TOKEN is not set. Skip sending message.")
        return

    payload = {
        "messages": [
            {
                "type": "flex",
                "altText": "股票漲跌報表",
                "contents": msg,
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        LINE_BROADCAST_URL,
        headers=headers,
        json=payload,
        timeout=20,
    )
    if response.status_code >= 400:
        print(f"LINE API error: {response.status_code} {response.text}")
    print(f"LINE API response: {response.status_code} {response.text}")


def fetch_rules(api_url: str = API_URL) -> list[Rule]:
    default_rules = [
        Rule("0050.TW", 5, 5.0),
        Rule("VOO", 5, 5.0),
        Rule("VT", 5, 5.0),
    ]

    try:
        config = requests.get(api_url, timeout=20).json()
        raw_rules = config.get("rules", [])
    except Exception as exc:
        print(f"API error: {exc}, use default rule")
        return default_rules

    parsed_rules = [parse_rule(item) for item in raw_rules]
    valid_rules = [rule for rule in parsed_rules if rule is not None]
    return valid_rules or default_rules


def parse_rule(rule_data: dict[str, Any]) -> Rule | None:
    try:
        symbol = str(rule_data.get("symbol", "")).strip().upper()
        x_days = int(rule_data["x_days"])
        y_percent = float(rule_data["y_percent"])
    except (TypeError, ValueError, KeyError):
        return None

    if not symbol or x_days <= 0:
        return None

    return Rule(symbol=symbol, x_days=x_days, y_percent=y_percent)


def is_market_open(symbol: str, now: datetime.datetime) -> bool:
    # 判斷市場 & 時區 & 時段（now 由外部傳入）
    if symbol.endswith(".TW"):
        tz = pytz.timezone("Asia/Taipei")
        session_start = datetime.time(8, 30)
        session_end = datetime.time(15, 0)
        market_name = "台股"
    else:
        tz = pytz.timezone("America/New_York")
        session_start = datetime.time(8, 30)
        session_end = datetime.time(17, 0)
        market_name = "美股"

    if not (session_start <= now.time() <= session_end):
        print(f"{symbol} ({market_name}) 非交易時段，跳過")
        return False

    ticker = yf.Ticker(symbol)
    min_data = ticker.history(period="1d", interval="1m")

    if min_data.empty:
        print(f"{symbol}: 今日無 1 分鐘資料，可能尚未開盤或休市，跳過")
        return False

    last_bar_time = min_data.index[-1]
    if last_bar_time.tzinfo is None:
        last_bar_time = tz.localize(last_bar_time)
    else:
        last_bar_time = last_bar_time.astimezone(tz)
    
    diff_min = (now - last_bar_time).total_seconds() / 60.0
    is_recent = diff_min <= 3

    if not is_recent:
        print(f"{symbol}: 最後一筆 1 分鐘資料距今 {diff_min:.1f} 分鐘，視為未開盤，跳過")
        return False

    return True

def download_close_prices(symbol: str, x_days: int):
    return yf.download(
        symbol,
        period=f"{x_days + DEFAULT_LOOKBACK_PADDING_DAYS}d",
        progress=False,
        auto_adjust=False,
    )["Close"].squeeze()  # ensure Series even when yfinance returns single-column DataFrame


def build_stock_bubble(rule: Rule) -> dict[str, Any] | None:
    # 取得 now 並決定時區 (AI提示: 可以抽出去嗎?)
    if rule.symbol.endswith(".TW"):
        tz = pytz.timezone("Asia/Taipei")
    else:
        tz = pytz.timezone("America/New_York")
    now = datetime.datetime.now(tz)  # 取得正確時區的現在時間
    
    # 修改：傳 now 給 is_market_open
    if not is_market_open(rule.symbol, now):
        return None

    close_series = download_close_prices(rule.symbol, rule.x_days)
    print(f"{rule.symbol} close_series: {close_series}") #保留這行來確認資料是否正確下載
    if len(close_series) < rule.x_days + 1:
        print(f"{rule.symbol}: not enough data")
        return None

    today = float(close_series.iloc[-1].item())
    past = float(close_series.iloc[-rule.x_days].item())
    drop = (today - past) / past * 100
    
    #Refactor point1 start# #AI提示#
    # 條件 1：漲跌幅絕對值 >= y_percent
    hit_threshold = (drop < 0) and (abs(drop) >= float(rule.y_percent))
    # 條件 2：現在是整點
    is_full_hour = (now.minute != 0 + 5)

    if not (hit_threshold or is_full_hour):
        print(f"{rule.symbol}: 變動未超過門檻且非整點，不送出 LINE 訊息")
        return None
     #Refactor point1 end#
     
    alert = "ALERT" if drop <= -rule.y_percent else "not triggered"
    
    print(f"{rule.symbol}: {drop:.2f}% in {rule.x_days} days " f"(threshold: {rule.y_percent}%) - {alert}")

    history_series = close_series.iloc[-rule.x_days :]
    start_date = history_series.index[0].strftime("%m-%d")
    end_date = history_series.index[-1].strftime("%m-%d")
    history_text = format_history(history_series)

    return build_bubble(rule.symbol, start_date,end_date, rule.x_days, 
                        drop, rule.y_percent, history_text)


def format_history(close_series) -> str:
    lines = []
    for idx, price in zip(close_series.index, close_series.values):
        lines.append(f"{idx.strftime('%m-%d')}: {float(price):.2f}")
    return "\n".join(lines)


def main() -> None:
    rules = fetch_rules() # [Rule("0050.TW", 5, 5.0)]

    bubbles = []
    for rule in rules:
        bubble = build_stock_bubble(rule)
        if bubble is not None:
            bubbles.append(bubble)

    if not bubbles:
        print("No valid stock report to send.")
        return
    
    send_line(build_carousel(bubbles))


if __name__ == "__main__":
    main()
