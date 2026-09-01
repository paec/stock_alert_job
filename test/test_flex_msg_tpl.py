import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import flex_msg_tpl


class BuildAddMoreUrlTests(unittest.TestCase):
    def test_build_add_more_url_adds_symbol_query_parameter(self):
        url = flex_msg_tpl._build_add_more_url("0050.TW", "https://example.test/add-more")

        self.assertEqual(url, "https://example.test/add-more?symbol=0050.TW")

    def test_build_add_more_url_preserves_existing_query_parameters(self):
        url = flex_msg_tpl._build_add_more_url(
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
        url = flex_msg_tpl._build_add_more_status_url(
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


class BuildBubbleButtonTests(unittest.TestCase):
    def _build_bubble(self, **kwargs):
        return flex_msg_tpl.build_bubble(
            "VOO",
            "08-01",
            "08-27",
            5,
            -6.0,
            5.0,
            "08-27: 100.00",
            **kwargs,
        )

    def test_build_bubble_does_not_include_button_by_default(self):
        bubble = self._build_bubble()

        self.assertNotIn("footer", bubble)

    @patch("flex_msg_tpl.ADD_MORE_API_URL", "https://example.test/add-more")
    def test_build_bubble_includes_add_more_button_when_enabled(self):
        bubble = self._build_bubble(show_add_more_button=True)

        self.assertEqual(bubble["footer"]["type"], "box")
        button = bubble["footer"]["contents"][0]
        self.assertEqual(button["type"], "button")
        self.assertEqual(button["style"], "primary")
        self.assertEqual(button["action"]["type"], "uri")
        self.assertEqual(button["action"]["label"], "已加碼")
        self.assertEqual(
            button["action"]["uri"],
            "https://example.test/add-more?symbol=VOO",
        )

    @patch("flex_msg_tpl.ADD_MORE_API_URL", "https://example.test/add-more")
    def test_build_bubble_uses_secondary_style_when_already_added(self):
        bubble = self._build_bubble(
            show_add_more_button=True,
            add_more_already_added=True,
        )

        button = bubble["footer"]["contents"][0]
        self.assertEqual(button["style"], "secondary")
        self.assertEqual(button["action"]["label"], "✅ 已加碼")
        self.assertEqual(
            button["action"]["uri"],
            "https://example.test/add-more?symbol=VOO",
        )

    def test_build_bubble_keeps_final_report_title_without_button_when_disabled(self):
        bubble = self._build_bubble(is_final_report=True, show_add_more_button=False)

        self.assertIn("(已關盤)", bubble["header"]["contents"][0]["text"])
        self.assertNotIn("footer", bubble)


if __name__ == "__main__":
    unittest.main()
