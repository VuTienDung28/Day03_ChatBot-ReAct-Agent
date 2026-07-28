# Cupid Web Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây static web demo swipe-card Cupid có responsive layout, match modal và mock data đồng bộ với U002/U003/U004.

**Architecture:** `index.html` giữ semantic shell và controls; `styles.css` thực hiện design tokens, 3-column layout, swipe states và responsive behavior; `app.js` giữ mock profiles cùng state machine render/drag/resolve/modal/reset. Không file nào gọi backend hoặc phụ thuộc code Mốc 3.

**Tech Stack:** HTML5, CSS, vanilla JavaScript, Pointer Events, native `<dialog>`, Python stdlib HTTP server.

## Global Constraints

- Chỉ tạo `cupid_web/index.html`, `cupid_web/styles.css`, `cupid_web/app.js`.
- Không sửa `src/`, `config/` hoặc dependency files.
- Không framework, build tool, package hoặc localStorage.
- Ảnh dùng CDN và phải có fallback initials.
- U002/U003/U004 có điểm 90/75/69.
- Controls tối thiểu 48×48px, hỗ trợ keyboard và reduced motion.
- Không commit/push nếu chưa được yêu cầu.

---

### Task 1: Semantic shell

**Files:**
- Create: `cupid_web/index.html`

**Interfaces:**
- Produces IDs dùng bởi JS: `profile-card`, `next-card`, `profile-image`, `profile-name`, `profile-meta`, `interest-list`, `score-value`, `score-ring`, `breakdown-list`, `shared-list`, `pass-button`, `like-button`, `match-dialog`, `copy-button`, `continue-button`, `reset-button`, `live-status`.

- [ ] Chạy `python -c "from pathlib import Path; assert Path('cupid_web/index.html').exists()"`; kỳ vọng FAIL.
- [ ] Tạo document có `nav`, `main`, `aside`, một visually-hidden `h1`, card stage, action buttons, detail panel, empty state và `<dialog>`.
- [ ] Link `styles.css` và `app.js` bằng relative path.
- [ ] Chạy script xác nhận landmark và IDs duy nhất; kỳ vọng exit 0.

### Task 2: Design system và responsive layout

**Files:**
- Create: `cupid_web/styles.css`

**Interfaces:**
- Consumes: class names trong `index.html`.
- Produces states: `.is-dragging`, `.is-exiting-left`, `.is-exiting-right`, `.is-fallback`, `.is-empty`, `.match-fallback-open`.

- [ ] Chạy kiểm tra file CSS tồn tại; kỳ vọng FAIL.
- [ ] Khai báo tokens màu, spacing, radius 16/32/pill, focus ring và typography.
- [ ] Dựng desktop 3-column, card 440×620, full-bleed image, scrim, action buttons, score panel và dialog.
- [ ] Thêm breakpoints 1024/768/520 và `prefers-reduced-motion`.
- [ ] Chạy script kiểm tra tokens, breakpoints và reduced-motion block; kỳ vọng exit 0.

### Task 3: Mock data và rendering

**Files:**
- Create: `cupid_web/app.js`

**Interfaces:**
- Produces `profiles`, `renderCurrentProfile()`, `renderDetails()`, `showEmptyState()`.

- [ ] Chạy `node --check cupid_web/app.js`; kỳ vọng FAIL vì file chưa tồn tại.
- [ ] Tạo danh sách tối thiểu sáu profiles; U002/U003/U004 phải có score 90/75/69 và ảnh CDN.
- [ ] Thêm `validateProfiles()` kiểm tra required fields, ID unique và score 0–100 khi load.
- [ ] Render card hiện tại, card kế tiếp, detail panel, counters và image fallback initials.
- [ ] Chạy `node --check cupid_web/app.js`; kỳ vọng exit 0.

### Task 4: Swipe state machine

**Files:**
- Modify: `cupid_web/app.js`

**Interfaces:**
- Consumes: DOM IDs và profiles.
- Produces `resolveCard(direction)`, pointer handlers, keyboard handlers và animation lock.

- [ ] Thêm runnable self-check cho pure helper `shouldResolve(distance, threshold)` với 109=false, 110=true; xác nhận FAIL trước khi helper tồn tại.
- [ ] Implement Pointer Events, capture/release, translate/rotate, directional labels và 110px threshold.
- [ ] Nút và ArrowLeft/ArrowRight gọi chung `resolveCard()`.
- [ ] Khóa resolve trong exit animation; pointercancel snap card về vị trí.
- [ ] Chạy `node --check` và self-check helper; kỳ vọng exit 0.

### Task 5: Match modal, copy và reset

**Files:**
- Modify: `cupid_web/app.js`

**Interfaces:**
- Produces `openMatchDialog(profile)`, `closeMatchDialog()`, `copyOpener()`, `resetDeck()`.

- [ ] Thêm assertion opener U002 chứa `du lịch` và match trigger chỉ áp dụng cho U002; xác nhận FAIL trước implementation.
- [ ] Like U002 mở dialog với score/shared/opener; các profile khác chỉ tăng like count.
- [ ] Implement native dialog và class-based overlay fallback.
- [ ] Implement Clipboard API với readonly-field selection fallback.
- [ ] Implement empty state và reset counters/index.
- [ ] Chạy `node --check` và data self-check; kỳ vọng exit 0.

### Task 6: Static và browser verification

**Files:**
- Verify: `cupid_web/index.html`
- Verify: `cupid_web/styles.css`
- Verify: `cupid_web/app.js`

**Interfaces:**
- Produces verified static demo.

- [ ] Chạy `node --check cupid_web/app.js`.
- [ ] Chạy Python HTML/ID/profile assertions.
- [ ] Khởi động `python -m http.server 8000 --directory cupid_web`.
- [ ] Kiểm tra HTTP 200 cho `/`, `/styles.css`, `/app.js`.
- [ ] Mở browser và kiểm tra pass/like, pointer drag, arrow keys, U002 dialog, copy, empty/reset, mobile viewport và console.
- [ ] Chạy `git diff --check` và xác nhận code mới chỉ nằm trong `cupid_web/`.

## Self-review

- Đủ semantic shell, visual system, mock data, swipe, match, fallback, responsive, accessibility và verification.
- Không backend/tool/Flask hoặc dependency mới.
- Function names và DOM IDs nhất quán giữa các task.
- Không có placeholder implementation.
