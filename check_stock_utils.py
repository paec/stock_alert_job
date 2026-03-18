import os

import pandas as pd
pd.set_option("display.max_rows", 1000) # 增加這行以顯示更多行數的 DataFrame
import datetime
from typing import Any
import pytz


def _format_date_only(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text = str(value)
    return text.split(" ")[0] if " " in text else text

def print_close_series_with_index(symbol: str, close_series) -> None:
    if isinstance(close_series, pd.Series):
        if close_series.empty:
            print(f"{symbol} close_series (index): <empty>")
            return

        indexed_rows = [
            f"{idx}. {_format_date_only(date)} {price}"
            for idx, (date, price) in enumerate(close_series.items(), start=1)
        ]
        print(f"{symbol} close_series (index):\n" + "\n".join(indexed_rows))
        return

    print(f"{symbol} close_series (index):\n1. {close_series}")

def parse_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def parse_positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def get_session_hours(market_name: str) -> tuple[datetime.time, datetime.time]:
    if market_name == "台股":
        return datetime.time(8, 0), datetime.time(15, 0)
    return datetime.time(8, 0), datetime.time(17, 0)


def get_market_timezone(symbol: str) -> tuple[pytz.BaseTzInfo, str]:
    if symbol.endswith(".TW"):
        return pytz.timezone("Asia/Taipei"), "台股"
    return pytz.timezone("America/New_York"), "美股"


def is_today_final_report_time(market_name: str, now: datetime.datetime) -> bool:
    if market_name == "台股":
        return now.hour == 14 and now.minute == 5
    return now.hour == 16 and now.minute == 45


def calculate_price_change_pct(close_series, x_days: int) -> float:
    today = float(close_series.iloc[-1].item())
    past = float(close_series.iloc[-x_days].item())
    today_date = close_series.index[-1]
    past_date = close_series.index[-x_days]

    today_label = today_date.strftime("%Y-%m-%d") if hasattr(today_date, "strftime") else str(today_date)
    past_label = past_date.strftime("%Y-%m-%d") if hasattr(past_date, "strftime") else str(past_date)
    print(f"Today: {today} ({today_label}), {x_days} days ago: {past} ({past_label})")
    
    return (today - past) / past * 100


def exceeds_drop_threshold(drop: float, y_percent: float) -> bool:
    return drop < 0 and abs(drop) >= y_percent


def exceeds_long_term_drop_threshold(drop: float, drop_percent: float) -> bool:
    return drop < 0 and abs(drop) >= drop_percent


def format_history(close_series) -> str:
    lines = []
    for idx, price in zip(close_series.index, close_series.values):
        lines.append(f"{idx.strftime('%m-%d')}: {float(price):.2f}")
    return "\n".join(lines)

def _env_to_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}