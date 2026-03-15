import unittest
import pandas as pd
from unittest.mock import MagicMock, patch
import shioaji_utils

class TestShioajiUtils(unittest.TestCase):
    @patch("shioaji_utils.sj.Shioaji")
    def test_init_api_and_logout_api(self, mock_shioaji):
        # Test init_api returns the same instance and calls login/activate_ca
        api_instance = MagicMock()
        mock_shioaji.return_value = api_instance
        # First call should create and login
        api = shioaji_utils.init_api()
        self.assertIs(api, api_instance)
        api_instance.login.assert_called()
        api_instance.activate_ca.assert_called()
        # Second call should return cached instance
        api2 = shioaji_utils.init_api()
        self.assertIs(api2, api_instance)
        # Test logout_api resets _api and calls logout
        shioaji_utils.logout_api()
        api_instance.logout.assert_called()
        self.assertIsNone(shioaji_utils._api)

    def test_get_recent_closing_prices(self):
        # Prepare a DataFrame with ts and Close columns
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            "ts": pd.to_datetime(dates),
            "Close": [100, 101, 102, 103, 104],
        })
        result = shioaji_utils.get_recent_closing_prices(df, days=3)
        self.assertEqual(len(result), 3)
        self.assertListEqual(list(result['Close']), [102, 103, 104])
        self.assertIn('Date', result.columns)
        self.assertIn('ts', result.columns)

    def test_format_tw_close_series(self):
        # Prepare a DataFrame with Date and Close columns
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02"],
            "Close": [100, 101]
        })
        series = shioaji_utils.format_tw_close_series(df)
        self.assertEqual(series.index.name, 'Date')
        self.assertListEqual(series.tolist(), [100, 101])

    @patch("shioaji_utils.init_api")
    def test_get_tw_close_prices(self, mock_init_api):
        # Mock API and contract
        api_mock = MagicMock()
        contract_mock = MagicMock()
        api_mock.Contracts.Stocks.__getitem__.return_value = contract_mock
        # Mock kbars return value
        kbars = {
            "ts": pd.date_range("2024-01-01", periods=5, freq="D"),
            "Close": [100, 101, 102, 103, 104],
        }
        api_mock.kbars.return_value = kbars
        mock_init_api.return_value = api_mock
        result = shioaji_utils.get_tw_close_prices("0050.TW", 3)
        self.assertEqual(len(result), 3)
        self.assertListEqual(list(result['Close']), [102, 103, 104])

if __name__ == "__main__":
    unittest.main()
