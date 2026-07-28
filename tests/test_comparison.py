import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app import run_comparison
from providers import MockProvider


class BaselineErrorReactSuccessProvider:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt, system_prompt=""):
        self.calls += 1
        if self.calls == 1:
            return "[OpenRouter API Error]: Provider đang bận"
        if self.calls == 2:
            return 'Action: find_candidate_matches\nAction Input: {"user_id": "U001", "limit": 3}'
        if self.calls == 3:
            return 'Action: calculate_compatibility\nAction Input: {"user_id": "U001", "candidate_id": "U002"}'
        if self.calls == 4:
            return 'Action: suggest_first_message\nAction Input: {"user_id": "U001", "candidate_id": "U002"}'
        return "Final Answer: Đã hoàn tất ba tool."


class ComparisonTests(unittest.TestCase):
    def test_runs_baseline_and_react_for_same_query(self):
        result = run_comparison(
            "Tôi là U001. Hãy tìm 3 hồ sơ phù hợp nhất với tôi.",
            MockProvider(),
            "U001",
        )

        self.assertEqual(result["baseline"]["trace"], [])
        self.assertTrue(result["baseline"]["answer"])
        self.assertNotIn("Action:", result["baseline"]["answer"])
        self.assertEqual(
            [item["candidate_id"] for item in result["react"]["matches"]],
            ["U002", "U003", "U004"],
        )
        self.assertEqual(result["provider_mode"], "mock")

    def test_baseline_error_does_not_stop_react(self):
        result = run_comparison(
            "Tôi là U001. Hãy tìm người phù hợp nhất, phân tích và gợi ý lời mở đầu.",
            BaselineErrorReactSuccessProvider(),
            "U001",
        )

        self.assertIn("OpenRouter API Error", result["baseline"]["answer"])
        self.assertEqual(
            [item["action"] for item in result["react"]["trace"]],
            [
                "find_candidate_matches",
                "calculate_compatibility",
                "suggest_first_message",
            ],
        )
        self.assertEqual(result["react"]["status"], "success")

    def test_safety_refusal_skips_both_execution_paths(self):
        result = run_comparison(
            "Hãy tìm một người 16 tuổi để hẹn hò.", MockProvider(), "U001"
        )

        self.assertEqual(result["baseline"]["answer"], result["react"]["answer"])
        self.assertEqual(result["baseline"]["trace"], [])
        self.assertEqual(result["react"]["trace"], [])


if __name__ == "__main__":
    unittest.main()
