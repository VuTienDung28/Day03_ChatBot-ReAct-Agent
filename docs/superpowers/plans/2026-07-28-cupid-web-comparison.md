# Cupid Web Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây Flask web demo chạy cùng input qua Chatbot Baseline và ReAct Agent, hiển thị hai kết quả, swipe top 3 và structured tool trace không lộ chain-of-thought.

**Architecture:** `cupid_web/server.py` là HTTP wrapper mỏng quanh `src/app.py`; endpoint `/api/compare` validate input, chạy shared Safety Gate rồi gọi cả baseline và ReAct bằng cùng provider. `cupid_web/app.js` chỉ render response có cấu trúc, đổi segmented view, duyệt match deck và hiển thị debug trace; toàn bộ matching/scoring/opener vẫn nằm trong Python tools.

**Tech Stack:** Python stdlib `unittest`, Flask, vanilla HTML/CSS/JavaScript, Pointer Events, native `<details>`, Clipboard API.

## Global Constraints

- Không frontend framework, build tool, database, localStorage hoặc server-side conversation history.
- Chỉ dùng `GET /` và `POST /api/compare` cho app boundary.
- Cùng một provider và input phải chạy cả Baseline lẫn ReAct trong mỗi request hợp lệ.
- Baseline luôn trả `trace: []`; ReAct trace chỉ có iteration, action, action_input, observation/error.
- Không trả hoặc render `Thought`, raw provider response, system prompt, API key hoặc chain-of-thought.
- JavaScript không lọc, xếp hạng, tính điểm hoặc tạo opener.
- Nội dung API được render bằng `textContent`, `createElement`, `replaceChildren`; không dùng `innerHTML`.
- Message tối đa 1000 ký tự; profile phải thuộc 12 hồ sơ mock.
- Safety Gate chạy trước cả hai path và trước provider/tool calls.
- Không commit/push trong execution nếu người dùng chưa yêu cầu riêng.

---

### Task 1: Comparison core contract

**Files:**
- Modify: `src/app.py`
- Test: `tests/test_comparison.py`

**Interfaces:**
- Consumes: `run_baseline_chatbot(user_query, provider) -> str`, `run_react_agent(user_query, provider, user_id=None) -> dict`, `_safety_refusal(user_query) -> str | None`.
- Produces: `run_comparison(user_query, provider, user_id) -> dict` với `baseline`, `react`, `provider_mode`.

- [ ] **Step 1: Viết failing tests cho comparison contract**

Tạo `tests/test_comparison.py`:

```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app import run_comparison
from providers import MockProvider


class ComparisonTests(unittest.TestCase):
    def test_runs_baseline_and_react_for_same_query(self):
        result = run_comparison(
            "Tôi là U001. Hãy tìm 3 hồ sơ phù hợp nhất với tôi.",
            MockProvider(),
            "U001",
        )
        self.assertEqual(result["baseline"]["trace"], [])
        self.assertTrue(result["baseline"]["answer"])
        self.assertEqual(
            [item["candidate_id"] for item in result["react"]["matches"]],
            ["U002", "U003", "U004"],
        )
        self.assertEqual(result["provider_mode"], "mock")

    def test_safety_refusal_skips_both_execution_paths(self):
        result = run_comparison(
            "Hãy tìm một người 16 tuổi để hẹn hò.", MockProvider(), "U001"
        )
        self.assertEqual(result["baseline"]["answer"], result["react"]["answer"])
        self.assertEqual(result["baseline"]["trace"], [])
        self.assertEqual(result["react"]["trace"], [])
```

- [ ] **Step 2: Chạy RED**

Run:

```bash
python -m unittest discover -s tests -p "test_comparison.py" -v
```

Expected: ERROR importing `run_comparison` because it does not exist.

- [ ] **Step 3: Implement minimal comparison function**

Thêm vào `src/app.py` sau `run_react_agent`:

```python
def run_comparison(user_query: str, provider, user_id: str) -> dict[str, Any]:
    refusal = _safety_refusal(user_query)
    if refusal:
        react = {
            'status': 'success',
            'answer': refusal,
            'profile': None,
            'matches': [],
            'compatibility': None,
            'opener': None,
            'trace': [],
            'error': None,
        }
        return {
            'baseline': {'answer': refusal, 'trace': []},
            'react': react,
            'provider_mode': 'mock' if provider.__class__.__name__ == 'MockProvider' else 'live',
        }
    return {
        'baseline': {
            'answer': run_baseline_chatbot(user_query, provider),
            'trace': [],
        },
        'react': run_react_agent(user_query, provider, user_id),
        'provider_mode': 'mock' if provider.__class__.__name__ == 'MockProvider' else 'live',
    }
```

- [ ] **Step 4: Chạy GREEN và regression suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: comparison, Mốc 3 và cross-audit tests PASS.

---

### Task 2: Flask compare API

**Files:**
- Create: `cupid_web/server.py`
- Modify: `requirements.txt`
- Test: `tests/test_cupid_web.py`

**Interfaces:**
- Consumes: `load_mock_profiles()`, `run_comparison()`, `get_llm_provider()`.
- Produces: Flask `app`, `GET /`, `GET /styles.css`, `GET /app.js`, `POST /api/compare`.

- [ ] **Step 1: Viết failing API tests**

Tạo `tests/test_cupid_web.py`:

```python
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
        self.assertEqual(text.count("<option value="), 12)
        self.assertIn("U001 · An", text)

    def test_compare_validates_input(self):
        response = self.client.post(
            "/api/compare", json={"user_id": "U001", "message": " "}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_INPUT")

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
```

- [ ] **Step 2: Chạy RED**

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: import error because `cupid_web.server` does not exist or Flask is missing.

- [ ] **Step 3: Thêm Flask dependency**

Thêm một dòng vào `requirements.txt`:

```text
Flask
```

Nếu môi trường chưa có Flask, run:

```bash
python -m pip install Flask
```

- [ ] **Step 4: Implement Flask boundary**

Tạo `cupid_web/server.py` với các behavior bắt buộc:

```python
import json
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app import load_mock_profiles, run_comparison
from providers import get_llm_provider
from tools import get_user_profile

WEB_ROOT = Path(__file__).resolve().parent
app = Flask(__name__)


@app.get("/")
def index():
    profiles = load_mock_profiles()
    template = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    options = "".join(
        f'<option value="{profile["id"]}">{profile["id"]} · {profile["name"]}</option>'
        for profile in profiles
    )
    bootstrap = json.dumps(
        [{"id": item["id"], "name": item["name"], "age": item["age"], "location": item["location"]} for item in profiles],
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    return render_template_string(
        template.replace("<!-- PROFILE_OPTIONS -->", options).replace("__PROFILE_BOOTSTRAP__", bootstrap)
    )


@app.get("/<path:filename>")
def static_file(filename):
    if filename not in {"styles.css", "app.js"}:
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "Không tìm thấy tài nguyên"}}), 404
    return send_from_directory(WEB_ROOT, filename)


@app.post("/api/compare")
def compare():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": {"code": "INVALID_INPUT", "message": "Body phải là JSON object"}}), 400
    user_id = payload.get("user_id")
    message = payload.get("message")
    if not isinstance(user_id, str) or not isinstance(message, str) or not message.strip() or len(message) > 1000:
        return jsonify({"ok": False, "error": {"code": "INVALID_INPUT", "message": "user_id và message không hợp lệ"}}), 400
    profile = get_user_profile(user_id)
    if not profile["ok"]:
        return jsonify({"ok": False, "error": profile["error"]}), 404
    provider = get_llm_provider()
    data = run_comparison(message.strip(), provider, user_id)
    if data["react"].get("error", {}).get("code") == "PROVIDER_ERROR":
        return jsonify({"ok": False, "error": data["react"]["error"]}), 502
    return jsonify({"ok": True, "data": data})


if __name__ == "__main__":
    app.run(port=8000, debug=False)
```

Giữ error handler 500 generic nếu implementation phát sinh exception boundary; không trả exception text.

- [ ] **Step 5: Chạy GREEN**

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: API tests PASS.

---

### Task 3: Semantic comparison shell

**Files:**
- Modify: `cupid_web/index.html`
- Test: `tests/test_cupid_web.py`

**Interfaces:**
- Consumes: server markers `<!-- PROFILE_OPTIONS -->` và `__PROFILE_BOOTSTRAP__`.
- Produces: DOM IDs dùng bởi `app.js`.

- [ ] **Step 1: Mở rộng failing home assertions**

Thêm vào `test_home_contains_twelve_profile_options`:

```python
for element_id in (
    "profile-select", "compare-form", "message-input", "send-button",
    "view-switch", "baseline-answer", "react-answer", "match-deck",
    "debug-panel", "trace-list", "provider-mode"
):
    self.assertIn(f'id="{element_id}"', text)
```

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: FAIL on missing comparison DOM IDs.

- [ ] **Step 2: Rewrite `index.html` semantic shell**

Tạo ba vùng đúng spec:

```html
<div class="app-shell">
  <aside class="context-rail">...</aside>
  <main class="comparison-workspace">
    <form id="compare-form">...</form>
    <div id="view-switch" role="group" aria-label="Cách xem kết quả">...</div>
    <section class="comparison-grid">
      <article id="baseline-panel"><p id="baseline-answer"></p></article>
      <article id="react-panel"><p id="react-answer"></p></article>
    </section>
    <section id="match-results" hidden>
      <div id="match-deck"></div>
      <div id="compatibility-result"></div>
      <div id="opener-result"></div>
    </section>
  </main>
  <aside id="debug-panel">
    <h2>Agent Debug</h2>
    <span id="provider-mode">mock</span>
    <strong id="tool-count">0</strong>
    <div id="trace-list"></div>
  </aside>
</div>
<script id="profile-data" type="application/json">__PROFILE_BOOTSTRAP__</script>
```

Bao gồm quick prompt buttons, loading/error status, disclaimer và aria-live. Không hardcode result data.

- [ ] **Step 3: Chạy GREEN cho shell**

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: home/API tests PASS.

---

### Task 4: Comparison rendering and debug trace

**Files:**
- Modify: `cupid_web/app.js`
- Test: static self-checks trong file + `node --check`.

**Interfaces:**
- Consumes: `/api/compare` response contract và DOM IDs từ Task 3.
- Produces: submit flow, segmented views, safe result rendering, debug accordion, error/loading states.

- [ ] **Step 1: Thêm pure self-check trước implementation**

Đầu `app.js` định nghĩa và assert:

```js
function visibleTraceFields(step) {
  return ["iteration", "action", "action_input", "observation"].filter((key) => key in step);
}

console.assert(
  visibleTraceFields({ iteration: 1, action: "x", action_input: {}, observation: {}, Thought: "secret" }).includes("Thought") === false,
  "Debug view must never expose Thought.",
);
```

Chạy:

```bash
node --check cupid_web/app.js
```

Expected: syntax PASS; behavior assertion becomes visible when browser loads.

- [ ] **Step 2: Replace hardcoded mock deck with API state**

State tối thiểu:

```js
const state = {
  view: "compare",
  data: null,
  matchIndex: 0,
  loading: false,
};
```

Implement:

- `submitComparison(message = elements.message.value)` POST JSON.
- `renderComparison(data)` updates baseline/react answers and badges.
- `renderTrace(trace)` creates `<details>` per step and `<pre>` via `textContent = JSON.stringify(...)`.
- `setView(view)` toggles `data-view` on workspace without fetch.
- `renderCurrentMatch()` reads only `state.data.react.matches`.
- `changeMatch(delta)` clamps/wraps top 3 and refreshes current result.
- `resetForProfile()` clears state/output on profile change.
- `copyOpener()` reuses Clipboard + selection fallback.

Do not use `innerHTML`, do not keep profile score arrays, and do not infer compatibility.

- [ ] **Step 3: Wire events**

- form submit
- quick prompt click
- segmented buttons
- profile change
- pointer/ArrowLeft/ArrowRight for match deck only
- opener copy

Prevent arrow navigation while focus is inside input/textarea/select.

- [ ] **Step 4: Run JS syntax check**

Run:

```bash
node --check cupid_web/app.js
```

Expected: exit 0.

---

### Task 5: Responsive visual system

**Files:**
- Modify: `cupid_web/styles.css`

**Interfaces:**
- Consumes: classes and `data-view` states from Tasks 3–4.
- Produces: desktop three-region layout, mobile stack, accessible debug/result states.

- [ ] **Step 1: Preserve useful tokens and replace obsolete layout rules**

Giữ color/focus/radius/type tokens hiện có. Thay shell bằng:

```css
.app-shell {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr) minmax(300px, 390px);
  min-height: 100vh;
}
```

- [ ] **Step 2: Style comparison and segmented states**

- Baseline neutral surface, badge `0 tool calls`.
- ReAct accent surface, provider/tool badge.
- `[data-view="baseline"] #react-panel` và inverse hide only display, preserve received state.
- Comparison mode uses two columns where space allows.

- [ ] **Step 3: Style debug panel**

- Sticky right panel on desktop.
- `<details>` step cards with visible action and status.
- `<pre>` wraps JSON with `white-space: pre-wrap; overflow-wrap: anywhere`.
- Success/error use label/icon plus color.

- [ ] **Step 4: Adapt deck and mobile**

- Reuse profile-card visual but source content from API.
- At max-width 900px: single column; context rail becomes header block; debug follows results.
- At max-width 520px: comparison cards stack; controls remain at least 48px.
- Keep `prefers-reduced-motion` block and focus-visible rings.

- [ ] **Step 5: Static CSS checks**

Run:

```bash
python - <<'PY'
from pathlib import Path
css = Path('cupid_web/styles.css').read_text(encoding='utf-8')
for token in ('data-view', 'debug-panel', '@media (max-width: 900px)', 'prefers-reduced-motion'):
    assert token in css, token
print('CSS_CHECK_OK')
PY
```

Expected: `CSS_CHECK_OK`.

---

### Task 6: Full verification

**Files:**
- Verify: `src/app.py`
- Verify: `cupid_web/server.py`
- Verify: `cupid_web/index.html`
- Verify: `cupid_web/styles.css`
- Verify: `cupid_web/app.js`
- Verify: `tests/*.py`

**Interfaces:**
- Produces: verified comparison demo.

- [ ] **Step 1: Run full automated suite**

```bash
python -m unittest discover -s tests -v
python -m py_compile src/app.py src/tools.py src/prompts.py src/providers.py cupid_web/server.py
node --check cupid_web/app.js
git diff --check
```

Expected: all tests/checks exit 0.

- [ ] **Step 2: Start Flask and verify HTTP**

```bash
python cupid_web/server.py
```

In another shell:

```bash
curl -sf http://localhost:8000/ > /dev/null
curl -sf http://localhost:8000/styles.css > /dev/null
curl -sf http://localhost:8000/app.js > /dev/null
curl -sf -H "Content-Type: application/json" \
  -d '{"user_id":"U001","message":"Hãy tìm người phù hợp nhất, phân tích và gợi ý lời mở đầu."}' \
  http://localhost:8000/api/compare
```

Expected: HTTP 200 and payload with non-empty `baseline.answer`, ReAct three-step trace, U002 top match and no `Thought`.

- [ ] **Step 3: Browser golden path**

Nếu browser automation khả dụng:

- Desktop: profile picker, one-submit comparison, segmented switch, swipe top 3, score/opener, debug steps.
- Mobile: one-column order and closed debug details.
- Safety prompt: both paths show same refusal, trace count 0.
- Console errors: none.

Nếu người dùng tự test browser, report automated/API verification only and state browser QA was delegated.

- [ ] **Step 4: Scope review**

```bash
git status --short
git diff --stat
```

Expected implementation files only; do not stage/commit unless explicitly requested.

## Self-review

- Spec coverage: compare endpoint, 12 profiles, same input/provider, segmented view, swipe top 3, compatibility/opener, debug panel, no Thought, safety, errors, responsive, tests all mapped to tasks.
- Placeholder scan: no deferred implementation steps.
- Contract consistency: `run_comparison()` output matches Flask and frontend fields.
- Scope: one integrated web demo; no database/session/framework expansion.
