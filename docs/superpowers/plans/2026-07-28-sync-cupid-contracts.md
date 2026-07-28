# Cupid Contract Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đồng bộ data path, test cases và ReAct prompt với bốn Cupid tools hiện có.

**Architecture:** `src/tools.py` tiếp tục là nguồn sự thật cho tool registry và đọc dữ liệu thật từ `cupid_data/cupid_profiles.json`. `config/test_cases.json` chỉ mô tả tình huống mà schema hiện có hỗ trợ; `src/prompts.py` chỉ liệt kê tool có trong registry và dùng JSON action input.

**Tech Stack:** Python stdlib, JSON.

## Global Constraints

- Giữ bốn tool: `get_user_profile`, `find_candidate_matches`, `calculate_compatibility`, `suggest_first_message`.
- Không thêm alias `search_candidates` hoặc `rank_candidates_by_compatibility`.
- Không thêm trường chiều cao, tọa độ hoặc khoảng cách.
- Giữ `MAX_ITERATIONS = 3`.
- Không thêm web UI hoặc dependency.
- Không commit/push nếu chưa được yêu cầu.

---

### Task 1: Sửa data path

**Files:**
- Modify: `src/tools.py:8`

**Interfaces:**
- Consumes: `cupid_data/cupid_profiles.json`.
- Produces: Bốn tool chạy được với dữ liệu thật.

- [ ] Chạy `get_user_profile("U001")` để xác nhận RED là `FileNotFoundError` tại `cupid_data/profiles.json`.
- [ ] Đổi `"profiles.json"` thành `"cupid_profiles.json"` trong `DATA_FILE`.
- [ ] Chạy `python -c "from src.tools import get_user_profile; assert get_user_profile('U001')['ok']"` và kỳ vọng exit 0.

### Task 2: Đồng bộ test cases

**Files:**
- Modify: `config/test_cases.json`

**Interfaces:**
- Consumes: Tool registry và profile IDs U001/U002/U003/U004/U999.
- Produces: Năm test cases gồm hai LLM-only, một find-match, một three-tool flow và một invalid-profile edge case.

- [ ] Chạy script kiểm tra tên tool trong `expected_behavior`; kỳ vọng RED vì có `search_candidates` và `rank_candidates_by_compatibility`.
- [ ] Viết lại case 3 dùng `find_candidate_matches` và mong đợi U002/U003/U004.
- [ ] Viết lại case 4 dùng `find_candidate_matches`, `calculate_compatibility`, `suggest_first_message` cho U001/U002.
- [ ] Viết case 5 dùng U999 và mong đợi `PROFILE_NOT_FOUND`.
- [ ] Chạy `python -m json.tool config/test_cases.json > /dev/null` và script tool-name check; kỳ vọng exit 0.

### Task 3: Đồng bộ ReAct prompt

**Files:**
- Modify: `src/prompts.py:34-56`

**Interfaces:**
- Consumes: Bốn tool names và JSON argument contracts.
- Produces: `REACT_SYSTEM_PROMPT` chỉ hướng dẫn gọi tool có thật.

- [ ] Chạy script so prompt names với registry; kỳ vọng RED vì prompt còn weather/flight.
- [ ] Thay danh sách tool bằng bốn Cupid tools và các JSON input mẫu.
- [ ] Yêu cầu output theo `Action: find_candidate_matches` + `Action Input: {"user_id": "U001", "limit": 3}` hoặc `Final Answer: Mình đã tìm thấy các ứng viên phù hợp.`.
- [ ] Thêm guardrails không bịa hồ sơ/điểm, không lộ dữ liệu nhạy cảm và xử lý tool error lịch sự.
- [ ] Chạy script prompt-registry check; kỳ vọng exit 0.

### Task 4: Verification tích hợp

**Files:**
- Verify: `src/tools.py`
- Verify: `config/test_cases.json`
- Verify: `src/prompts.py`
- Verify: `cupid_data/cupid_expected_results.json`

**Interfaces:**
- Produces: Bằng chứng top 3, breakdown, opener và error khớp expected results.

- [ ] Chạy `python src/tools.py`.
- [ ] Chạy `python -m py_compile src/tools.py src/prompts.py`.
- [ ] Chạy script so top 3 U001 với U002=90, U003=75, U004=69.
- [ ] Chạy script xác nhận U001/U002 total=90 và U999=`PROFILE_NOT_FOUND`.
- [ ] Chạy `git diff --check` và kiểm tra chỉ các file đã duyệt cùng design spec/plan thay đổi.
