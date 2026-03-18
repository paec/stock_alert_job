import datetime
import json
import os
from dataclasses import dataclass
from typing import Any
import requests
import yfinance as yf
from shioaji_utils import get_tw_close_prices, format_tw_close_series, logout_api
from check_stock_utils import (
    _env_to_bool,
    calculate_price_change_pct,
    exceeds_drop_threshold,
    exceeds_long_term_drop_threshold,
    format_history as format_history_utils,
    get_market_timezone,
    get_session_hours,
    is_today_final_report_time,
    parse_positive_float,
    parse_positive_int,
    print_close_series_with_index,
)

from flex_msg_tpl import build_bubble, build_carousel

API_URL = os.getenv("CONFIG_API_URL", "https://your-pythonanywhere-domain/api/config")
LINE_TOKEN = os.getenv("LINE_TOKEN", "")
LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
DEFAULT_LOOKBACK_PADDING_DAYS = 5
DEFAULT_LONG_TERM_LOOKBACK_DAYS = 60
DEFAULT_LONG_TERM_DROP_PERCENT = 10.0

LONG_TERM_LOOKBACK_DAYS = DEFAULT_LONG_TERM_LOOKBACK_DAYS
LONG_TERM_DROP_PERCENT = DEFAULT_LONG_TERM_DROP_PERCENT





FORCE_SEND_REPORT = _env_to_bool("FORCE_SEND_REPORT", False)


@dataclass(frozen=True)
class Rule:
    symbol: str
    x_days: int
    y_percent: float


@dataclass(frozen=True)
class TriggerContext:
    short_drop: float
    long_drop: float
    primary_triggered: bool
    long_term_triggered: bool
    is_final_report: bool


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


def _load_long_term_config(config: dict[str, Any]) -> None:
    global LONG_TERM_LOOKBACK_DAYS, LONG_TERM_DROP_PERCENT

    long_term_cfg = config.get("long_term_drop")
    if not isinstance(long_term_cfg, dict):
        long_term_cfg = {}

    lookback_raw = long_term_cfg.get(
        "days",
        config.get("long_term_days", config.get("long_term_lookback_days")),
    )
    threshold_raw = long_term_cfg.get(
        "drop_percent",
        config.get("long_term_drop_percent", config.get("long_term_percent")),
    )

    LONG_TERM_LOOKBACK_DAYS = parse_positive_int(
        lookback_raw,
        DEFAULT_LONG_TERM_LOOKBACK_DAYS,
    )
    LONG_TERM_DROP_PERCENT = parse_positive_float(
        threshold_raw,
        DEFAULT_LONG_TERM_DROP_PERCENT,
    )


def fetch_rules(api_url: str = API_URL) -> list[Rule]:
    default_rules = [Rule("0050.TW", 5, 5.0), Rule("VOO", 5, 5.0), Rule("VT", 5, 5.0)]

    try:
        config = requests.get(api_url, timeout=20).json()
        _load_long_term_config(config)
        raw_rules = config.get("rules", [])
    except Exception as exc:
        _load_long_term_config({})
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
    tz, market_name = get_market_timezone(symbol)
    session_start, session_end = get_session_hours(market_name)
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

    if last_bar_time.tzinfo is None:
        last_bar_time = tz.localize(last_bar_time)
    else:
        last_bar_time = last_bar_time.astimezone(tz)

    if last_bar_time.date() != now.date():
        print(
            f"{symbol}: 最近一筆日線資料日期為 {last_bar_time.date()} "
            f"（今日 {now.date()}），視為尚未開盤或休市，跳過"
        )
        return False

    return True


def download_close_prices(symbol: str, x_days: int):
    required_days = max(x_days, LONG_TERM_LOOKBACK_DAYS) + DEFAULT_LOOKBACK_PADDING_DAYS

    # 由於永豐的API無法一次取得14天以上的資料，因此暫時改用yfinance下載所有股票的資料
    # if symbol.endswith(".TW"):
    #     close_df = get_tw_close_prices(symbol, required_days)
    #     close_series = format_tw_close_series(close_df)
    # else:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{required_days}d", interval="1d", auto_adjust=False)
    close_series = df["Close"].squeeze()

    print_close_series_with_index(symbol, close_series)
    return close_series


def _has_enough_close_data(close_series, rule: Rule) -> bool:
    required_days = max(rule.x_days, LONG_TERM_LOOKBACK_DAYS)
    if len(close_series) < required_days:
        print(
            f"{rule.symbol}: not enough data for lookback {required_days} days "
            f"(current: {len(close_series)})"
        )
        return False
    return True


def _build_trigger_context(
    rule: Rule,
    close_series,
    market_name: str,
    now: datetime.datetime,
) -> TriggerContext:
    short_drop = calculate_price_change_pct(close_series, rule.x_days) # 短期下跌幅度，各個股票有不同設定
    long_drop = calculate_price_change_pct(close_series, LONG_TERM_LOOKBACK_DAYS) # 長期下跌幅度，所有股票共用同一設定
    primary_triggered = exceeds_drop_threshold(short_drop, rule.y_percent)
    long_term_triggered = exceeds_long_term_drop_threshold(long_drop, LONG_TERM_DROP_PERCENT)
    is_final_report = is_today_final_report_time(market_name, now)

    return TriggerContext(
        short_drop=short_drop,
        long_drop=long_drop,
        primary_triggered=primary_triggered,
        long_term_triggered=long_term_triggered,
        is_final_report=is_final_report,
    )


def _should_send_report(trigger_ctx: TriggerContext) -> bool:
    return (
        FORCE_SEND_REPORT
        or trigger_ctx.primary_triggered
        or trigger_ctx.long_term_triggered
        or trigger_ctx.is_final_report
    )


def _resolve_alert_status(trigger_ctx: TriggerContext) -> str:
    if FORCE_SEND_REPORT:
        return "FORCED_SEND"
    if trigger_ctx.primary_triggered and trigger_ctx.long_term_triggered:
        return "ALERT(short+long)"
    if trigger_ctx.primary_triggered:
        return "ALERT(short)"
    if trigger_ctx.long_term_triggered:
        return "ALERT(long)"
    return "FINAL_REPORT"


def _log_non_triggered(rule: Rule, trigger_ctx: TriggerContext) -> None:
    print(
        f"{rule.symbol}: short {trigger_ctx.short_drop:.2f}% ({rule.x_days}d) / "
        f"long {trigger_ctx.long_drop:.2f}% ({LONG_TERM_LOOKBACK_DAYS}d) "
        f"皆未觸發且非最終報表時間，不送出 LINE 訊息"
    )


def _log_triggered(rule: Rule, trigger_ctx: TriggerContext, alert_status: str) -> None:
    print(
        f"{rule.symbol}: short {trigger_ctx.short_drop:.2f}%/{rule.x_days}d "
        f"(threshold: {rule.y_percent}%), "
        f"long {trigger_ctx.long_drop:.2f}%/{LONG_TERM_LOOKBACK_DAYS}d "
        f"(threshold: {LONG_TERM_DROP_PERCENT}%) - {alert_status}"
    )


def _build_history_section(rule: Rule, close_series) -> tuple[str, str, str]:
    history_series = close_series.iloc[-rule.x_days:]
    start_date = history_series.index[0].strftime("%m-%d")
    end_date = history_series.index[-1].strftime("%m-%d")
    history_text = format_history_utils(history_series)
    return start_date, end_date, history_text


def _get_close_point_days_ago(close_series, days: int) -> tuple[str | None, float | None]:
    if len(close_series) < days:
        return None, None

    point_time = close_series.index[-days]
    point_price = float(close_series.iloc[-days].item())
    point_date = point_time.strftime("%Y-%m-%d") if hasattr(point_time, "strftime") else str(point_time)
    return point_date, point_price


def build_stock_bubble(rule: Rule) -> dict[str, Any] | None:
    tz, market_name = get_market_timezone(rule.symbol)
    now = datetime.datetime.now(tz)

    if not FORCE_SEND_REPORT and not is_market_open(rule.symbol, now):
        return None

    close_series = download_close_prices(rule.symbol, rule.x_days)
   
    if not FORCE_SEND_REPORT and not has_today_data(close_series, tz, rule.symbol):
        return None

    if not _has_enough_close_data(close_series, rule):
        return None

    trigger_ctx = _build_trigger_context(rule, close_series, market_name, now)
    if not _should_send_report(trigger_ctx):
        _log_non_triggered(rule, trigger_ctx)
        return None

    alert_status = _resolve_alert_status(trigger_ctx)
    _log_triggered(rule, trigger_ctx, alert_status)

    start_date, end_date, history_text = _build_history_section(rule, close_series)
    short_lookback_days = rule.x_days
    long_lookback_days = LONG_TERM_LOOKBACK_DAYS
    short_lookback_date, close_short_lookback_ago = _get_close_point_days_ago(close_series, short_lookback_days)
    long_lookback_date, close_long_lookback_ago = _get_close_point_days_ago(close_series, long_lookback_days)
    return build_bubble(
        rule.symbol,
        start_date,
        end_date,
        rule.x_days,
        trigger_ctx.short_drop,
        rule.y_percent,
        history_text,
        is_final_report=trigger_ctx.is_final_report,
        short_lookback_days=short_lookback_days,
        long_lookback_days=long_lookback_days,
        short_lookback_change_pct=trigger_ctx.short_drop,
        long_lookback_change_pct=trigger_ctx.long_drop,
        short_lookback_date=short_lookback_date,
        long_lookback_date=long_lookback_date,
        close_short_lookback_ago=close_short_lookback_ago,
        close_long_lookback_ago=close_long_lookback_ago,
        long_term_drop_percent=LONG_TERM_DROP_PERCENT,
    )


def main() -> None:
    rules = fetch_rules()

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
        logout_api()


if __name__ == "__main__":
    main()
