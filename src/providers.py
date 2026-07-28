"""
🔌 MULTI-PROVIDER LLM ADAPTER (OpenAI, Gemini, Anthropic, OpenRouter & Offline Mock)
Hỗ trợ chuyển đổi linh hoạt giữa các nhà cung cấp AI chỉ bằng cách đổi biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho tất cả các LLM Provider"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env!"
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (GPT-4o, GPT-3.5-turbo, etc.)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env!"
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider (Claude 3.5 Sonnet, Claude 3 Haiku)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "claude-3-haiku-20240307"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_anthropic_api_key_here":
            return "[Anthropic Error]: Chưa cấu hình ANTHROPIC_API_KEY trong file .env!"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model_name,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            return f"[Anthropic Exception]: {str(e)}"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter Provider (Hỗ trợ gọi mọi model qua OpenRouter API)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "google/gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return "[OpenRouter Error]: Chưa cấu hình OPENROUTER_API_KEY trong file .env!"
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"[OpenRouter API Error {res.status_code}]: {res.text}"
        except Exception as e:
            return f"[OpenRouter Exception]: {str(e)}"


class MockProvider(BaseLLMProvider):
    """Offline provider deterministic cho các luồng demo Cupid."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        text = prompt.lower()
        system_text = system_prompt.lower()

        if "react agent" not in system_text:
            if "3 yếu tố quan trọng" in text:
                return (
                    "Ba yếu tố quan trọng gồm mục tiêu mối quan hệ, giá trị "
                    "sống và sở thích chung. Kết quả chỉ mang tính tham khảo."
                )
            if "địa chỉ nhà" in text or "tọa độ chính xác" in text:
                return (
                    "Không nên chia sẻ vị trí chính xác với người lạ vì điều "
                    "đó có thể ảnh hưởng đến quyền riêng tư và an toàn cá nhân."
                )
            if "u999" in text:
                return (
                    "Không tìm thấy hồ sơ U999 trong dữ liệu mô phỏng được "
                    "cung cấp. Bạn vui lòng kiểm tra lại mã hồ sơ."
                )
            if "gợi ý lời mở đầu" in text:
                return (
                    "Theo dữ liệu mô phỏng, U002 là ứng viên nổi bật cho U001. "
                    "Lời mở đầu gợi ý: Chào Bình, mình thấy chúng ta đều thích "
                    "du lịch. Bạn thích điều gì nhất ở sở thích này?"
                )
            if "tìm 3 hồ sơ" in text or "tìm người phù hợp" in text:
                return (
                    "Theo dữ liệu mô phỏng, ba hồ sơ nổi bật là U002, U003 và "
                    "U004. Baseline không dùng tool nên kết quả này không được "
                    "bảo đảm deterministic."
                )
            return "Đây là phản hồi baseline minh họa, không sử dụng tool."

        selected_match = re.search(
            r"hồ sơ người dùng đã chọn:\s*(u\d+)",
            text,
            re.I,
        )
        query_ids = re.findall(r"\bu\d{3,}\b", text, re.I)
        user_id = (
            selected_match.group(1).upper()
            if selected_match
            else (query_ids[0].upper() if query_ids else None)
        )
        candidate_match = re.search(
            r'"candidate_id"\s*:\s*"(u\d+)"',
            text,
            re.I,
        )
        candidate_id = (
            candidate_match.group(1).upper()
            if candidate_match
            else None
        )

        if "profile_not_found" in text:
            return (
                f"Final Answer: Không tìm thấy hồ sơ {user_id or 'đã chọn'} "
                "trong dữ liệu mô phỏng. Bạn vui lòng kiểm tra lại mã hồ sơ."
            )

        wants_analysis = (
            "phân tích độ tương thích" in text or "phân tích tương thích" in text
        )
        wants_opener = "lời mở đầu" in text
        has_matches = '"matches"' in text and '"candidate_id"' in text
        has_compatibility = '"total_score"' in text and '"breakdown"' in text
        has_opener = '"message"' in text and '"based_on"' in text

        if has_opener:
            return (
                "Final Answer: Đã tạo lời mở đầu từ Observation đã được xác "
                "minh."
            )

        if has_compatibility and wants_opener:
            return (
                "Action: suggest_first_message\n"
                f'Action Input: {{"user_id": "{user_id}", '
                f'"candidate_id": "{candidate_id}"}}'
            )

        if has_compatibility:
            return (
                "Final Answer: Đã phân tích độ tương thích bằng dữ liệu tool."
            )

        if has_matches and wants_analysis:
            return (
                "Action: calculate_compatibility\n"
                f'Action Input: {{"user_id": "{user_id}", '
                f'"candidate_id": "{candidate_id}"}}'
            )

        if has_matches:
            return (
                "Final Answer: Đã tìm thấy các ứng viên phù hợp từ dữ liệu "
                "tool."
            )

        wants_matches = (
            re.search(
                r"\b(tìm|đề xuất|gợi ý)\b.*\b(người|ứng viên|hồ sơ)\b",
                text,
                re.I,
            )
            or "ghép đôi" in text
            or "phù hợp nhất" in text
        )
        if user_id and wants_matches:
            return (
                "Action: find_candidate_matches\n"
                f'Action Input: {{"user_id": "{user_id}", "limit": 3}}'
            )

        if "3 yếu tố quan trọng" in text:
            return (
                "Final Answer: Ba yếu tố quan trọng gồm mục tiêu mối quan hệ, "
                "giá trị sống và sở thích chung."
            )

        if "địa chỉ nhà" in text or "tọa độ chính xác" in text:
            return (
                "Final Answer: Không nên chia sẻ vị trí chính xác với người lạ "
                "vì có thể ảnh hưởng đến quyền riêng tư và an toàn cá nhân."
            )

        return (
            "Final Answer: Yêu cầu nằm ngoài các luồng Cupid demo hiện được "
            "hỗ trợ."
        )


def get_llm_provider(provider_name: str = None) -> BaseLLMProvider:
    """Factory function tự chọn Provider từ biến môi trường LLM_PROVIDER"""
    name = (provider_name or os.getenv("LLM_PROVIDER") or "mock").lower().strip()
    
    if name == "gemini":
        return GeminiProvider()
    elif name == "openai":
        return OpenAIProvider()
    elif name == "anthropic":
        return AnthropicProvider()
    elif name == "openrouter":
        return OpenRouterProvider()
    else:
        return MockProvider()


if __name__ == "__main__":
    print("=== TEST MULTI-PROVIDER LLM ADAPTER ===")
    provider = get_llm_provider()
    print(f"✅ Provider đang dùng: {provider.__class__.__name__}")
    print(f"🤖 User Query: Hello")
    print(f"💬 Response  : {provider.generate('Hello')}")
