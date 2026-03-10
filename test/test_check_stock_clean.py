import datetime as dt
import unittest
from unittest.mock import patch

import pandas as pd
import pytz

import check_stock_clean as stock_job


class FixedDateTime(dt.datetime):
    frozen_now = None

    @classmethod
    def now(cls, tz=None):
        if cls.frozen_now is None:
            raise AssertionError("frozen_now must be set before calling now()")
        if tz is None:
            return cls.frozen_now
        return cls.frozen_now.astimezone(tz)


def make_close_series(values, start="2026-03-03", tz="America/New_York"):
    index = pd.date_range(start=start, periods=len(values), freq="D", tz=tz)
    return pd.Series(values, index=index)


def make_intraday_frame(timestamps):
    return pd.DataFrame({"Close": list(range(len(timestamps)))}, index=pd.DatetimeIndex(timestamps))


class ParseRuleTests(unittest.TestCase):
    def test_parse_rule_returns_normalized_rule(self):
        rule = stock_job.parse_rule({"symbol": " voo ", "x_days": "5", "y_percent": "3.5"})

        self.assertEqual(rule, stock_job.Rule(symbol="VOO", x_days=5, y_percent=3.5))

    def test_parse_rule_rejects_invalid_payload(self):
        self.assertIsNone(stock_job.parse_rule({"symbol": "", "x_days": 5, "y_percent": 3}))
        self.assertIsNone(stock_job.parse_rule({"symbol": "VOO", "x_days": 0, "y_percent": 3}))
        self.assertIsNone(stock_job.parse_rule({"symbol": "VOO", "y_percent": 3}))


class FetchRulesTests(unittest.TestCase):
    @patch("check_stock_clean.requests.get")
    def test_fetch_rules_returns_valid_rules_from_api(self, mock_get):
        mock_get.return_value.json.return_value = {
            "rules": [
                {"symbol": "voo", "x_days": 5, "y_percent": 3},
                {"symbol": "", "x_days": 5, "y_percent": 3},
                {"symbol": "vt", "x_days": 10, "y_percent": 7.5},
            ]
        }

        rules = stock_job.fetch_rules("https://example.test/config")

        self.assertEqual(
            rules,
            [
                stock_job.Rule("VOO", 5, 3.0),
                stock_job.Rule("VT", 10, 7.5),
            ],
        )
        mock_get.assert_called_once_with("https://example.test/config", timeout=20)

    @patch("check_stock_clean.requests.get")
    def test_fetch_rules_falls_back_to_default_rules_on_error(self, mock_get):
        mock_get.side_effect = RuntimeError("boom")

        rules = stock_job.fetch_rules("https://example.test/config")

        self.assertEqual(
            rules,
            [
                stock_job.Rule("0050.TW", 5, 5.0),
                stock_job.Rule("VOO", 5, 5.0),
                stock_job.Rule("VT", 5, 5.0),
            ],
        )

    @patch("check_stock_clean.requests.get")
    def test_fetch_rules_falls_back_when_api_returns_no_valid_rules(self, mock_get):
        mock_get.return_value.json.return_value = {
            "rules": [
                {"symbol": "", "x_days": 5, "y_percent": 3},
                {"symbol": "VOO", "x_days": 0, "y_percent": 3},
            ]
        }

        rules = stock_job.fetch_rules()

        self.assertEqual(len(rules), 3)
        self.assertEqual(rules[0], stock_job.Rule("0050.TW", 5, 5.0))


class SendLineTests(unittest.TestCase):
    @patch("check_stock_clean.requests.post")
    def test_send_line_skips_when_token_is_missing(self, mock_post):
        stock_job.send_line({"type": "carousel", "contents": []}, token="")

        mock_post.assert_not_called()

    @patch("check_stock_clean.requests.post")
    def test_send_line_posts_expected_payload(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "ok"
        message = {"type": "carousel", "contents": [{"type": "bubble"}]}

        stock_job.send_line(message, token="token-123")

        mock_post.assert_called_once_with(
            stock_job.LINE_BROADCAST_URL,
            headers={
                "Authorization": "Bearer token-123",
                "Content-Type": "application/json",
            },
            json={
                "messages": [
                    {
                        "type": "flex",
                        "altText": "股票漲跌報表",
                        "contents": message,
                    }
                ]
            },
            timeout=20,
        )

    @patch("builtins.print")
    @patch("check_stock_clean.requests.post")
    def test_send_line_prints_error_and_response_when_line_api_fails(self, mock_post, mock_print):
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "server error"

        stock_job.send_line({"type": "carousel", "contents": []}, token="token-123")

        mock_print.assert_any_call("LINE API error: 500 server error")
        mock_print.assert_any_call("LINE API response: 500 server error")


class IsMarketOpenTests(unittest.TestCase):
    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_returns_false_outside_trading_hours(self, mock_ticker):
        taipei = pytz.timezone("Asia/Taipei")
        now = taipei.localize(dt.datetime(2026, 3, 10, 7, 0))

        is_open = stock_job.is_market_open("0050.TW", now)

        self.assertFalse(is_open)
        mock_ticker.assert_not_called()

    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_returns_false_when_no_intraday_data(self, mock_ticker):
        taipei = pytz.timezone("Asia/Taipei")
        now = taipei.localize(dt.datetime(2026, 3, 10, 9, 0))
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        is_open = stock_job.is_market_open("0050.TW", now)

        self.assertFalse(is_open)

    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_returns_false_when_last_bar_is_stale(self, mock_ticker):
        new_york = pytz.timezone("America/New_York")
        now = new_york.localize(dt.datetime(2026, 3, 10, 10, 0))
        mock_ticker.return_value.history.return_value = make_intraday_frame(
            [dt.datetime(2026, 3, 10, 9, 55)]
        )

        is_open = stock_job.is_market_open("VOO", now)

        self.assertFalse(is_open)

    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_returns_false_after_session_end(self, mock_ticker):
        new_york = pytz.timezone("America/New_York")
        now = new_york.localize(dt.datetime(2026, 3, 10, 17, 1))

        is_open = stock_job.is_market_open("VOO", now)

        self.assertFalse(is_open)
        mock_ticker.assert_not_called()

    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_returns_true_when_recent_bar_exists(self, mock_ticker):
        new_york = pytz.timezone("America/New_York")
        now = new_york.localize(dt.datetime(2026, 3, 10, 10, 0))
        mock_ticker.return_value.history.return_value = make_intraday_frame(
            [new_york.localize(dt.datetime(2026, 3, 10, 9, 58))]
        )

        is_open = stock_job.is_market_open("VOO", now)

        self.assertTrue(is_open)

    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_accepts_session_start_with_exact_three_minute_naive_bar(self, mock_ticker):
        taipei = pytz.timezone("Asia/Taipei")
        now = taipei.localize(dt.datetime(2026, 3, 10, 8, 30))
        mock_ticker.return_value.history.return_value = make_intraday_frame(
            [dt.datetime(2026, 3, 10, 8, 27)]
        )

        is_open = stock_job.is_market_open("0050.TW", now)

        self.assertTrue(is_open)

    @patch("check_stock_clean.yf.Ticker")
    def test_is_market_open_accepts_session_end_with_cross_timezone_recent_bar(self, mock_ticker):
        new_york = pytz.timezone("America/New_York")
        utc = pytz.UTC
        now = new_york.localize(dt.datetime(2026, 3, 10, 17, 0))
        mock_ticker.return_value.history.return_value = make_intraday_frame(
            [utc.localize(dt.datetime(2026, 3, 10, 20, 58))]
        )

        is_open = stock_job.is_market_open("VOO", now)

        self.assertTrue(is_open)


class DownloadClosePricesTests(unittest.TestCase):
    @patch("check_stock_clean.yf.download")
    def test_download_close_prices_returns_close_series(self, mock_download):
        expected_series = make_close_series([100.0, 101.5])
        mock_download.return_value = pd.DataFrame({"Close": expected_series})

        close_series = stock_job.download_close_prices("VOO", 5)

        self.assertTrue(close_series.equals(expected_series))
        mock_download.assert_called_once_with(
            "VOO",
            period="10d",
            progress=False,
            auto_adjust=False,
        )


class BuildStockBubbleTests(unittest.TestCase):
    def setUp(self):
        self.rule = stock_job.Rule("VOO", 3, 5.0)
        self.now = pytz.timezone("America/New_York").localize(dt.datetime(2026, 3, 10, 10, 15))

    @patch("check_stock_clean.datetime.datetime", FixedDateTime)
    @patch("check_stock_clean.is_market_open", return_value=False)
    def test_build_stock_bubble_returns_none_when_market_is_closed(self, mock_is_market_open):
        FixedDateTime.frozen_now = self.now

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)
        mock_is_market_open.assert_called_once()

    @patch("check_stock_clean.datetime.datetime", FixedDateTime)
    @patch("check_stock_clean.download_close_prices")
    @patch("check_stock_clean.is_market_open", return_value=True)
    def test_build_stock_bubble_returns_none_when_price_history_is_too_short(
        self,
        mock_is_market_open,
        mock_download_close_prices,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 95.0, 94.0])

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)

    @patch("check_stock_clean.datetime.datetime", FixedDateTime)
    @patch("check_stock_clean.build_bubble")
    @patch("check_stock_clean.download_close_prices")
    @patch("check_stock_clean.is_market_open", return_value=True)
    def test_build_stock_bubble_returns_none_when_not_threshold_and_not_full_hour(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 99.0, 98.0, 97.0])

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)
        mock_build_bubble.assert_not_called()

    @patch("check_stock_clean.datetime.datetime", FixedDateTime)
    @patch("check_stock_clean.build_bubble", return_value={"type": "bubble"})
    @patch("check_stock_clean.download_close_prices")
    @patch("check_stock_clean.is_market_open", return_value=True)
    def test_build_stock_bubble_builds_bubble_when_drop_hits_threshold(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 90.0, 88.0, 85.0])

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertEqual(bubble, {"type": "bubble"})
        mock_build_bubble.assert_called_once_with(
            "VOO",
            "03-04",
            "03-06",
            3,
            -5.555555555555555,
            5.0,
            "03-04: 90.00\n03-05: 88.00\n03-06: 85.00",
        )

    @patch("check_stock_clean.datetime.datetime", FixedDateTime)
    @patch("check_stock_clean.build_bubble", return_value={"type": "bubble"})
    @patch("check_stock_clean.download_close_prices")
    @patch("check_stock_clean.is_market_open", return_value=True)
    def test_build_stock_bubble_builds_bubble_on_full_hour_even_without_alert(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now.replace(minute=0)
        mock_download_close_prices.return_value = make_close_series([100.0, 102.0, 101.0, 103.0])

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertEqual(bubble, {"type": "bubble"})
        self.assertEqual(mock_build_bubble.call_args.args[3], 3)
        self.assertGreater(mock_build_bubble.call_args.args[4], 0)

    @patch("check_stock_clean.datetime.datetime", FixedDateTime)
    @patch("check_stock_clean.is_market_open", return_value=False)
    def test_build_stock_bubble_uses_taipei_time_for_tw_symbols(self, mock_is_market_open):
        FixedDateTime.frozen_now = pytz.UTC.localize(dt.datetime(2026, 3, 10, 1, 0))

        bubble = stock_job.build_stock_bubble(stock_job.Rule("0050.TW", 3, 5.0))

        self.assertIsNone(bubble)
        market_now = mock_is_market_open.call_args.args[1]
        self.assertEqual(str(market_now.tzinfo), "Asia/Taipei")
        self.assertEqual(market_now.hour, 9)


class FormatHistoryTests(unittest.TestCase):
    def test_format_history_returns_date_price_lines(self):
        close_series = make_close_series([100.0, 101.25], tz="Asia/Taipei")

        history = stock_job.format_history(close_series)

        self.assertEqual(history, "03-03: 100.00\n03-04: 101.25")


class MainTests(unittest.TestCase):
    @patch("check_stock_clean.send_line")
    @patch("check_stock_clean.build_carousel", return_value={"type": "carousel"})
    @patch("check_stock_clean.build_stock_bubble")
    @patch("check_stock_clean.fetch_rules")
    def test_main_sends_carousel_when_bubbles_exist(
        self,
        mock_fetch_rules,
        mock_build_stock_bubble,
        mock_build_carousel,
        mock_send_line,
    ):
        mock_fetch_rules.return_value = [stock_job.Rule("VOO", 5, 5.0), stock_job.Rule("VT", 5, 5.0)]
        mock_build_stock_bubble.side_effect = [{"type": "bubble", "hero": "one"}, None]

        stock_job.main()

        mock_build_carousel.assert_called_once_with([{"type": "bubble", "hero": "one"}])
        mock_send_line.assert_called_once_with({"type": "carousel"})

    @patch("check_stock_clean.send_line")
    @patch("check_stock_clean.build_stock_bubble", return_value=None)
    @patch("check_stock_clean.fetch_rules", return_value=[stock_job.Rule("VOO", 5, 5.0)])
    def test_main_skips_line_send_when_no_bubbles(self, mock_fetch_rules, mock_build_stock_bubble, mock_send_line):
        stock_job.main()

        mock_send_line.assert_not_called()


if __name__ == "__main__":
    unittest.main()