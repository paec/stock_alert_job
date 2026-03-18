import datetime as dt
import unittest

import pandas as pd

import check_stock_utils


class ParseHelpersTests(unittest.TestCase):
    def test_parse_positive_int(self):
        self.assertEqual(check_stock_utils.parse_positive_int("12", 5), 12)
        self.assertEqual(check_stock_utils.parse_positive_int(0, 5), 5)
        self.assertEqual(check_stock_utils.parse_positive_int("bad", 5), 5)

    def test_parse_positive_float(self):
        self.assertEqual(check_stock_utils.parse_positive_float("10.5", 3.0), 10.5)
        self.assertEqual(check_stock_utils.parse_positive_float(-1, 3.0), 3.0)
        self.assertEqual(check_stock_utils.parse_positive_float(None, 3.0), 3.0)


class MarketHelpersTests(unittest.TestCase):
    def test_get_market_timezone(self):
        tw_tz, tw_market = check_stock_utils.get_market_timezone("0050.TW")
        us_tz, us_market = check_stock_utils.get_market_timezone("VOO")

        self.assertEqual(str(tw_tz), "Asia/Taipei")
        self.assertEqual(tw_market, "台股")
        self.assertEqual(str(us_tz), "America/New_York")
        self.assertEqual(us_market, "美股")

    def test_get_session_hours(self):
        tw_start, tw_end = check_stock_utils.get_session_hours("台股")
        us_start, us_end = check_stock_utils.get_session_hours("美股")

        self.assertEqual((tw_start, tw_end), (dt.time(8, 0), dt.time(15, 0)))
        self.assertEqual((us_start, us_end), (dt.time(8, 0), dt.time(17, 0)))

    def test_is_today_final_report_time(self):
        self.assertTrue(check_stock_utils.is_today_final_report_time("台股", dt.datetime(2026, 3, 10, 14, 5)))
        self.assertFalse(check_stock_utils.is_today_final_report_time("台股", dt.datetime(2026, 3, 10, 14, 4)))
        self.assertTrue(check_stock_utils.is_today_final_report_time("美股", dt.datetime(2026, 3, 10, 16, 45)))
        self.assertFalse(check_stock_utils.is_today_final_report_time("美股", dt.datetime(2026, 3, 10, 16, 44)))


class PriceHelpersTests(unittest.TestCase):
    def test_calculate_price_change_pct(self):
        series = pd.Series([100.0, 95.0, 90.0, 80.0])
        pct = check_stock_utils.calculate_price_change_pct(series, 3)
        self.assertAlmostEqual(pct, -15.789473684210526)

    def test_threshold_helpers(self):
        self.assertTrue(check_stock_utils.exceeds_drop_threshold(-5.0, 5.0))
        self.assertFalse(check_stock_utils.exceeds_drop_threshold(-4.99, 5.0))
        self.assertTrue(check_stock_utils.exceeds_long_term_drop_threshold(-10.0, 10.0))
        self.assertFalse(check_stock_utils.exceeds_long_term_drop_threshold(10.0, 10.0))


class FormatHistoryTests(unittest.TestCase):
    def test_format_history(self):
        idx = pd.date_range(start="2026-03-01", periods=2, freq="D", tz="America/New_York")
        series = pd.Series([100.0, 101.5], index=idx)

        text = check_stock_utils.format_history(series)

        self.assertEqual(text, "03-01: 100.00\n03-02: 101.50")


if __name__ == "__main__":
    unittest.main()
