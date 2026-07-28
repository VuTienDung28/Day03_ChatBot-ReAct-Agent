import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app import run_react_agent
from prompts import REACT_SYSTEM_PROMPT
from providers import MockProvider


class ReactMilestoneThreeTests(unittest.TestCase):
    def test_prompt_requires_profile_id_verification(self):
        self.assertIn("phải gọi tool", REACT_SYSTEM_PROMPT)
        self.assertIn("xác minh", REACT_SYSTEM_PROMPT)

    def test_case_4_calls_three_tools_in_order(self):
        result = run_react_agent(
            "Tôi là người dùng U001. Hãy tìm người phù hợp nhất, phân tích độ tương thích và gợi ý lời mở đầu.",
            MockProvider(),
            user_id="U001",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            [item["action"] for item in result["trace"]],
            [
                "find_candidate_matches",
                "calculate_compatibility",
                "suggest_first_message",
            ],
        )
        self.assertEqual(result["matches"][0]["candidate_id"], "U002")
        self.assertEqual(result["compatibility"]["total_score"], 90.0)
        self.assertIn("du lịch", result["opener"]["message"])
        self.assertIn("90.0", result["answer"])
        self.assertIn(result["opener"]["message"], result["answer"])

    def test_case_5_verifies_unknown_profile_with_tool(self):
        result = run_react_agent(
            "Tôi là người dùng U999. Hãy tìm người phù hợp nhất với tôi.",
            MockProvider(),
            user_id="U999",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual([item["action"] for item in result["trace"]], ["find_candidate_matches"])
        self.assertEqual(
            result["trace"][0]["action_input"], {"user_id": "U999", "limit": 3}
        )
        self.assertEqual(
            result["trace"][0]["observation"]["error"]["code"],
            "PROFILE_NOT_FOUND",
        )
        self.assertIn("không tìm thấy", result["answer"].lower())


if __name__ == "__main__":
    unittest.main()
