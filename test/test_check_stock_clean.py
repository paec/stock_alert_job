import datetime as dt
import unittest
from unittest.mock import patch

import pandas as pd
import pytz

import check_stock as stock_job


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


class ParseRuleTests(unittest.TestCase):
    def test_parse_rule_returns_normalized_rule(self):
        rule = stock_job.parse_rule({"symbol": " voo ", "x_days": "5", "y_percent": "3.5"})

        self.assertEqual(rule, stock_job.Rule(symbol="VOO", x_days=5, y_percent=3.5))

    def test_parse_rule_rejects_invalid_payload(self):
        self.assertIsNone(stock_job.parse_rule({"symbol": "", "x_days": 5, "y_percent": 3}))
        self.assertIsNone(stock_job.parse_rule({"symbol": "VOO", "x_days": 0, "y_percent": 3}))
        self.assertIsNone(stock_job.parse_rule({"symbol": "VOO", "y_percent": 3}))


class FetchRulesTests(unittest.TestCase):
    @patch("check_stock.requests.get")
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

    @patch("check_stock.requests.get")
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

    @patch("check_stock.requests.get")
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
    @patch("check_stock.requests.post")
    def test_send_line_skips_when_token_is_missing(self, mock_post):
        stock_job.send_line({"type": "carousel", "contents": []}, token="")

        mock_post.assert_not_called()

    @patch("check_stock.requests.post")
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

    @patch("builtins.print") #mock_print會攔截print函數的調用，讓我們能夠檢查print是否被正確調用以及輸出的內容。
    @patch("check_stock.requests.post")
    def test_send_line_prints_error_and_response_when_line_api_fails(self, mock_post, mock_print):
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "server error"

        stock_job.send_line({"type": "carousel", "contents": []}, token="token-123")

        mock_print.assert_any_call("LINE API error: 500 server error")
        mock_print.assert_any_call("LINE API response: 500 server error")


class IsMarketOpenTests(unittest.TestCase):
    def test_is_market_open_returns_false_outside_trading_hours(self):
        taipei = pytz.timezone("Asia/Taipei")
        now = taipei.localize(dt.datetime(2026, 3, 10, 7, 0))

        is_open = stock_job.is_market_open("0050.TW", now)

        self.assertFalse(is_open)

    def test_is_market_open_returns_true_during_tw_session_hours(self):
        taipei = pytz.timezone("Asia/Taipei")
        now = taipei.localize(dt.datetime(2026, 3, 10, 9, 0))

        is_open = stock_job.is_market_open("0050.TW", now)

        self.assertTrue(is_open)

    def test_is_market_open_returns_true_during_us_session_hours(self):
        new_york = pytz.timezone("America/New_York")
        now = new_york.localize(dt.datetime(2026, 3, 10, 10, 0))

        is_open = stock_job.is_market_open("VOO", now)

        self.assertTrue(is_open)

    def test_is_market_open_returns_false_after_session_end(self):
        new_york = pytz.timezone("America/New_York")
        now = new_york.localize(dt.datetime(2026, 3, 10, 17, 1))

        is_open = stock_job.is_market_open("VOO", now)

        self.assertFalse(is_open)

    def test_is_market_open_accepts_tw_session_start_boundary(self):
        taipei = pytz.timezone("Asia/Taipei")
        now = taipei.localize(dt.datetime(2026, 3, 10, 8, 0))

        is_open = stock_job.is_market_open("0050.TW", now)

        self.assertTrue(is_open)

    def test_is_market_open_accepts_us_session_end_boundary(self):
        new_york = pytz.timezone("America/New_York")
        now = new_york.localize(dt.datetime(2026, 3, 10, 17, 0))

        is_open = stock_job.is_market_open("VOO", now)

        self.assertTrue(is_open)


class HasTodayDataTests(unittest.TestCase):
    @patch("check_stock.datetime.datetime", FixedDateTime)
    def test_has_today_data_returns_false_for_empty_series(self):
        tz = pytz.timezone("America/New_York")
        FixedDateTime.frozen_now = tz.localize(dt.datetime(2026, 3, 10, 10, 15))
        close_series = pd.Series(dtype=float)

        has_data = stock_job.has_today_data(close_series, tz, "VOO")

        self.assertFalse(has_data)

    @patch("check_stock.datetime.datetime", FixedDateTime)
    def test_has_today_data_returns_false_for_stale_daily_bar(self):
        tz = pytz.timezone("America/New_York")
        FixedDateTime.frozen_now = tz.localize(dt.datetime(2026, 3, 10, 10, 15))
        close_series = make_close_series([100.0, 99.0], start="2026-03-08")

        has_data = stock_job.has_today_data(close_series, tz, "VOO")

        self.assertFalse(has_data)

    @patch("check_stock.datetime.datetime", FixedDateTime)
    def test_has_today_data_returns_true_for_today_daily_bar(self):
        tz = pytz.timezone("America/New_York")
        FixedDateTime.frozen_now = tz.localize(dt.datetime(2026, 3, 10, 10, 15))
        close_series = make_close_series([100.0, 99.0, 98.0], start="2026-03-08")

        has_data = stock_job.has_today_data(close_series, tz, "VOO")

        self.assertTrue(has_data)

    @patch("check_stock.datetime.datetime", FixedDateTime)
    def test_has_today_data_handles_naive_timestamp_index_for_tw_data(self):
        tz = pytz.timezone("Asia/Taipei")
        FixedDateTime.frozen_now = tz.localize(dt.datetime(2026, 3, 10, 9, 30))
        close_series = pd.Series(
            [100.0, 101.0],
            index=pd.to_datetime(["2026-03-09", "2026-03-10"]),
        )

        has_data = stock_job.has_today_data(close_series, tz, "0050.TW")

        self.assertTrue(has_data)


class DownloadClosePricesTests(unittest.TestCase):
    @patch("check_stock.yf.Ticker")
    def test_download_close_prices_returns_close_series_for_us_symbols(self, mock_ticker_cls):
        history_df = pd.DataFrame(
            {"Close": [100.0, 101.5]},
            index=pd.DatetimeIndex(
                ["2026-03-09 00:00:00-04:00", "2026-03-10 00:00:00-04:00"],
                name="Date",
            ),
        )
        expected_series = history_df["Close"].squeeze()
        mock_ticker = mock_ticker_cls.return_value
        mock_ticker.history.return_value = history_df

        close_series = stock_job.download_close_prices("VOO", 5)

        self.assertTrue(close_series.equals(expected_series))
        mock_ticker_cls.assert_called_once_with("VOO")
        mock_ticker.history.assert_called_once_with(period="10d", interval="1d")

    @patch("check_stock.format_tw_close_series")
    @patch("check_stock.get_tw_close_prices")
    def test_download_close_prices_uses_shioaji_helpers_for_tw_symbols(
        self,
        mock_get_tw_close_prices,
        mock_format_tw_close_series,
    ):
        tw_df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2026-03-09", "2026-03-10"]),
                "Close": [100.0, 101.5],
                "ts": pd.to_datetime(["2026-03-09 13:30", "2026-03-10 13:30"]),
            }
        )
        expected_series = pd.Series(
            [100.0, 101.5],
            index=pd.to_datetime(["2026-03-09", "2026-03-10"]),
        )
        mock_get_tw_close_prices.return_value = tw_df
        mock_format_tw_close_series.return_value = expected_series

        close_series = stock_job.download_close_prices("0050.TW", 5)

        self.assertTrue(close_series.equals(expected_series))
        mock_get_tw_close_prices.assert_called_once_with(
            "0050.TW",
            10,
        )
        mock_format_tw_close_series.assert_called_once_with(tw_df)


class GetSessionHoursTests(unittest.TestCase):
    def test_tw_returns_correct_hours(self):
        start, end = stock_job._get_session_hours("台股")
        self.assertEqual(start, dt.time(8, 0))
        self.assertEqual(end, dt.time(15, 0))

    def test_us_returns_correct_hours(self):
        start, end = stock_job._get_session_hours("美股")
        self.assertEqual(start, dt.time(8, 0))
        self.assertEqual(end, dt.time(17, 0))


class GetMarketTimezoneTests(unittest.TestCase):
    def test_get_market_timezone_returns_taipei_for_tw_symbols(self):
        tz, market_name = stock_job.get_market_timezone("0050.TW")

        self.assertEqual(str(tz), "Asia/Taipei")
        self.assertEqual(market_name, "台股")

    def test_get_market_timezone_returns_new_york_for_non_tw_symbols(self):
        tz, market_name = stock_job.get_market_timezone("VOO")

        self.assertEqual(str(tz), "America/New_York")
        self.assertEqual(market_name, "美股")


class IsTodayFinalReportTimeTests(unittest.TestCase):
    def test_tw_market_returns_true_only_at_14_05(self):
        self.assertTrue(stock_job.is_today_final_report_time("台股", dt.datetime(2026, 3, 10, 14, 5)))
        self.assertFalse(stock_job.is_today_final_report_time("台股", dt.datetime(2026, 3, 10, 14, 4)))

    def test_us_market_returns_true_only_at_16_45(self):
        self.assertTrue(stock_job.is_today_final_report_time("美股", dt.datetime(2026, 3, 10, 16, 45)))
        self.assertFalse(stock_job.is_today_final_report_time("美股", dt.datetime(2026, 3, 10, 16, 44)))


class CalculatePriceChangePctTests(unittest.TestCase):

    def test_price_up(self):
        series = make_close_series([100, 110, 120, 130])
        pct = stock_job.calculate_price_change_pct(series, 3)
        self.assertAlmostEqual(pct, 18.181818181818183)

    def test_price_down(self):
        series = make_close_series([100, 90, 80, 70])
        pct = stock_job.calculate_price_change_pct(series, 3)
        self.assertAlmostEqual(pct, -22.22222222222222)

    def test_price_flat(self):
        series = make_close_series([100, 100, 100, 100])
        pct = stock_job.calculate_price_change_pct(series, 3)
        self.assertAlmostEqual(pct, 0.0)


class ExceedsDropThresholdTests(unittest.TestCase):
    def test_exceeds_threshold(self):
        self.assertTrue(stock_job._exceeds_drop_threshold(-6.0, 5.0))

    def test_not_exceeds_threshold(self):
        self.assertFalse(stock_job._exceeds_drop_threshold(-4.0, 5.0))

    def test_positive_drop(self):
        self.assertFalse(stock_job._exceeds_drop_threshold(6.0, 5.0))

    def test_exact_threshold(self):
        self.assertTrue(stock_job._exceeds_drop_threshold(-5.0, 5.0))


class BuildStockBubbleTests(unittest.TestCase):

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.build_bubble", return_value={"type": "bubble", "market": "tw"})
    @patch("check_stock.has_today_data", return_value=True)
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=True)
    def test_build_stock_bubble_tw_integration(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_has_today_data,
        mock_build_bubble,
    ):
        # 台股，跌幅超過門檻
        rule = stock_job.Rule("0050.TW", 3, 5.0)
        # 固定 now 在台北時區
        tz = pytz.timezone("Asia/Taipei")
        FixedDateTime.frozen_now = tz.localize(dt.datetime(2026, 3, 10, 10, 30))
        # 近 4 天收盤價，跌幅 -10%
        close_series = pd.Series(
            [100.0, 98.0, 95.0, 90.0],
            index=pd.date_range(start="2026-03-07", periods=4, freq="D", tz=tz),
        )
        mock_download_close_prices.return_value = close_series

        bubble = stock_job.build_stock_bubble(rule)

        self.assertEqual(bubble, {"type": "bubble", "market": "tw"})
        mock_is_market_open.assert_called_once_with("0050.TW", FixedDateTime.frozen_now)
        mock_download_close_prices.assert_called_once_with("0050.TW", 3)
        mock_has_today_data.assert_called_once_with(close_series, tz, "0050.TW")
        # 應該有觸發 build_bubble，且 drop < 0 且 abs(drop) > y_percent
        args, kwargs = mock_build_bubble.call_args
        self.assertEqual(args[0], "0050.TW")
        self.assertEqual(args[3], 3)

        self.assertLess(args[4], 0)
        self.assertGreaterEqual(abs(args[4]), 5.0)

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.build_bubble", return_value={"type": "bubble", "market": "tw-final"})
    @patch("check_stock.has_today_data", return_value=True)
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=True)
    def test_build_stock_bubble_tw_builds_bubble_on_final_report_time_without_alert(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_has_today_data,
        mock_build_bubble,
    ):
        rule = stock_job.Rule("0050.TW", 3, 5.0)
        tz = pytz.timezone("Asia/Taipei")
        FixedDateTime.frozen_now = tz.localize(dt.datetime(2026, 3, 10, 14, 5))
        # 漲幅為正，未達下跌門檻；但因為是最終報表時間仍應產生 bubble
        close_series = pd.Series(
            [100.0, 101.0, 102.0, 103.0],
            index=pd.date_range(start="2026-03-07", periods=4, freq="D", tz=tz),
        )
        mock_download_close_prices.return_value = close_series

        bubble = stock_job.build_stock_bubble(rule)

        self.assertEqual(bubble, {"type": "bubble", "market": "tw-final"})
        self.assertTrue(mock_build_bubble.call_args.kwargs["is_final_report"])
        self.assertGreater(mock_build_bubble.call_args.args[4], 0)


    def setUp(self):
        self.rule = stock_job.Rule("VOO", 3, 5.0)
        self.now = pytz.timezone("America/New_York").localize(dt.datetime(2026, 3, 10, 10, 15))

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.is_market_open", return_value=False)
    def test_build_stock_bubble_returns_none_when_market_is_closed(self, mock_is_market_open):
        FixedDateTime.frozen_now = self.now

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)
        mock_is_market_open.assert_called_once()

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.build_bubble", return_value={"type": "bubble", "forced": True})
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=False)
    def test_build_stock_bubble_force_send_bypasses_market_and_threshold_checks(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 101.0, 101.0, 101.0], start="2026-03-07")

        with patch("check_stock.FORCE_SEND_REPORT", True):
            bubble = stock_job.build_stock_bubble(self.rule)

        self.assertEqual(bubble, {"type": "bubble", "forced": True})
        mock_is_market_open.assert_not_called()
        self.assertFalse(mock_build_bubble.call_args.kwargs["is_final_report"])

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=True)
    def test_build_stock_bubble_returns_none_when_price_history_is_too_short(
        self,
        mock_is_market_open,
        mock_download_close_prices,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 95.0, 94.0], start="2026-03-08")

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.has_today_data", return_value=False)
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=True)
    def test_build_stock_bubble_returns_none_when_today_data_is_missing(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_has_today_data,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 99.0, 98.0, 97.0], start="2026-03-07")

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)
        mock_has_today_data.assert_called_once()

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.build_bubble")
    @patch("check_stock.download_close_prices")
    def test_build_stock_bubble_returns_none_when_not_threshold_and_not_final_report_time(
        self,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 99.0, 98.0, 97.0], start="2026-03-07")

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertIsNone(bubble)
        mock_build_bubble.assert_not_called()

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.build_bubble", return_value={"type": "bubble"})
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=True)
    def test_build_stock_bubble_builds_bubble_when_drop_hits_threshold(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now
        mock_download_close_prices.return_value = make_close_series([100.0, 90.0, 88.0, 85.0], start="2026-03-07")

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertEqual(bubble, {"type": "bubble"})
        mock_build_bubble.assert_called_once_with(
            "VOO",
            "03-08",
            "03-10",
            3,
            -5.555555555555555,
            5.0,
            "03-08: 90.00\n03-09: 88.00\n03-10: 85.00",
            is_final_report=False,
        )

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.build_bubble", return_value={"type": "bubble"})
    @patch("check_stock.download_close_prices")
    @patch("check_stock.is_market_open", return_value=True)
    def test_build_stock_bubble_builds_bubble_on_final_report_time_even_without_alert(
        self,
        mock_is_market_open,
        mock_download_close_prices,
        mock_build_bubble,
    ):
        FixedDateTime.frozen_now = self.now.replace(hour=16, minute=45)
        mock_download_close_prices.return_value = make_close_series([100.0, 102.0, 101.0, 103.0], start="2026-03-07")

        bubble = stock_job.build_stock_bubble(self.rule)

        self.assertEqual(bubble, {"type": "bubble"})
        self.assertEqual(mock_build_bubble.call_args.args[3], 3)
        self.assertGreater(mock_build_bubble.call_args.args[4], 0)
        self.assertTrue(mock_build_bubble.call_args.kwargs["is_final_report"])

    @patch("check_stock.datetime.datetime", FixedDateTime)
    @patch("check_stock.is_market_open", return_value=False)
    def test_build_stock_bubble_uses_taipei_time_for_tw_symbols(self, mock_is_market_open):
        FixedDateTime.frozen_now = pytz.UTC.localize(dt.datetime(2026, 3, 10, 1, 0))

        bubble = stock_job.build_stock_bubble(stock_job.Rule("0050.TW", 3, 5.0))

        self.assertIsNone(bubble)
        market_now = mock_is_market_open.call_args.args[1]
        self.assertEqual(str(market_now.tzinfo), "Asia/Taipei")
        self.assertEqual(market_now.hour, 9)


class FormatHistoryTests(unittest.TestCase):
    def test_format_history_returns_mm_dd_lines_for_us_market(self):
        close_series = make_close_series([100.0, 101.25], tz="Asia/Taipei")

        history = stock_job.format_history(close_series, isTW=False)

        self.assertEqual(history, "03-03: 100.00\n03-04: 101.25")

    def test_format_history_returns_timestamp_lines_for_tw_market(self):
        close_series = make_close_series([100.0, 101.25], tz="Asia/Taipei")

        history = stock_job.format_history(close_series, isTW=True)

        self.assertEqual(
            history,
            "2026-03-03 00:00:00+08:00: 100.00\n2026-03-04 00:00:00+08:00: 101.25",
        )


class MainTests(unittest.TestCase):
    @patch("check_stock.logout_api")
    @patch("check_stock.send_line")
    @patch("check_stock.build_carousel", return_value={"type": "carousel"})
    @patch("check_stock.build_stock_bubble")
    @patch("check_stock.fetch_rules")
    def test_main_sends_carousel_when_bubbles_exist(
        self,
        mock_fetch_rules,
        mock_build_stock_bubble,
        mock_build_carousel,
        mock_send_line,
        mock_logout_api,
    ):
        mock_fetch_rules.return_value = [stock_job.Rule("VOO", 5, 5.0), stock_job.Rule("VT", 5, 5.0)]
        mock_build_stock_bubble.side_effect = [{"type": "bubble", "hero": "one"}, None]

        stock_job.main()

        mock_build_carousel.assert_called_once_with([{"type": "bubble", "hero": "one"}])
        mock_send_line.assert_called_once_with({"type": "carousel"})
        mock_logout_api.assert_called_once()

    @patch("check_stock.logout_api")
    @patch("check_stock.send_line", side_effect=RuntimeError("send_line failed"))
    @patch("check_stock.build_carousel", return_value={"type": "carousel"})
    @patch("check_stock.build_stock_bubble", return_value={"type": "bubble"})
    @patch("check_stock.fetch_rules", return_value=[stock_job.Rule("VOO", 5, 5.0)])
    def test_main_ensures_logout_api_on_send_line_failure(
        self,
        mock_fetch_rules,
        mock_build_stock_bubble,
        mock_build_carousel,
        mock_send_line,
        mock_logout_api,
    ):
        with self.assertRaises(RuntimeError):
            stock_job.main()
        mock_send_line.assert_called_once_with({"type": "carousel"})
        mock_logout_api.assert_called_once()


if __name__ == "__main__":
    unittest.main()