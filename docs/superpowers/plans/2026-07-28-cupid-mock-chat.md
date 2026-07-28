# Cupid Mock Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third local-only Mock Chat screen after candidate selection, with editable Agent opener, isolated candidate threads and deterministic scripted replies.

**Architecture:** Extend the existing in-memory frontend state machine from `compare | discover` to `compare | discover | chat`. Chat reads the selected candidate and existing ReAct opener, stores messages per candidate in `state.chats`, and never calls fetch/LLM/backend.

**Tech Stack:** Vanilla JavaScript DOM APIs, CSS responsive layout, timers, native textarea/form, Python static-contract tests and Playwright browser verification; no new dependency.

## Global Constraints

- No chat API, websocket, LLM call, database, localStorage, server history or persistence across reload.
- Mock Chat never calls `fetch`; only Compare may call `/api/compare`.
- Chat bubbles are plain text rendered with `textContent`; no Markdown or HTML.
- Opener is prefilled only for the candidate it belongs to and is never auto-sent.
- Threads are isolated by candidate ID and cleared when selected profile changes/reload occurs.
- Scripted replies are deterministic, candidate-specific and local-only.
- Message limit is 500 characters; empty/unsafe messages do not create bubbles or replies.
- Enter sends, Shift+Enter inserts newline, IME composition does not submit.
- Back restores Discover deck/insight/thread state; controls are at least 48×48px and accessible.
- Do not commit or push unless explicitly requested.

---

### Task 1: Mock Chat semantic shell

**Files:**
- Test: `tests/test_cupid_web.py`
- Modify: `cupid_web/index.html`

**Interfaces:**
- Produces IDs: `start-chat`, `chat-screen`, `back-to-discover`, `chat-candidate-name`, `chat-candidate-id`, `chat-avatar`, `chat-log`, `typing-indicator`, `chat-form`, `chat-input`, `chat-count`, `chat-send`, `chat-error`, `agent-suggestion`, `chat-live-status`.

- [ ] **Step 1: Add failing home assertions**

Extend the home ID loop in `tests/test_cupid_web.py`:

```python
for element_id in (
    "start-chat", "chat-screen", "back-to-discover", "chat-candidate-name",
    "chat-candidate-id", "chat-avatar", "chat-log", "typing-indicator",
    "chat-form", "chat-input", "chat-count", "chat-send", "chat-error",
    "agent-suggestion", "chat-live-status",
):
    self.assertIn(f'id="{element_id}"', text)
```

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: FAIL because Chat shell is absent.

- [ ] **Step 2: Add insight CTA hidden by default**

Inside `.discover-insight`, after opener/compatibility containers:

```html
<button id="start-chat" class="start-chat-button" type="button" hidden>
  Bắt đầu mock chat <span aria-hidden="true">→</span>
</button>
```

- [ ] **Step 3: Add hidden Chat screen**

```html
<section id="chat-screen" class="chat-screen" hidden aria-labelledby="chat-candidate-name">
  <header class="chat-header">
    <button id="back-to-discover" class="back-button" type="button">← Quay lại khám phá</button>
    <div class="chat-person">
      <span id="chat-avatar" class="chat-avatar" aria-hidden="true"></span>
      <div><strong id="chat-candidate-name"></strong><span id="chat-candidate-id"></span></div>
    </div>
    <span class="mock-chat-badge">Mock conversation</span>
  </header>
  <p class="local-chat-banner">Demo local — tin nhắn không được gửi.</p>
  <div id="chat-log" class="chat-log" role="log" aria-live="polite" aria-relevant="additions"></div>
  <div id="typing-indicator" class="typing-indicator" hidden aria-live="polite"></div>
  <form id="chat-form" class="chat-composer">
    <span id="agent-suggestion" class="agent-suggestion" hidden>Gợi ý từ Agent</span>
    <label class="visually-hidden" for="chat-input">Tin nhắn mock</label>
    <textarea id="chat-input" maxlength="500" rows="2" placeholder="Nhập tin nhắn…"></textarea>
    <p id="chat-error" class="chat-error" role="alert"></p>
    <div class="chat-composer-footer">
      <span id="chat-count">0/500</span>
      <button id="chat-send" class="primary-button" type="submit">Gửi</button>
    </div>
  </form>
  <p id="chat-live-status" class="visually-hidden" aria-live="polite"></p>
</section>
```

- [ ] **Step 4: Run GREEN**

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: API/home tests PASS.

---

### Task 2: Chat state, candidate entry and opener prefill

**Files:**
- Test: `tests/test_mock_chat.py`
- Modify: `cupid_web/app.js`

**Interfaces:**
- Produces `SCRIPTED_REPLIES`, `chatThread(candidateId)`, `enterChat(candidateId)`, `exitChat()`, `renderChat()`.
- Consumes `state.selectedCandidateId`, `state.data.react.matches`, `state.data.react.opener`.

- [ ] **Step 1: Write failing static contract tests**

Create `tests/test_mock_chat.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MockChatContractTests(unittest.TestCase):
    def test_chat_functions_and_local_state_exist(self):
        source = (ROOT / "cupid_web" / "app.js").read_text(encoding="utf-8")
        for token in (
            "SCRIPTED_REPLIES", "function chatThread", "function enterChat",
            "function exitChat", "function renderChat", "function sendMockMessage",
            "function validateMockMessage",
        ):
            self.assertIn(token, source)
        self.assertIn("chats:", source)

    def test_mock_chat_functions_do_not_fetch(self):
        source = (ROOT / "cupid_web" / "app.js").read_text(encoding="utf-8")
        chat_source = source[source.index("function enterChat"):]
        self.assertNotIn('fetch("', chat_source)
        self.assertNotIn("innerHTML", source)
```

Run and expect FAIL.

- [ ] **Step 2: Extend state and DOM references**

```js
state.chats = {};
state.chatCandidateId = null;
state.chatReplyTimer = null;
```

Add all Chat DOM refs from Task 1 and `startChat`.

- [ ] **Step 3: Add deterministic replies**

```js
const SCRIPTED_REPLIES = {
  U002: [
    "Chào bạn! Mình thích nhất những chuyến đi có nhiều góc đẹp để chụp ảnh. Còn bạn?",
    "Nghe thú vị đó. Gần đây bạn có chuyến đi nào đáng nhớ không?",
  ],
  U003: [
    "Chào bạn! Mình thường bắt đầu buổi sáng bằng một ly cà phê rồi đi chạy bộ.",
    "Bạn hay ghé quán cà phê nào ở Hà Nội?",
  ],
  U004: [
    "Chào bạn! Cà phê và nấu ăn đều là cách mình thư giãn cuối tuần.",
    "Nếu chọn một món để cùng nấu, bạn sẽ chọn món gì?",
  ],
};
const DEFAULT_REPLIES = ["Cảm ơn bạn đã nhắn. Rất vui được làm quen với bạn!"];
```

- [ ] **Step 4: Implement thread and candidate helpers**

```js
function chatCandidate(candidateId = state.chatCandidateId) {
  return state.data?.react?.matches?.find((match) => match.candidate_id === candidateId) || null;
}

function chatThread(candidateId) {
  state.chats[candidateId] ||= { messages: [], replyIndex: 0, typing: false };
  return state.chats[candidateId];
}
```

Use candidate ID as the sole thread key.

- [ ] **Step 5: Gate Chat CTA in insight**

At end of `showDiscoverInsight(match)`:

```js
elements.startChat.hidden = state.selectedCandidateId !== match.candidate_id;
elements.startChat.dataset.candidateId = match.candidate_id;
```

`renderDiscover()` hides CTA until select. Right select calls `showDiscoverInsight(match)` before advancing.

- [ ] **Step 6: Implement enter/exit**

```js
function enterChat(candidateId) {
  const candidate = chatCandidate(candidateId);
  if (!candidate || state.selectedCandidateId !== candidateId) return;
  state.screen = "chat";
  state.chatCandidateId = candidateId;
  elements.discoverScreen.hidden = true;
  elements.chatScreen.hidden = false;
  elements.chatName.textContent = candidate.name;
  elements.chatId.textContent = candidate.candidate_id;
  elements.chatAvatar.textContent = initialsFor(candidate.name);
  const thread = chatThread(candidateId);
  const topCandidateId = state.data.react.matches[0]?.candidate_id;
  if (!thread.messages.length && candidateId === topCandidateId && state.data.react.opener?.message) {
    elements.chatInput.value = state.data.react.opener.message;
    elements.agentSuggestion.hidden = false;
  } else {
    elements.chatInput.value = "";
    elements.agentSuggestion.hidden = true;
  }
  renderChat();
  elements.chatInput.focus();
}

function exitChat() {
  if (state.chatReplyTimer) window.clearTimeout(state.chatReplyTimer);
  const thread = state.chatCandidateId && chatThread(state.chatCandidateId);
  if (thread) thread.typing = false;
  state.chatReplyTimer = null;
  state.screen = "discover";
  elements.chatScreen.hidden = true;
  elements.discoverScreen.hidden = false;
  renderDiscover();
  showDiscoverInsight(chatCandidate(state.chatCandidateId));
  elements.startChat.focus();
}
```

Back preserves messages/thread and deck progress.

- [ ] **Step 7: Run GREEN contract tests**

```bash
python -m unittest discover -s tests -p "test_mock_chat.py" -v
node --check cupid_web/app.js
```

Expected: PASS.

---

### Task 3: Message rendering, validation, send and scripted reply

**Files:**
- Modify: `cupid_web/app.js`
- Test: `tests/test_mock_chat.py`

**Interfaces:**
- `validateMockMessage(text) -> string | null` error message.
- `sendMockMessage()`, `appendMockReply(candidateId)`, `renderChat()`.

- [ ] **Step 1: Add validation static assertions**

Assert source contains max `500`, safety terms, `sender`, `sentAt`, and no HTML rendering.

- [ ] **Step 2: Implement local validation**

```js
function validateMockMessage(text) {
  const value = String(text);
  if (!value.trim()) return "Hãy nhập một tin nhắn.";
  if (value.length > 500) return "Tin nhắn tối đa 500 ký tự.";
  const lower = value.toLowerCase();
  if (["tình dục", "gây áp lực", "ép buộc", "phải đồng ý", "địa chỉ nhà", "tọa độ chính xác", "số điện thoại"].some((term) => lower.includes(term))) {
    return "Tin nhắn này không phù hợp với demo trò chuyện an toàn.";
  }
  return null;
}
```

- [ ] **Step 3: Implement plain-text bubbles**

```js
function messageBubble(message) {
  const row = node("div", `message-row message-row--${message.sender}`);
  const bubble = node("div", "message-bubble");
  bubble.append(node("p", "", message.text), node("time", "", message.sentAt));
  row.append(bubble);
  return row;
}

function renderChat() {
  const thread = chatThread(state.chatCandidateId);
  const candidate = chatCandidate();
  const content = [node("p", "chat-separator", `Bạn đã chọn xem insight của ${candidate.name}.`)];
  if (!thread.messages.length) content.push(node("p", "chat-empty", "Hãy chỉnh lời mở đầu rồi gửi khi bạn sẵn sàng."));
  else content.push(...thread.messages.map(messageBubble));
  elements.chatLog.replaceChildren(...content);
  elements.typing.hidden = !thread.typing;
  elements.typing.textContent = thread.typing ? `${candidate.name} đang nhập…` : "";
  elements.chatSend.disabled = thread.typing;
  elements.chatCount.textContent = `${elements.chatInput.value.length}/500`;
  elements.chatLog.scrollTo({ top: elements.chatLog.scrollHeight, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}
```

Messages use `textContent` through `node()`.

- [ ] **Step 4: Implement send/reply**

```js
function localTime() {
  return new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" }).format(new Date());
}

function sendMockMessage() {
  const error = validateMockMessage(elements.chatInput.value);
  if (error) { elements.chatError.textContent = error; return; }
  const candidateId = state.chatCandidateId;
  const thread = chatThread(candidateId);
  thread.messages.push({ id: crypto.randomUUID(), sender: "user", text: elements.chatInput.value.trim(), sentAt: localTime() });
  elements.chatInput.value = "";
  elements.agentSuggestion.hidden = true;
  elements.chatError.textContent = "";
  thread.typing = true;
  renderChat();
  state.chatReplyTimer = window.setTimeout(() => appendMockReply(candidateId), 700);
}

function appendMockReply(candidateId) {
  const thread = chatThread(candidateId);
  const replies = SCRIPTED_REPLIES[candidateId] || DEFAULT_REPLIES;
  const text = replies[Math.min(thread.replyIndex, replies.length - 1)];
  thread.messages.push({ id: crypto.randomUUID(), sender: "candidate", text, sentAt: localTime() });
  thread.replyIndex += 1;
  thread.typing = false;
  state.chatReplyTimer = null;
  if (state.screen === "chat" && state.chatCandidateId === candidateId) renderChat();
}
```

Timer is candidate-scoped and cannot write into another thread.

- [ ] **Step 5: Wire form/keyboard**

- form submit prevents default and calls `sendMockMessage()`.
- input updates counter, clears error, hides suggestion when user edits away from exact opener.
- keydown: Enter without Shift and without `event.isComposing` sends; Shift+Enter remains newline.
- start-chat click reads dataset candidate ID; Back calls `exitChat()`.

- [ ] **Step 6: Reset behavior**

`resetForProfile()` clears `state.chats`, `chatCandidateId`, timer and Chat screen. Replay deck does not clear chat threads.

- [ ] **Step 7: Run automated checks**

```bash
python -m unittest discover -s tests -v
node --check cupid_web/app.js
git diff --check
```

Expected: PASS.

---

### Task 4: Chat visual system and responsive behavior

**Files:**
- Modify: `cupid_web/styles.css`

**Interfaces:**
- Produces full-height Chat screen, bubbles, composer, typing indicator and mobile layout.

- [ ] **Step 1: Add desktop Chat layout**

```css
.chat-screen { min-height: 100vh; max-width: 980px; margin: 0 auto; padding: 22px; display: grid; grid-template-rows: auto auto minmax(280px, 1fr) auto auto; }
.chat-header { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; }
.chat-person { display: flex; align-items: center; gap: 12px; justify-self: center; }
.chat-avatar { display: grid; place-items: center; width: 48px; aspect-ratio: 1; border-radius: 50%; color: white; background: var(--ink); font-weight: 800; }
.mock-chat-badge { justify-self: end; }
.local-chat-banner { margin: 18px 0 0; padding: 10px; border-radius: 12px; color: var(--muted); background: var(--card); text-align: center; }
.chat-log { min-height: 360px; max-height: calc(100vh - 300px); overflow-y: auto; padding: 24px 8px; }
.message-row { display: flex; margin-top: 10px; }
.message-row--user { justify-content: flex-end; }
.message-bubble { max-width: 76%; padding: 11px 14px; border-radius: 18px; background: var(--card); overflow-wrap: anywhere; }
.message-row--user .message-bubble { color: white; background: var(--accent); border-bottom-right-radius: 5px; }
.message-row--candidate .message-bubble { border-bottom-left-radius: 5px; }
.message-bubble p { margin-bottom: 4px; white-space: pre-wrap; }
.message-bubble time { display: block; font-size: 11px; opacity: .72; text-align: right; }
```

- [ ] **Step 2: Style typing/composer**

Typing indicator has three CSS dots plus visually available text. Composer uses sticky visual placement at bottom without covering log; textarea and Send remain accessible. Suggestion chip is clearly marked and removable by editing.

- [ ] **Step 3: Add mobile rules**

At max-width 600px:

- Chat screen uses `min-height: 100dvh`, compact padding.
- Header grid wraps with Back and badge; candidate remains visible.
- Chat log max height adapts.
- Bubble max width 84%.
- Composer footer and send stay reachable; no horizontal overflow.

- [ ] **Step 4: CSS static check**

```bash
python - <<'PY'
from pathlib import Path
css = Path('cupid_web/styles.css').read_text(encoding='utf-8')
for token in ('chat-screen', 'chat-log', 'message-row--user', 'typing-indicator', 'agent-suggestion', '100dvh', 'overflow-wrap'):
    assert token in css, token
print('MOCK_CHAT_CSS_OK')
PY
```

Expected: PASS.

---

### Task 5: Browser verification

**Files:**
- Verify all frontend/tests.

- [ ] **Step 1: Full automated suite**

```bash
python -m unittest discover -s tests -v
python -m py_compile src/app.py src/tools.py src/prompts.py src/providers.py cupid_web/server.py
node --check cupid_web/app.js
git diff --check
```

- [ ] **Step 2: Playwright deterministic fixture flow**

Verify:

1. Compare fixture → Discover CTA → select U002.
2. `start-chat` appears only after select.
3. Enter Chat: opener prefilled, suggestion visible, no bubbles yet, no new network call.
4. Edit/send: user bubble, typing indicator, then U002 scripted reply.
5. Back: deck progress/insight preserved.
6. Select/chat U003: thread empty and no U002 opener/messages.
7. Re-enter U002: U002 thread restored.
8. Empty, unsafe and over-limit messages produce no bubble/reply.
9. Enter/Shift+Enter/IME behavior.
10. No console errors or page overflow desktop/mobile.

- [ ] **Step 3: Live regression smoke**

Confirm Flask/Nemotron Compare still returns successful payload and Chat navigation itself makes no additional request.

- [ ] **Step 4: Scope review**

```bash
git status --short
git diff --stat
```

Do not commit/push.

## Self-review

- Covers semantic shell, local state, opener gating, scripted replies, validation, thread isolation, timer scoping, keyboard/IME, responsive/accessibility and browser tests.
- No backend/API/dependency expansion.
- No placeholders or unrequested persistence.
