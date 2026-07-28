import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from providers import OpenRouterProvider


class OpenRouterProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = OpenRouterProvider(api_key="test-key", model="test/model")

    def response(self, payload=None, status=200, text=""):
        response = Mock(status_code=status, text=text)
        if isinstance(payload, Exception):
            response.json.side_effect = payload
        else:
            response.json.return_value = payload
        return response

    @patch("providers.requests.post")
    def test_returns_valid_completion_content(self, post):
        post.return_value = self.response(
            {"choices": [{"message": {"content": "Xin chào"}}]}
        )

        self.assertEqual(self.provider.generate("hello"), "Xin chào")
        post.assert_called_once()

    @patch("providers.requests.post")
    def test_normalizes_http_200_error_envelope(self, post):
        post.return_value = self.response(
            {"error": {"code": 429, "message": "Provider đang bận"}}
        )

        result = self.provider.generate("hello")

        self.assertEqual(result, "[OpenRouter API Error]: Provider đang bận")
        self.assertNotIn("test-key", result)
        self.assertNotIn("choices", result)

    @patch("providers.requests.post")
    def test_rejects_malformed_success_envelopes(self, post):
        malformed = (
            {},
            {"choices": []},
            {"choices": [{}]},
            {"choices": [{"message": {}}]},
            {"choices": [{"message": {"content": " "}}]},
        )

        for payload in malformed:
            with self.subTest(payload=payload):
                post.return_value = self.response(payload)
                result = self.provider.generate("hello")
                self.assertEqual(
                    result,
                    "[OpenRouter API Error]: Phản hồi không có nội dung completion hợp lệ",
                )

    @patch("providers.requests.post")
    def test_rejects_invalid_json_without_leaking_parser_exception(self, post):
        post.return_value = self.response(ValueError("raw parser details"))

        result = self.provider.generate("hello")

        self.assertEqual(
            result,
            "[OpenRouter API Error]: Phản hồi không có nội dung completion hợp lệ",
        )
        self.assertNotIn("raw parser details", result)

    @patch("providers.requests.post")
    def test_non_200_response_does_not_retry(self, post):
        post.return_value = self.response(status=429, text="rate limited")

        result = self.provider.generate("hello")

        self.assertEqual(result, "[OpenRouter API Error 429]: rate limited")
        post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
