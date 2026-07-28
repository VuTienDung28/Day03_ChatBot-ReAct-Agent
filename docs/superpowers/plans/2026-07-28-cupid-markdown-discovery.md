# Cupid Markdown Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render Baseline/ReAct output as safe Markdown and turn real ReAct matches into a same-page Tinder-like discovery deck with Back, swipe and insight/opener behavior.

**Architecture:** Keep `/api/compare` and Python contracts unchanged. Extend the current vanilla frontend with two hidden screens: Compare stores the latest payload and renders Markdown; Discover reads only `react.matches`, uses a small presentation-only image map, and exposes local pass/select state without backend side effects.

**Tech Stack:** Vanilla JavaScript DOM APIs, Pointer Events, CSS transitions, native `<details>`, Clipboard API, Python `unittest`/HTTP smoke; no Markdown package or frontend framework.

## Global Constraints

- Do not add a Markdown dependency, frontend framework, build tool, database, route, localStorage or server-side session.
- `src/tools.py` remains the only source of matching, ranking, compatibility and opener truth.
- Candidate cards use only `react.matches`; CDN image mapping is presentation-only and has initials fallback.
- Baseline/ReAct output must render safe Markdown without `innerHTML`; HTML, links and images from model output are text only.
- Swipe left means local pass; swipe right means local select and insight/opener display, never a real match or API side effect.
- Swipe threshold is exactly 110px; below threshold snaps back.
- Debug exposes only iteration, action, action_input, observation/error; never Thought or chain-of-thought.
- Back preserves the latest comparison response, segmented view and debug trace.
- Controls are keyboard accessible, at least 48×48px, and honor reduced motion.
- Do not commit or push unless explicitly requested.

---

### Task 1: Safe Markdown renderer

**Files:**
- Test: `tests/test_markdown_renderer.py`
- Modify: `cupid_web/app.js`

**Interfaces:**
- Produces pure `renderMarkdown(text) -> DocumentFragment` and `inlineMarkdown(text) -> DocumentFragment`.
- Consumes string outputs from `data.baseline.answer` and `data.react.answer`.

- [ ] **Step 1: Write failing renderer tests as browser-evaluable JS**

Create a small test fixture contract in `tests/test_markdown_renderer.py` that reads `cupid_web/app.js` and asserts the named functions/guards exist, then use the browser smoke in Task 5 for DOM behavior. The expected behavior is:

```js
const fragment = renderMarkdown('# Title\n\n**bold**\n\n- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n<script>alert(1)</script>');
const host = document.createElement('div');
host.append(fragment);
console.assert(host.querySelector('h1').textContent === 'Title');
console.assert(host.querySelectorAll('li').length === 2);
console.assert(host.querySelector('table'));
console.assert(host.querySelector('script') === null);
console.assert(host.textContent.includes('<script>alert(1)</script>'));
```

- [ ] **Step 2: Run RED**

Run:

```bash
python -m unittest discover -s tests -p "test_markdown_renderer.py" -v
```

Expected: FAIL because `renderMarkdown` is absent.

- [ ] **Step 3: Implement minimal DOM-only renderer**

Add these helpers before result rendering in `cupid_web/app.js`:

```js
function inlineMarkdown(text) {
  const fragment = document.createDocumentFragment();
  for (const [index, part] of String(text).split(/(\*\*[^*]+\*\*)/g).entries()) {
    const strong = part.match(/^\*\*(.+)\*\*$/);
    fragment.append(strong ? node('strong', '', strong[1]) : document.createTextNode(part));
  }
  return fragment;
}

function renderMarkdown(text) {
  const fragment = document.createDocumentFragment();
  const lines = String(text ?? '').split(/\r?\n/);
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    const tableSeparator = index + 1 < lines.length && /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(lines[index + 1]);
    if (line.includes('|') && tableSeparator) {
      const table = node('table');
      const head = node('thead');
      const body = node('tbody');
      const cells = (value) => value.replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim());
      const headerRow = node('tr');
      for (const cell of cells(line)) headerRow.append(node('th', '', cell));
      head.append(headerRow);
      index += 2;
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        const row = node('tr');
        for (const cell of cells(lines[index])) row.append(node('td', '', cell));
        body.append(row);
        index += 1;
      }
      table.append(head, body);
      const wrapper = node('div', 'markdown-table-wrap');
      wrapper.append(table);
      fragment.append(wrapper);
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) { fragment.append(node(`h${heading[1].length}`, '', heading[2])); index += 1; continue; }
    if (/^\s*[-*]\s+/.test(line)) {
      const list = node('ul');
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        const item = node('li'); item.append(inlineMarkdown(lines[index].replace(/^\s*[-*]\s+/, ''))); list.append(item); index += 1;
      }
      fragment.append(list); continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      const list = node('ol');
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        const item = node('li'); item.append(inlineMarkdown(lines[index].replace(/^\s*\d+\.\s+/, ''))); list.append(item); index += 1;
      }
      fragment.append(list); continue;
    }
    const paragraph = node('p'); paragraph.append(inlineMarkdown(line)); fragment.append(paragraph); index += 1;
  }
  return fragment;
}
```

Use only `textContent`/DOM nodes; do not interpret HTML, URLs, images or events.

- [ ] **Step 4: Render answer fields with the new renderer**

Replace:

```js
elements.baselineAnswer.textContent = data.baseline.answer;
elements.reactAnswer.textContent = data.react.answer;
```

with:

```js
elements.baselineAnswer.replaceChildren(renderMarkdown(data.baseline.answer));
elements.reactAnswer.replaceChildren(renderMarkdown(data.react.answer));
```

- [ ] **Step 5: Run GREEN**

Run:

```bash
python -m unittest discover -s tests -p "test_markdown_renderer.py" -v
node --check cupid_web/app.js
```

Expected: PASS and JavaScript syntax exit 0.

---

### Task 2: Compare-to-Discover semantic screens

**Files:**
- Test: `tests/test_cupid_web.py`
- Modify: `cupid_web/index.html`

**Interfaces:**
- Produces DOM IDs: `compare-screen`, `discover-screen`, `discover-button`, `back-to-compare`, `discover-card`, `discover-title`, `discover-progress`, `pass-card`, `select-card`, `discover-live-status`.
- Consumes the existing comparison payload without API changes.

- [ ] **Step 1: Add failing home assertions**

Add to the Flask home test:

```python
for element_id in (
    "compare-screen", "discover-screen", "discover-button", "back-to-compare",
    "discover-card", "discover-title", "discover-progress", "pass-card",
    "select-card", "discover-live-status",
):
    self.assertIn(f'id="{element_id}"', text)
```

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: FAIL because the second screen/CTA is absent.

- [ ] **Step 2: Add Compare CTA and screen wrappers**

Wrap existing composer/comparison/debug layout content in `#compare-screen`, add below the ReAct result area:

```html
<button id="discover-button" class="discover-cta" type="button" hidden>
  Khám phá 3 ứng viên <span aria-hidden="true">→</span>
</button>
```

Keep `#debug-panel` on Compare. The CTA must be hidden initially.

- [ ] **Step 3: Add hidden Discover screen**

Add after Compare screen:

```html
<section id="discover-screen" class="discover-screen" hidden aria-labelledby="discover-title">
  <header class="discover-header">
    <button id="back-to-compare" class="back-button" type="button">← So sánh lại</button>
    <div><p class="eyebrow">Khám phá kết quả Agent</p><h2 id="discover-title">Có 3 hồ sơ để bạn xem xét.</h2></div>
    <span id="discover-progress">0/0</span>
  </header>
  <div class="discover-layout">
    <div class="discover-stage">
      <div id="discover-card" class="discover-card" tabindex="0" aria-label="Hồ sơ đang xem"></div>
      <div class="discover-actions">
        <button id="pass-card" class="discover-action discover-action--pass" type="button" aria-label="Bỏ qua hồ sơ">×</button>
        <p><kbd>←</kbd> bỏ qua <kbd>→</kbd> chọn</p>
        <button id="select-card" class="discover-action discover-action--select" type="button" aria-label="Chọn hồ sơ">♥</button>
      </div>
    </div>
    <aside class="discover-insight" aria-live="polite">
      <p class="eyebrow">Insight</p>
      <div id="discover-insight-content"><p>Chọn một hồ sơ để xem insight.</p></div>
    </aside>
  </div>
  <details id="discover-debug" class="discover-debug">
    <summary>Agent Debug</summary>
    <div id="discover-trace-list"></div>
  </details>
  <p id="discover-live-status" class="visually-hidden" aria-live="polite"></p>
</section>
```

- [ ] **Step 4: Run GREEN for semantic shell**

Run:

```bash
python -m unittest discover -s tests -p "test_cupid_web.py" -v
```

Expected: home/API tests PASS.

---

### Task 3: Two-screen state and CTA/back behavior

**Files:**
- Test: `tests/test_markdown_renderer.py` (static contract assertions)
- Modify: `cupid_web/app.js`

**Interfaces:**
- `enterDiscover()`, `exitDiscover()`, `renderDiscover()`, `showDiscoverInsight()`.
- Consumes `state.data.react.matches`, `state.data.react.compatibility`, `state.data.react.opener`.

- [ ] **Step 1: Add failing JS contract assertions**

Assert `cupid_web/app.js` contains these function names and `discover-button` listeners. Run the existing unittest/static contract and expect FAIL.

- [ ] **Step 2: Add state fields and DOM references**

Extend state:

```js
const state = {
  view: "compare",
  screen: "compare",
  data: null,
  matchIndex: 0,
  resolved: [],
  selectedCandidateId: null,
  loading: false,
  drag: null,
};
```

Add DOM refs for all Discover IDs.

- [ ] **Step 3: Gate/show CTA from real matches**

In `renderComparison(data)`:

```js
const hasMatches = (data.react.matches || []).length > 0;
elements.discoverButton.hidden = !hasMatches;
if (!hasMatches) exitDiscover();
```

Do not show the CTA for safety refusal, provider error or empty matches.

- [ ] **Step 4: Implement same-page navigation**

```js
function enterDiscover() {
  if (!state.data?.react?.matches?.length) return;
  state.screen = "discover";
  state.matchIndex = 0;
  state.resolved = [];
  state.selectedCandidateId = null;
  elements.compareScreen.hidden = true;
  elements.discoverScreen.hidden = false;
  renderDiscover();
  elements.discoverCard.focus();
}

function exitDiscover() {
  state.screen = "compare";
  state.drag = null;
  elements.discoverScreen.hidden = true;
  elements.compareScreen.hidden = false;
  elements.discoverButton.focus();
}
```

CTA click calls `enterDiscover`; Back calls `exitDiscover`. No fetch call occurs during either transition.

- [ ] **Step 5: Run GREEN**

Run:

```bash
node --check cupid_web/app.js
python -m unittest discover -s tests -v
```

Expected: PASS.

---

### Task 4: Tinder-like 3-card deck and insights

**Files:**
- Test: `tests/test_markdown_renderer.py` (static helpers/threshold contract)
- Modify: `cupid_web/app.js`

**Interfaces:**
- Pure `shouldResolve(distance, threshold = 110) -> bool`.
- `resolveDiscoverCard(direction)`, `pointerDown`, `pointerMove`, `pointerUp`.
- Presentation-only `IMAGE_MAP` and initials fallback.

- [ ] **Step 1: Add failing deck self-check contract**

```js
console.assert(shouldResolve(109) === false, "Under threshold must snap back.");
console.assert(shouldResolve(110) === true, "At threshold must resolve.");
```

Static test must assert `110` and `resolveDiscoverCard` exist.

- [ ] **Step 2: Add image map and card rendering**

```js
const IMAGE_MAP = {
  U002: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=960&q=85",
  U003: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=960&q=85",
  U004: "https://images.unsplash.com/photo-1531384441138-2736e62e0919?auto=format&fit=crop&w=960&q=85",
};

function renderDiscover() {
  const matches = state.data.react.matches || [];
  if (state.matchIndex >= matches.length) {
    elements.discoverCard.replaceChildren(node("div", "discover-empty", "Bạn đã xem hết 3 hồ sơ."));
    elements.discoverProgress.textContent = `${matches.length}/${matches.length}`;
    return;
  }
  const match = matches[state.matchIndex];
  const card = node("article", "discover-card-inner");
  const image = document.createElement("img");
  image.src = IMAGE_MAP[match.candidate_id] || "";
  image.alt = `Ảnh minh họa của ${match.name}`;
  image.addEventListener("error", () => card.classList.add("is-fallback"));
  const fallback = node("span", "discover-initials", initialsFor(match.name));
  const wash = node("div", "discover-wash");
  const copy = node("div", "discover-copy");
  copy.append(node("span", "discover-id", match.candidate_id), node("h3", "", match.name), node("strong", "discover-score", `${match.score}%`));
  const reasons = node("ul", "discover-reasons");
  for (const reason of match.reasons || []) reasons.append(node("li", "", reason));
  copy.append(reasons);
  card.append(fallback, image, wash, copy);
  elements.discoverCard.replaceChildren(card);
  elements.discoverCard.setAttribute("aria-label", `${match.name}, tương thích ${match.score}%`);
  elements.discoverProgress.textContent = `${state.matchIndex + 1}/${matches.length}`;
  showDiscoverInsight();
}
```

- [ ] **Step 3: Implement insight/opener behavior**

`showDiscoverInsight()` always renders current candidate name/score/reasons. It renders compatibility/opener only when candidate ID equals the structured result candidate (or response metadata explicitly identifies it); otherwise it renders a CTA text telling the user to return to chat for detailed analysis. Never reuse U002 insight for another ID.

Right select calls:

```js
function resolveDiscoverCard(direction) {
  if (state.animating || !currentDiscoverMatch()) return;
  state.animating = true;
  state.resolved.push({ candidateId: currentDiscoverMatch().candidate_id, direction });
  if (direction === "select") {
    state.selectedCandidateId = currentDiscoverMatch().candidate_id;
    showDiscoverInsight();
  }
  // apply exit class, then advance after reduced-motion-aware timeout
}
```

Right select is local only; no API request or fake match modal.

- [ ] **Step 4: Implement Pointer Events and controls**

- `pointerdown`: store pointerId/startX, capture pointer, add dragging class.
- `pointermove`: translate/rotate; right/left stamp opacity.
- `pointerup`: release capture; `shouldResolve(deltaX)` then resolve or reset.
- `pointercancel`: reset transform/drag.
- buttons call same `resolveDiscoverCard("pass")`/`resolveDiscoverCard("select")`.
- Arrow keys call same functions only when not focused in input/select/textarea.
- Under 110px resets; at 110px resolves.

- [ ] **Step 5: Run GREEN**

Run:

```bash
node --check cupid_web/app.js
python -m unittest discover -s tests -v
```

Expected: PASS.

---

### Task 5: Visual system, Markdown and responsive Discover screen

**Files:**
- Modify: `cupid_web/styles.css`

**Interfaces:**
- Consumes Compare/Discover classes and `data-screen`/hidden states.
- Produces Tinder-like card visuals, Markdown typography, CTA, insight panel, debug drawer and mobile layout.

- [ ] **Step 1: Add Markdown styles**

```css
.markdown-body { color: var(--body); line-height: 1.65; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { color: var(--ink); line-height: 1.15; }
.markdown-body strong { color: var(--ink); font-weight: 800; }
.markdown-body ul, .markdown-body ol { padding-left: 22px; }
.markdown-table-wrap { overflow-x: auto; margin: 16px 0; }
.markdown-body table { min-width: 520px; border-collapse: collapse; }
.markdown-body th, .markdown-body td { padding: 9px 11px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
.markdown-body th { color: var(--ink); background: var(--card); }
```

- [ ] **Step 2: Add Compare CTA and screen layout**

Style CTA as prominent red/ink button below results. Discover screen fills center workspace while debug remains side panel or collapsible drawer.

- [ ] **Step 3: Add Tinder-like card states**

Implement `.discover-card`, `.discover-card-inner`, `.is-dragging`, `.is-exiting-left`, `.is-exiting-right`, `.discover-stamp--pass`, `.discover-stamp--select`, image fallback and dark wash. Keep action buttons at least 48px.

- [ ] **Step 4: Add responsive/accessibility styles**

- Desktop: card center + insight right.
- Tablet/mobile: Back/header → card → controls → insight → debug.
- `.discover-debug` uses `<details>` on mobile.
- `prefers-reduced-motion` removes large rotation/transition.
- Focus-visible styles cover Back, card, actions, CTA and copy.

- [ ] **Step 5: Run CSS checks**

```bash
python - <<'PY'
from pathlib import Path
css = Path('cupid_web/styles.css').read_text(encoding='utf-8')
for token in ('markdown-body', 'discover-screen', 'discover-card-inner', 'is-exiting-left', 'is-exiting-right', '110px', 'prefers-reduced-motion'):
    assert token in css, token
print('DISCOVERY_CSS_OK')
PY
```

Expected: `DISCOVERY_CSS_OK`.

---

### Task 6: Full verification and browser golden path

**Files:**
- Verify: `cupid_web/index.html`, `cupid_web/styles.css`, `cupid_web/app.js`, `cupid_web/server.py`, `tests/*.py`.

**Interfaces:**
- Produces verified Compare → Discover demo.

- [ ] **Step 1: Automated checks**

```bash
python -m unittest discover -s tests -v
python -m py_compile src/app.py src/tools.py src/prompts.py src/providers.py cupid_web/server.py
node --check cupid_web/app.js
git diff --check
```

Expected: all pass.

- [ ] **Step 2: HTTP smoke**

With Flask on port 8000:

```bash
curl -sf http://localhost:8000/ > /dev/null
curl -sf -H "Content-Type: application/json" \
  -d '{"user_id":"U001","message":"Tôi là người dùng U001. Hãy tìm 3 hồ sơ phù hợp nhất với tôi."}' \
  http://localhost:8000/api/compare
```

Expected: API returns matches U002/U003/U004; frontend page contains Compare and Discover IDs.

- [ ] **Step 3: Browser desktop golden path**

Use Playwright/Chrome:

1. Open `http://localhost:8000/` and verify no console/page errors.
2. Click a quick prompt and send.
3. Verify Baseline/ReAct output contains rendered headings/list/table nodes, not raw Markdown markers.
4. Verify CTA appears only after matches.
5. Click CTA; verify Compare hides, Discover focuses card, progress is `1/3`.
6. Drag under 110px and verify card resets; drag at least 110px left and verify progress advances.
7. Reload current response is not required; click Back and verify previous output/trace persists.
8. Enter Discover again, press right/select on U002; verify score/opener insight and no network request.
9. Open Debug and verify only structured trace fields, no `Thought`.

- [ ] **Step 4: Browser mobile golden path**

At a 390px viewport verify one-column order, no horizontal page overflow, 48px controls, Back/CTA focus and Discover details below the card.

- [ ] **Step 5: Scope review**

```bash
git status --short
git diff --stat
```

Expected: only requested frontend/tests/spec/plan changes; do not stage/commit/push.

## Self-review

- Spec coverage: Markdown safety, two screens, CTA/back, exact 110px threshold, pass/select, insight/opener, image fallback, debug, responsive/accessibility and verification are mapped to Tasks 1–6.
- Contract consistency: `react.matches` remains the only deck source; compatibility/opener are candidate-gated.
- No placeholders or new dependency requirements.
