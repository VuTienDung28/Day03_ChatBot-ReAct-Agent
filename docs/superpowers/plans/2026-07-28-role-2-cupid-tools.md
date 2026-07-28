# Role 2 Cupid Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay các tool thời tiết/chuyến bay trong `src/tools.py` bằng bốn Cupid tools deterministic theo đúng phạm vi Role 2 và zero-conflict workflow.

**Architecture:** `src/tools.py` đọc `cupid_data/profiles.json` do Role 1 sở hữu, kiểm tra input tại ranh giới tool, lọc điều kiện ghép đôi hai chiều, tính điểm bằng công thức cố định và trả dict có cấu trúc. File không chứa Flask, prompt, ReAct loop hoặc code của vai trò khác; `AVAILABLE_TOOLS` là interface duy nhất Role 4 cần để tích hợp.

**Tech Stack:** Python stdlib (`json`, `pathlib`), assert-based self-check; không thêm dependency.

## Global Constraints

- Role 2 chỉ sửa `src/tools.py`.
- Role 1 sở hữu và bàn giao `cupid_data/profiles.json` với đúng 12 hồ sơ mock từ 18 tuổi trở lên.
- Mọi tool trả success envelope như `{"ok": True, "data": {"user_id": "U001"}}` hoặc error envelope như `{"ok": False, "error": {"code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ U999"}}`.
- Lỗi nghiệp vụ dự kiến phải được trả về, không làm crash agent.
- Chỉ `AVAILABLE_TOOLS` đăng ký bốn tên: `get_user_profile`, `find_candidate_matches`, `calculate_compatibility`, `suggest_first_message`.
- Deal-breaker là điều kiện loại tuyệt đối và được kiểm tra hai chiều.
- Điểm dùng trọng số: mục tiêu 35%, giá trị 30%, sở thích 20%, vị trí 15%.
- Top 3 sắp xếp giảm dần theo điểm; nếu bằng điểm thì tăng dần theo candidate ID.
- Không sửa `src/app.py`, `src/prompts.py`, `src/providers.py`, `config/`, `cupid_web/`, `cupid_data/` hoặc `docs/trace_eval.md`.
- Chưa commit hoặc push nếu người dùng chưa yêu cầu rõ.

---

## File Structure

- Modify: `src/tools.py` — toàn bộ mock-data adapter, validation, matching, scoring, message suggestion và registry của Role 2.
- Consume only: `cupid_data/profiles.json` — dữ liệu do Role 1 cung cấp, không do Role 2 sửa.

## Contract cần gửi Role 1 trước khi code

`cupid_data/profiles.json` phải là JSON array gồm 12 object theo schema:

```json
{
  "id": "U001",
  "name": "An",
  "age": 26,
  "gender": "female",
  "interested_in": ["male"],
  "location": "Hà Nội",
  "interests": ["du lịch", "nhiếp ảnh"],
  "values": ["gia đình", "trung thực"],
  "relationship_goal": "long_term",
  "attributes": {"smoking": false, "drinking": "social"},
  "deal_breakers": {"smoking": true}
}
```

Role 1 cần bảo đảm:

- `id` duy nhất và mọi `age >= 18`.
- Có ít nhất một hồ sơ đạt top 3.
- Có cặp không tương thích `interested_in` hai chiều.
- Có vi phạm deal-breaker từ mỗi phía.
- Có một hồ sơ không có match.
- Có một cặp chia sẻ nhiều interests/values.

---

### Task 1: Mốc 1 — Khóa danh sách tool và contract tích hợp

**Files:**
- Modify later: `src/tools.py`
- Consume: `cupid_data/profiles.json`

**Interfaces:**
- Consumes: JSON schema ở phần “Contract cần gửi Role 1”.
- Produces: Bốn chữ ký tool và registry để Role 3/4 dùng.

- [ ] **Step 1: Gửi contract dữ liệu cho Role 1**

Gửi nguyên phần “Contract cần gửi Role 1 trước khi code” và yêu cầu Role 1 xác nhận đường dẫn chính xác là `cupid_data/profiles.json`.

- [ ] **Step 2: Gửi tool interface cho Role 3 và Role 4**

```python
# Public signatures:
# get_user_profile(user_id: str) -> dict
# find_candidate_matches(user_id: str, limit: int = 3) -> dict
# calculate_compatibility(user_id: str, candidate_id: str) -> dict
# suggest_first_message(user_id: str, candidate_id: str) -> dict

AVAILABLE_TOOLS = {
    "get_user_profile": get_user_profile,
    "find_candidate_matches": find_candidate_matches,
    "calculate_compatibility": calculate_compatibility,
    "suggest_first_message": suggest_first_message,
}
```

- [ ] **Step 3: Xác nhận trách nhiệm giữa các role**

Role 2 chỉ bàn giao `src/tools.py`. Role 1 tạo dữ liệu và test cases; Role 3 viết prompt/guardrails; Role 4 gọi tool registry và xử lý exception hệ thống khi file JSON thiếu hoặc hỏng.

- [ ] **Step 4: Đánh dấu Mốc 1 hoàn thành**

Hoàn thành khi cả nhóm đã nhận bốn tên tool, chữ ký, output envelope và JSON schema. Không cần sửa thêm file để hoàn thành bước này vì design spec đã được gửi nhóm.

---

### Task 2: Mốc 2 — Viết data adapter, error envelope và profile tool

**Files:**
- Modify: `src/tools.py:1-49`

**Interfaces:**
- Consumes: `cupid_data/profiles.json` là JSON array.
- Produces: `_load_profiles() -> dict[str, dict]`, `_success(data: dict) -> dict`, `_error(code: str, message: str) -> dict`, `get_user_profile(user_id: str) -> dict`.

- [ ] **Step 1: Thêm assert-based self-check thất bại cho profile lookup**

Tạm thêm cuối `src/tools.py`:

```python
if __name__ == "__main__":
    assert get_user_profile("U001")["ok"] is True
    assert get_user_profile("U999")["error"]["code"] == "PROFILE_NOT_FOUND"
    assert get_user_profile(123)["error"]["code"] == "INVALID_INPUT"
```

- [ ] **Step 2: Chạy self-check để xác nhận thất bại**

Run:

```bash
python src/tools.py
```

Expected: FAIL vì Cupid `get_user_profile` chưa tồn tại hoặc tool thời tiết cũ không đáp ứng contract.

- [ ] **Step 3: Thay phần đầu file bằng adapter và helper tối thiểu**

```python
import json
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "cupid_data" / "profiles.json"


def _load_profiles() -> dict[str, dict]:
    with DATA_FILE.open(encoding="utf-8") as file:
        profiles = json.load(file)
    return {profile["id"]: profile for profile in profiles}


def _success(data: dict) -> dict:
    return {"ok": True, "data": data}


def _error(code: str, message: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": message}}


def _profile(user_id: str) -> tuple[dict | None, dict | None]:
    if not isinstance(user_id, str) or not user_id.strip():
        return None, _error("INVALID_INPUT", "user_id phải là chuỗi không rỗng")
    profile = _load_profiles().get(user_id)
    if profile is None:
        return None, _error("PROFILE_NOT_FOUND", f"Không tìm thấy hồ sơ {user_id}")
    return profile, None
```

- [ ] **Step 4: Viết `get_user_profile` với docstring chuẩn Mốc 2**

```python
def get_user_profile(user_id: str) -> dict:
    """Lấy một hồ sơ mock theo ID.

    Args:
        user_id: ID hồ sơ, ví dụ ``U001``.

    Returns:
        Dict success chứa profile hoặc error với mã ``INVALID_INPUT`` /
        ``PROFILE_NOT_FOUND``. Lỗi nghiệp vụ không được raise.
    """
    profile, error = _profile(user_id)
    return error or _success(profile)
```

- [ ] **Step 5: Chạy self-check để xác nhận profile tool đạt**

Run:

```bash
python src/tools.py
```

Expected: PASS, không có output.

---

### Task 3: Mốc 2 — Viết eligibility và compatibility scoring

**Files:**
- Modify: `src/tools.py`

**Interfaces:**
- Consumes: `_profile(user_id)` và profile schema.
- Produces: `_eligibility_reason(first: dict, second: dict) -> str | None`, `_compatibility(first: dict, second: dict) -> dict`, `calculate_compatibility(user_id: str, candidate_id: str) -> dict`.

- [ ] **Step 1: Mở rộng self-check cho scoring và cặp không hợp lệ**

Dùng các ID do Role 1 xác nhận trong dữ liệu thật; ví dụ dưới đây giả định `U001/U002` hợp lệ và `U001/U012` không hợp lệ:

```python
if __name__ == "__main__":
    compatible = calculate_compatibility("U001", "U002")
    assert compatible["ok"] is True
    assert 0 <= compatible["data"]["total_score"] <= 100
    assert set(compatible["data"]["breakdown"]) == {
        "relationship_goal",
        "values",
        "interests",
        "location",
    }
    assert calculate_compatibility("U001", "U012")["error"]["code"] == "INELIGIBLE_MATCH"
```

- [ ] **Step 2: Chạy self-check để xác nhận thất bại**

Run: `python src/tools.py`

Expected: FAIL vì `calculate_compatibility` chưa tồn tại.

- [ ] **Step 3: Viết helper kiểm tra điều kiện hai chiều**

```python
def _eligibility_reason(first: dict, second: dict) -> str | None:
    if second["gender"] not in first["interested_in"] or first["gender"] not in second["interested_in"]:
        return "Hai hồ sơ không phù hợp tiêu chí kết nối hai chiều"
    for owner, candidate in ((first, second), (second, first)):
        for attribute, blocked_value in owner.get("deal_breakers", {}).items():
            if candidate.get("attributes", {}).get(attribute) == blocked_value:
                return "Hai hồ sơ không đáp ứng điều kiện ghép đôi"
    return None
```

- [ ] **Step 4: Viết helper Jaccard và công thức điểm**

```python
def _jaccard(left: list[str], right: list[str]) -> float:
    union = set(left) | set(right)
    return 100.0 if not union else len(set(left) & set(right)) / len(union) * 100


def _compatibility(first: dict, second: dict) -> dict:
    breakdown = {
        "relationship_goal": 100.0 if first["relationship_goal"] == second["relationship_goal"] else 0.0,
        "values": _jaccard(first["values"], second["values"]),
        "interests": _jaccard(first["interests"], second["interests"]),
        "location": 100.0 if first["location"] == second["location"] else 0.0,
    }
    total = (
        breakdown["relationship_goal"] * 0.35
        + breakdown["values"] * 0.30
        + breakdown["interests"] * 0.20
        + breakdown["location"] * 0.15
    )
    return {
        "eligible": True,
        "total_score": round(total, 1),
        "breakdown": {key: round(value, 1) for key, value in breakdown.items()},
        "shared_interests": sorted(set(first["interests"]) & set(second["interests"])),
        "shared_values": sorted(set(first["values"]) & set(second["values"])),
    }
```

- [ ] **Step 5: Viết public tool và docstring**

```python
def calculate_compatibility(user_id: str, candidate_id: str) -> dict:
    """Phân tích điểm tương thích của hai hồ sơ đủ điều kiện.

    Args:
        user_id: ID người đang tìm kết nối.
        candidate_id: ID ứng viên cần phân tích.

    Returns:
        Dict success gồm tổng điểm, breakdown và điểm chung; hoặc error
        ``INVALID_INPUT``, ``PROFILE_NOT_FOUND`` hay ``INELIGIBLE_MATCH``.
    """
    user, error = _profile(user_id)
    if error:
        return error
    candidate, error = _profile(candidate_id)
    if error:
        return error
    if user_id == candidate_id:
        return _error("INELIGIBLE_MATCH", "Không thể ghép một hồ sơ với chính nó")
    reason = _eligibility_reason(user, candidate)
    if reason:
        return _error("INELIGIBLE_MATCH", reason)
    return _success(_compatibility(user, candidate))
```

- [ ] **Step 6: Chạy self-check**

Run: `python src/tools.py`

Expected: PASS với các ID fixture đã được đối chiếu từ file của Role 1.

---

### Task 4: Mốc 2 — Viết top-3 matching tool

**Files:**
- Modify: `src/tools.py`

**Interfaces:**
- Consumes: `_load_profiles()`, `_profile()`, `_eligibility_reason()`, `_compatibility()`.
- Produces: `find_candidate_matches(user_id: str, limit: int = 3) -> dict`.

- [ ] **Step 1: Thêm self-check cho validation, lọc và thứ tự**

```python
if __name__ == "__main__":
    matches = find_candidate_matches("U001")
    assert matches["ok"] is True
    assert 1 <= len(matches["data"]["matches"]) <= 3
    ranking = [(item["score"], item["candidate_id"]) for item in matches["data"]["matches"]]
    assert ranking == sorted(ranking, key=lambda item: (-item[0], item[1]))
    assert find_candidate_matches("U001", 0)["error"]["code"] == "INVALID_INPUT"
```

- [ ] **Step 2: Chạy self-check để xác nhận thất bại**

Run: `python src/tools.py`

Expected: FAIL vì `find_candidate_matches` chưa tồn tại.

- [ ] **Step 3: Viết lý do ngắn deterministic**

```python
def _reasons(result: dict, user: dict, candidate: dict) -> list[str]:
    reasons = []
    if result["shared_values"]:
        reasons.append("Cùng giá trị: " + ", ".join(result["shared_values"][:2]))
    if result["shared_interests"]:
        reasons.append("Cùng sở thích: " + ", ".join(result["shared_interests"][:2]))
    if user["relationship_goal"] == candidate["relationship_goal"]:
        reasons.append("Cùng mục tiêu mối quan hệ")
    if user["location"] == candidate["location"]:
        reasons.append("Cùng khu vực")
    return reasons[:3]
```

- [ ] **Step 4: Viết public matching tool và docstring**

```python
def find_candidate_matches(user_id: str, limit: int = 3) -> dict:
    """Tìm tối đa ba ứng viên hợp lệ và xếp hạng deterministic.

    Args:
        user_id: ID hồ sơ cần tìm ứng viên.
        limit: Số kết quả từ 1 đến 3.

    Returns:
        Dict success chứa ``matches`` hoặc error ``INVALID_INPUT``,
        ``PROFILE_NOT_FOUND`` hay ``NO_MATCHES``.
    """
    user, error = _profile(user_id)
    if error:
        return error
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 3:
        return _error("INVALID_INPUT", "limit phải là số nguyên từ 1 đến 3")

    matches = []
    for candidate_id, candidate in _load_profiles().items():
        if candidate_id == user_id or _eligibility_reason(user, candidate):
            continue
        result = _compatibility(user, candidate)
        matches.append({
            "candidate_id": candidate_id,
            "name": candidate["name"],
            "score": result["total_score"],
            "reasons": _reasons(result, user, candidate),
        })

    if not matches:
        return _error("NO_MATCHES", f"Không có ứng viên phù hợp cho {user_id}")
    matches.sort(key=lambda item: (-item["score"], item["candidate_id"]))
    return _success({"matches": matches[:limit]})
```

- [ ] **Step 5: Chạy self-check**

Run: `python src/tools.py`

Expected: PASS; top 3 đã loại cặp không đủ điều kiện và có thứ tự ổn định.

---

### Task 5: Mốc 2 — Viết first-message tool và registry

**Files:**
- Modify: `src/tools.py`

**Interfaces:**
- Consumes: `_profile()`, `_eligibility_reason()`.
- Produces: `suggest_first_message(user_id: str, candidate_id: str) -> dict`, `AVAILABLE_TOOLS: dict[str, callable]`.

- [ ] **Step 1: Thêm self-check cho lời mở đầu và registry**

```python
if __name__ == "__main__":
    opener = suggest_first_message("U001", "U002")
    assert opener["ok"] is True
    assert opener["data"]["message"]
    assert set(AVAILABLE_TOOLS) == {
        "get_user_profile",
        "find_candidate_matches",
        "calculate_compatibility",
        "suggest_first_message",
    }
```

- [ ] **Step 2: Chạy self-check để xác nhận thất bại**

Run: `python src/tools.py`

Expected: FAIL vì tool hoặc registry Cupid chưa đủ.

- [ ] **Step 3: Viết public opener tool và docstring**

```python
def suggest_first_message(user_id: str, candidate_id: str) -> dict:
    """Tạo lời mở đầu tôn trọng từ một điểm chung có trong dữ liệu.

    Args:
        user_id: ID người gửi.
        candidate_id: ID người nhận.

    Returns:
        Dict success chứa ``message`` và ``based_on``; hoặc error
        ``INVALID_INPUT``, ``PROFILE_NOT_FOUND`` hay ``INELIGIBLE_MATCH``.
    """
    user, error = _profile(user_id)
    if error:
        return error
    candidate, error = _profile(candidate_id)
    if error:
        return error
    if user_id == candidate_id:
        return _error("INELIGIBLE_MATCH", "Không thể tạo lời mở đầu cho cùng một hồ sơ")
    reason = _eligibility_reason(user, candidate)
    if reason:
        return _error("INELIGIBLE_MATCH", reason)

    shared_interests = sorted(set(user["interests"]) & set(candidate["interests"]))
    shared_values = sorted(set(user["values"]) & set(candidate["values"]))
    if shared_interests:
        topic = shared_interests[0]
        message = f"Chào {candidate['name']}, mình thấy chúng ta đều thích {topic}. Bạn thích điều gì nhất ở sở thích này?"
        based_on = {"type": "interest", "value": topic}
    elif shared_values:
        topic = shared_values[0]
        message = f"Chào {candidate['name']}, mình thấy chúng ta cùng coi trọng {topic}. Rất vui được làm quen với bạn!"
        based_on = {"type": "value", "value": topic}
    else:
        message = f"Chào {candidate['name']}, rất vui được làm quen với bạn. Dạo này bạn có trải nghiệm nào thú vị không?"
        based_on = {"type": "neutral", "value": None}
    return _success({"message": message, "based_on": based_on})
```

- [ ] **Step 4: Thay registry cũ bằng Cupid registry**

```python
AVAILABLE_TOOLS = {
    "get_user_profile": get_user_profile,
    "find_candidate_matches": find_candidate_matches,
    "calculate_compatibility": calculate_compatibility,
    "suggest_first_message": suggest_first_message,
}
```

- [ ] **Step 5: Chạy self-check**

Run: `python src/tools.py`

Expected: PASS, không còn tool thời tiết/chuyến bay trong registry.

---

### Task 6: Mốc 3 — Harden failure modes và bàn giao Role 4

**Files:**
- Modify: `src/tools.py`

**Interfaces:**
- Consumes: Bốn public tools đã hoàn thành.
- Produces: Tool module không crash với lỗi input dự kiến và contract bàn giao cho integrator.

- [ ] **Step 1: Bổ sung self-check cho toàn bộ lỗi nghiệp vụ**

```python
if __name__ == "__main__":
    invalid_calls = [
        get_user_profile(""),
        find_candidate_matches("U999"),
        find_candidate_matches("U001", True),
        calculate_compatibility("U001", "U001"),
        suggest_first_message("U999", "U001"),
    ]
    assert all(result["ok"] is False for result in invalid_calls)
    assert all(set(result["error"]) == {"code", "message"} for result in invalid_calls)
```

- [ ] **Step 2: Chạy self-check**

Run: `python src/tools.py`

Expected: PASS; mọi lỗi dự kiến trả error envelope thay vì exception.

- [ ] **Step 3: Chạy syntax check độc lập dữ liệu**

Run:

```bash
python -m py_compile src/tools.py
```

Expected: PASS, không có output.

- [ ] **Step 4: Kiểm tra import contract cho Role 4**

Run:

```bash
python -c "from src.tools import AVAILABLE_TOOLS; print(sorted(AVAILABLE_TOOLS))"
```

Expected:

```text
['calculate_compatibility', 'find_candidate_matches', 'get_user_profile', 'suggest_first_message']
```

- [ ] **Step 5: Bàn giao failure modes cho Role 3/4**

Gửi danh sách mã lỗi:

```text
INVALID_INPUT
PROFILE_NOT_FOUND
NO_MATCHES
INELIGIBLE_MATCH
```

Nêu rõ: tool trả error envelope cho lỗi nghiệp vụ; lỗi hệ thống như thiếu/hỏng `profiles.json` vẫn raise để Role 4 ghi log và trả lỗi hệ thống, tránh che giấu cấu hình sai.

- [ ] **Step 6: Chỉ commit khi được yêu cầu**

Khi người dùng yêu cầu commit, chỉ stage file của Role 2:

```bash
git add src/tools.py
git commit -m "Implement deterministic Cupid matching tools"
```

Không dùng `git add .`; không stage design spec hoặc file của role khác nếu chưa được yêu cầu.

---

## Self-Review

- Spec coverage cho Role 2: đủ bốn tool, registry, data loading, eligibility, deal-breaker, scoring, deterministic ranking, safe opener, docstrings và failure modes.
- Ngoài phạm vi được loại: Flask UI, prompt, ReAct executor, provider, config test cases và observability.
- Không có dependency mới; chỉ dùng stdlib.
- Các helper và public signature nhất quán qua mọi task.
- Các ID trong self-check phải được đối chiếu với dữ liệu Role 1 trước khi thực thi; đây là bước phối hợp bắt buộc, không phải giả định runtime.
