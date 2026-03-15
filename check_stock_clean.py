import datetime
import os
from dataclasses import dataclass
from typing import Any

import pytz
import requests
import yfinance as yf
from shioaji_utils import get_tw_close_prices, format_tw_close_series, logout_api

from flex_msg_tpl import build_bubble, build_carousel

API_URL = os.getenv("CONFIG_API_URL", "https://your-pythonanywhere-domain/api/config")
LINE_TOKEN = os.getenv("LINE_TOKEN", "")
LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
DEFAULT_LOOKBACK_PADDING_DAYS = 5


def _env_to_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


FORCE_SEND_REPORT = _env_to_bool("FORCE_SEND_REPORT", False)

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
    default_rules = [Rule("0050.TW", 5, 5.0),Rule("VOO", 5, 5.0),Rule("VT", 5, 5.0)]

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


def _get_session_hours(market_name: str) -> tuple[datetime.time, datetime.time]:
    if market_name == "台股":
        return datetime.time(8, 0), datetime.time(15, 0)
    return datetime.time(8, 0), datetime.time(17, 0)


def is_market_open(symbol: str, now: datetime.datetime) -> bool:
    # return True
    tz, market_name = get_market_timezone(symbol)
    session_start, session_end = _get_session_hours(market_name)
    local_now = now.astimezone(tz)

    if not (session_start <= local_now.time() <= session_end):
        print(f"{symbol} ({market_name}) 非交易時段，跳過")
        return False

    return True


def has_today_data(close_series, tz, symbol: str) -> bool:
    """
    檢查 yf.download 回來的日線 close_series
    最後一筆資料的日期是否為「今天」（以 tz 為準）。
    """
    if close_series.empty:
        print(f"{symbol}: close_series 為空，跳過")
        return False

    now = datetime.datetime.now(tz)
    last_bar_time = close_series.index[-1]

    # 對齊時區
    if last_bar_time.tzinfo is None:
        last_bar_time = tz.localize(last_bar_time)
    else:
        last_bar_time = last_bar_time.astimezone(tz)

    last_bar_date = last_bar_time.date()
    today_date = now.date()
    
    if last_bar_date != today_date:
        print(
            f"{symbol}: 最近一筆日線資料日期為 {last_bar_date} "
            f"（今日 {today_date}），視為尚未開盤或休市，跳過"
        )
        return False

    return True


def get_market_timezone(symbol: str) -> tuple[pytz.BaseTzInfo, str]:
    """
    依照股票代號判斷所屬市場與時區。
    回傳 (tz, market_name)
    """
    if symbol.endswith(".TW"):
        return pytz.timezone("Asia/Taipei"), "台股"
    else:
        return pytz.timezone("America/New_York"), "美股"
        
def is_today_final_report_time(market_name: str, now: datetime.datetime):
    if market_name == "台股":
        return now.hour == 14 and now.minute == 5
    else:
        return now.hour == 16 and now.minute == 45


def download_close_prices(symbol: str, x_days: int):
    if symbol.endswith(".TW"): # 台股用 Sinopac
        close_df = get_tw_close_prices(symbol, x_days + DEFAULT_LOOKBACK_PADDING_DAYS)
        close_series = format_tw_close_series(close_df)
    else: # 美股用 yfinance
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{x_days + DEFAULT_LOOKBACK_PADDING_DAYS}d", interval="1d")
        close_series = df["Close"].squeeze() # 只取 Close 欄位並 squeeze 成 series (index 是date，value 是Close)

    print(f"{symbol} close_series: {close_series}")
    return close_series


def calculate_price_change_pct(close_series, x_days: int) -> float:
    today = float(close_series.iloc[-1].item())
    past = float(close_series.iloc[-x_days].item())
    return (today - past) / past * 100


def _exceeds_drop_threshold(drop: float, y_percent: float) -> bool:
    return drop < 0 and abs(drop) >= y_percent


def build_stock_bubble(rule: Rule) -> dict[str, Any] | None:
    # 決定時區並取得 now 
    tz, market_name = get_market_timezone(rule.symbol)
    now = datetime.datetime.now(tz)

    # 先用「時間區間」判斷是否有可能是開盤時間
    if not FORCE_SEND_REPORT and not is_market_open(rule.symbol, now):
        return None

    # 只下載一次 close_series，後面全部重用
    close_series = download_close_prices(rule.symbol, rule.x_days)

    # 最近一筆日線資料日期是否為今日，否則視為尚未開盤或休市，跳過
    if not FORCE_SEND_REPORT and not has_today_data(close_series, tz, rule.symbol):
        return None
        
    if len(close_series) < rule.x_days + 1:
        print(f"{rule.symbol}: not enough data")
        return None

    drop = calculate_price_change_pct(close_series, rule.x_days)
    is_final_report = is_today_final_report_time(market_name, now)
    should_send = FORCE_SEND_REPORT or _exceeds_drop_threshold(drop, rule.y_percent) or is_final_report

    if not should_send:
        print(f"{rule.symbol}: {drop:.2f}% 變動未超過門檻且非最終報表時間，不送出 LINE 訊息")
        return None

    if FORCE_SEND_REPORT:
        alert_status = "FORCED_SEND"
    else:
        alert_status = "ALERT" if _exceeds_drop_threshold(drop, rule.y_percent) else "not triggered"
    print(f"{rule.symbol}: {drop:.2f}% in {rule.x_days} days (threshold: {rule.y_percent}%) - {alert_status}")

    history_series = close_series.iloc[-rule.x_days:]
    start_date = history_series.index[0].strftime("%m-%d")
    end_date = history_series.index[-1].strftime("%m-%d")
    history_text = format_history(history_series, isTW=rule.symbol.endswith(".TW"))

    return build_bubble(rule.symbol, start_date, end_date, rule.x_days,
                        drop, rule.y_percent, history_text, is_final_report=is_final_report)


def format_history(close_series, isTW: bool) -> str:
    lines = []
    for idx, price in zip(close_series.index, close_series.values):
        date_format = idx if isTW else idx.strftime('%m-%d')
        lines.append(f"{date_format}: {float(price):.2f}")
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

    try:
        send_line(build_carousel(bubbles))
    finally:
        # Sinopac API 登出
        logout_api()


if __name__ == "__main__":
    main()
