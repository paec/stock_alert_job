"""Send a fake threshold-alarm Flex message to one LINE user.

Requires LINE_TOKEN and LINE_USER_ID; use DRY_RUN=true to print without sending.
"""

import datetime as dt
import json
import os
from typing import Any

import requests

import flex_msg_tpl
from flex_msg_tpl import build_bubble, build_carousel

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
DEFAULT_SYMBOL = "TEST"
DEFAULT_SHORT_DROP_PERCENT = 8.0
DEFAULT_SHORT_THRESHOLD_PERCENT = 5.0
DEFAULT_LONG_DROP_PERCENT = 15.0
DEFAULT_LONG_THRESHOLD_PERCENT = 10.0


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _get_symbol() -> str:
    symbol = os.getenv("MANUAL_TEST_SYMBOL", DEFAULT_SYMBOL).strip().upper()
    if not symbol:
        raise ValueError("MANUAL_TEST_SYMBOL must not be empty")
    return symbol


def build_manual_message(
    symbol: str,
    short_drop_percent: float = DEFAULT_SHORT_DROP_PERCENT,
    short_threshold_percent: float = DEFAULT_SHORT_THRESHOLD_PERCENT,
    long_drop_percent: float = DEFAULT_LONG_DROP_PERCENT,
    long_threshold_percent: float = DEFAULT_LONG_THRESHOLD_PERCENT,
) -> dict[str, Any]:
    short_drop = -abs(short_drop_percent)
    long_drop = -abs(long_drop_percent)

    if short_drop > -short_threshold_percent:
        raise ValueError("short drop must reach the short threshold")
    if long_drop > -long_threshold_percent:
        raise ValueError("long drop must reach the long threshold")

    today = dt.date.today()
    history_dates = [today - dt.timedelta(days=offset) for offset in range(4, -1, -1)]
    history_prices = [100.0, 99.0, 97.0, 94.0, 92.0]
    history_text = "\n".join(
        f"{date_value.strftime('%m-%d')}: {price:.2f}"
        for date_value, price in zip(history_dates, history_prices)
    )

    bubble = build_bubble(
        symbol=symbol,
        start_date=history_dates[0].strftime("%m-%d"),
        end_date=history_dates[-1].strftime("%m-%d"),
        x_days=5,
        drop=short_drop,
        y_percent=short_threshold_percent,
        history_text=history_text,
        is_final_report=False,
        short_lookback_days=5,
        long_lookback_days=60,
        short_lookback_change_pct=short_drop,
        long_lookback_change_pct=long_drop,
        short_lookback_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
        long_lookback_date=(today - dt.timedelta(days=60)).strftime("%Y-%m-%d"),
        close_short_lookback_ago=100.0,
        close_long_lookback_ago=108.0,
        long_term_drop_percent=long_threshold_percent,
        show_add_more_button=True,
    )
    return build_carousel([bubble])


def send_manual_message(message: dict[str, Any], token: str, user_id: str) -> None:
    payload = build_push_payload(message, user_id)
    response = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"LINE API error: {response.status_code} {response.text}")

    print(f"LINE push succeeded: {response.status_code}")


def build_push_payload(message: dict[str, Any], user_id: str) -> dict[str, Any]:
    return {
        "to": user_id,
        "messages": [
            {
                "type": "flex",
                "altText": "股票漲跌報表（手動測試）",
                "contents": message,
            }
        ],
    }


def main() -> None:
    dry_run = os.getenv("DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}
    token = os.getenv("LINE_TOKEN", "").strip()  or 'xxx'
    user_id = os.getenv("LINE_USER_ID", "").strip() or '0989216438'
    if not dry_run and not token:
        raise SystemExit("LINE_TOKEN is required")
    if not dry_run and not user_id:
        raise SystemExit("LINE_USER_ID is required")

    try:
        message = build_manual_message(
            symbol=_get_symbol(),
            short_drop_percent=_get_float_env(
                "MANUAL_TEST_SHORT_DROP_PERCENT",
                DEFAULT_SHORT_DROP_PERCENT,
            ),
            short_threshold_percent=_get_float_env(
                "MANUAL_TEST_SHORT_THRESHOLD_PERCENT",
                DEFAULT_SHORT_THRESHOLD_PERCENT,
            ),
            long_drop_percent=_get_float_env(
                "MANUAL_TEST_LONG_DROP_PERCENT",
                DEFAULT_LONG_DROP_PERCENT,
            ),
            long_threshold_percent=_get_float_env(
                "MANUAL_TEST_LONG_THRESHOLD_PERCENT",
                DEFAULT_LONG_THRESHOLD_PERCENT,
            ),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if flex_msg_tpl.ADD_MORE_API_URL.startswith("https://example.invalid/"):
        print("Warning: ADD_MORE_API_URL is still using the placeholder URL.")

    if dry_run:
        print(json.dumps(build_push_payload(message, user_id or "dry-run-user"), ensure_ascii=True, indent=2))
        print("DRY_RUN=true: LINE push skipped")
        return

    print("Sending a fake threshold-alarm Flex message...")
    send_manual_message(message, token, user_id)


if __name__ == "__main__":
    main()
