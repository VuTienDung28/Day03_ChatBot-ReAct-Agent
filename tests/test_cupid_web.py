import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LLM_PROVIDER"] = "mock"

from cupid_web.server import app


class CupidWebTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_home_contains_twelve_profile_options(self):
        response = self.client.get("/")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('rel="icon"', text)
        self.assertEqual(text.count("<option value="), 12)
        self.assertIn("U001 · An", text)
        for element_id in (
            "profile-select",
            "compare-form",
            "message-input",
            "send-button",
            "view-switch",
            "baseline-answer",
            "react-answer",
            "match-deck",
            "debug-panel",
            "trace-list",
            "provider-mode",
            "compare-screen",
            "discover-screen",
            "discover-button",
            "back-to-compare",
            "discover-card",
            "discover-title",
            "discover-progress",
            "pass-card",
            "select-card",
            "discover-live-status",
            "start-chat",
            "chat-screen",
            "back-to-discover",
            "chat-candidate-name",
            "chat-candidate-id",
            "chat-avatar",
            "chat-log",
            "typing-indicator",
            "chat-form",
            "chat-input",
            "chat-count",
            "chat-send",
            "chat-error",
            "agent-suggestion",
            "chat-live-status",
            "compare-debug",
            "comparison-status",
            "selected-candidate-context",
            "selected-candidate-avatar",
            "discover-card-help",
            "theme-toggle",
            "profile-avatar",
        ):
            self.assertIn(f'id="{element_id}"', text)
        self.assertIn('id="comparison-workspace" class="comparison-workspace" data-view="compare" aria-busy="false"', text)
        self.assertIn('class="theme-icon theme-icon--sun"', text)
        self.assertIn('class="theme-icon theme-icon--moon"', text)

    def test_visible_shell_copy_avoids_em_and_en_dashes(self):
        response = self.client.get("/")
        text = response.get_data(as_text=True)

        self.assertNotIn("—", text)
        self.assertNotIn("–", text)

    def test_compare_validates_input(self):
        response = self.client.post(
            "/api/compare", json={"user_id": "U001", "message": " "}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_INPUT")

    def test_compare_rejects_unknown_profile(self):
        response = self.client.post(
            "/api/compare",
            json={"user_id": "U999", "message": "Tìm người phù hợp"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "PROFILE_NOT_FOUND")

    def test_compare_returns_both_paths_and_safe_trace(self):
        response = self.client.post(
            "/api/compare",
            json={
                "user_id": "U001",
                "message": "Hãy tìm người phù hợp nhất, phân tích và gợi ý lời mở đầu.",
            },
        )
        data = response.get_json()["data"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["baseline"]["trace"], [])
        self.assertEqual(data["react"]["matches"][0]["candidate_id"], "U002")
        self.assertEqual(len(data["react"]["trace"]), 3)
        self.assertNotIn("Thought", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
