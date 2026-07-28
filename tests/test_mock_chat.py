import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MockChatContractTests(unittest.TestCase):
    def test_chat_functions_and_local_state_exist(self):
        source = (ROOT / "cupid_web" / "app.js").read_text(encoding="utf-8")

        for token in (
            "SCRIPTED_REPLIES",
            "function chatThread",
            "function enterChat",
            "function exitChat",
            "function renderChat",
            "function sendMockMessage",
            "function validateMockMessage",
            "function appendMockReply",
        ):
            self.assertIn(token, source)
        self.assertIn("chats:", source)
        self.assertIn("500", source)
        self.assertIn("event.isComposing", source)

    def test_mock_chat_functions_do_not_fetch_or_render_html(self):
        source = (ROOT / "cupid_web" / "app.js").read_text(encoding="utf-8")
        chat_source = source[
            source.index("function validateMockMessage"):source.index("function resetCardPosition")
        ]

        self.assertNotIn('fetch("', chat_source)
        self.assertNotIn("innerHTML", source)
        self.assertIn('setAttribute("aria-busy"', source)
        self.assertIn("renderPendingComparison", source)
        self.assertIn("renderSelectedCandidate", source)
        self.assertIn("Hãy nhập yêu cầu để so sánh.", source)
        self.assertIn("function applyTheme", source)
        self.assertIn("cupid-theme", source)
        self.assertIn("function renderAvatar", source)
        self.assertIn('addEventListener("error"', source)
        for profile_id in (f"U{index:03}" for index in range(1, 13)):
            self.assertIn(f"{profile_id}:", source)
        for term in ("tình dục", "ép buộc", "địa chỉ nhà", "số điện thoại"):
            self.assertIn(term, chat_source)


if __name__ == "__main__":
    unittest.main()
