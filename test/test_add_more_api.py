import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import add_more_api


class BuildAddMoreUrlTests(unittest.TestCase):
    def test_build_add_more_url_adds_symbol_query_parameter(self):
        url = add_more_api.build_add_more_url(
            "0050.TW",
            "https://example.test/add-more",
        )

        self.assertEqual(url, "https://example.test/add-more?symbol=0050.TW")

    def test_build_add_more_url_preserves_existing_query_parameters(self):
        url = add_more_api.build_add_more_url(
            "A B&TEST",
            "https://example.test/add-more?source=line",
        )

        parsed_url = urlsplit(url)
        self.assertEqual(parsed_url.path, "/add-more")
        self.assertEqual(
            parse_qs(parsed_url.query),
            {"source": ["line"], "symbol": ["A B&TEST"]},
        )

    def test_build_add_more_status_url_appends_status_and_preserves_url_parts(self):
        url = add_more_api.build_add_more_status_url(
            "A B&TEST",
            "https://example.test/add-more/?source=line#section",
        )

        parsed_url = urlsplit(url)
        self.assertEqual(parsed_url.path, "/add-more/status")
        self.assertEqual(parsed_url.fragment, "section")
        self.assertEqual(
            parse_qs(parsed_url.query),
            {"source": ["line"], "symbol": ["A B&TEST"]},
        )


class CheckAddMoreStatusTests(unittest.TestCase):
    @patch(
        "add_more_api.build_add_more_status_url",
        return_value="https://example.test/add-more/status?symbol=VOO",
    )
    @patch("add_more_api.requests.get")
    def test_check_add_more_status_returns_boolean_response(self, mock_get, mock_build_url):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = True

        status = add_more_api.check_add_more_status("VOO")

        self.assertTrue(status)
        mock_build_url.assert_called_once_with("VOO")
        mock_get.assert_called_once_with(
            "https://example.test/add-more/status?symbol=VOO",
            timeout=20,
        )

    @patch("add_more_api.requests.get")
    def test_check_add_more_status_returns_false_when_not_added(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = False

        status = add_more_api.check_add_more_status("VOO")

        self.assertFalse(status)

    @patch("add_more_api.requests.get")
    def test_check_add_more_status_fails_open_for_http_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "server error"

        status = add_more_api.check_add_more_status("VOO")

        self.assertFalse(status)
        mock_get.assert_called_once_with(
            "https://example.invalid/api/add-more/status?symbol=VOO",
            timeout=20,
        )

    @patch("add_more_api.requests.get", side_effect=RuntimeError("network error"))
    def test_check_add_more_status_fails_open_for_request_error(self, mock_get):
        status = add_more_api.check_add_more_status("VOO")

        self.assertFalse(status)

    @patch(
        "add_more_api.build_add_more_status_url",
        side_effect=ValueError("invalid URL"),
    )
    def test_check_add_more_status_fails_open_for_invalid_base_url(self, mock_build_url):
        status = add_more_api.check_add_more_status("VOO")

        self.assertFalse(status)
        mock_build_url.assert_called_once_with("VOO")

    @patch("add_more_api.requests.get")
    def test_check_add_more_status_fails_open_for_invalid_response(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"added": True}

        status = add_more_api.check_add_more_status("VOO")

        self.assertFalse(status)

    @patch("add_more_api.requests.get")
    def test_check_add_more_status_fails_open_for_json_error(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError("invalid JSON")

        status = add_more_api.check_add_more_status("VOO")

        self.assertFalse(status)


if __name__ == "__main__":
    unittest.main()