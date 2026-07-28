# Cupid Web Comparison, Discovery and Mock Chat Design

## 1. Mục tiêu

Web demo có ba giai đoạn trong cùng page:

1. **Compare:** cùng input qua Baseline/ReAct, output Markdown an toàn và structured trace.
2. **Discover:** CTA mở Tinder-like swipe deck từ `react.matches`.
3. **Mock Chat:** sau khi select candidate, người dùng mở thread local, chỉnh opener và nhận scripted reply deterministic.

Mock Chat chỉ minh họa UX. Tin nhắn không gửi ra ngoài, không gọi LLM/API, không tạo tài khoản hoặc lưu qua reload.

## 2. Phạm vi

### Bao gồm

- Flask `GET /` và `POST /api/compare` hiện có.
- Safe Markdown, Compare/Discover flow, exact 110px swipe và candidate-gated insight/opener.
- CTA `Bắt đầu mock chat` sau khi candidate được select.
- Màn Chat thứ ba trong cùng page, Back giữ Discover state.
- Thread riêng theo candidate trong browser memory.
- Opener đúng candidate được prefill để sửa, chưa tự gửi.
- Scripted replies theo U002/U003/U004 và fallback generic.
- Typing indicator, timestamps, local-only banner, composer max 500 ký tự.
- Local safety filter, keyboard/focus/mobile/accessibility tests.

### Không bao gồm

- Chat API, LLM call, websocket, database, localStorage hoặc server history.
- Gửi tin thật, read receipts thật, online presence thật hoặc push notification.
- Markdown/HTML trong chat bubbles.
- Auto-send opener hoặc auto-match.
- Trộn thread giữa candidates.

## 3. Architecture and state

API contract không đổi. State mở rộng:

```js
{
  screen: "compare" | "discover" | "chat",
  view: "compare" | "baseline" | "react",
  data: latestComparisonPayload,
  matchIndex: 0,
  resolved: [],
  selectedCandidateId: null,
  chats: {
    U002: {
      messages: [
        { id: "m1", sender: "user" | "candidate", text: "...", sentAt: "15:42" }
      ],
      replyIndex: 0,
      typing: false
    }
  }
}
```

```text
Compare -> Discover -> select candidate -> insight CTA -> Mock Chat
  ^           ^                                    |
  |           +-------------- Back ----------------+
  +---------------- Back from Discover
```

Mọi state mất khi reload hoặc đổi selected profile. Không persistence.

## 4. Compare and Discover contracts

Giữ nguyên các quy tắc đã duyệt:

- Baseline/ReAct output render bằng safe DOM Markdown parser.
- Discover CTA chỉ có khi `react.matches` không rỗng.
- Swipe deck chỉ dùng matches từ tool, image map là presentation-only.
- Trái = pass; phải = select/insight; không tạo match thật.
- Compatibility/opener chỉ hiện cho đúng candidate.
- Debug không có Thought/chain-of-thought.

## 5. Chat entry

Sau `resolveDiscoverCard("select")`, insight panel cho candidate đó xuất CTA:

```text
Bắt đầu mock chat →
```

CTA chỉ hiện khi `state.selectedCandidateId` khớp candidate đang hiển thị trong insight. Nhấn CTA:

- Gọi `enterChat(candidateId)`.
- Ẩn Discover, hiện Chat; không gọi fetch.
- Tạo thread nếu chưa tồn tại.
- Nếu candidate đúng top candidate và có `react.opener.message`, điền message vào composer.
- Opener chỉ là draft; không thêm bubble cho tới khi user nhấn Send.
- Focus composer.

Candidate không có opener mở composer rỗng.

## 6. Chat screen UI

### Header

- Back button `← Quay lại khám phá`.
- Candidate avatar/image fallback, name và ID.
- Badge `Mock conversation`.

### Conversation

- Banner: `Demo local — tin nhắn không được gửi.`
- Separator đầu thread: `Bạn đã chọn xem insight của {name}.`
- User bubble bên phải, candidate bubble bên trái.
- Timestamp dùng local `HH:mm`, không giả read receipt.
- Empty thread có prompt: `Hãy chỉnh lời mở đầu rồi gửi khi bạn sẵn sàng.`

### Composer

- Textarea `maxlength=500`.
- Character counter.
- Agent suggestion chip khi opener được prefill.
- Send button tối thiểu 48px.
- Enter gửi; Shift+Enter newline.
- Trong lúc candidate typing, Send disabled để tránh nhiều reply chồng nhau.

## 7. Scripted replies

Replies deterministic theo candidate, mỗi thread có `replyIndex`:

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
```

Fallback:

```text
Cảm ơn bạn đã nhắn. Rất vui được làm quen với bạn!
```

Sau user send:

1. Append user bubble.
2. Clear composer/suggestion chip.
3. Set `typing=true`; render three-dot indicator and announce via `aria-live`.
4. Sau khoảng 700ms, append next scripted reply, increment replyIndex, set `typing=false`.
5. Scroll latest message into view; reduced motion dùng instant scroll.

## 8. Back and thread separation

`exitChat()`:

- Clear pending typing timeout or ensure callback is candidate/thread scoped.
- Hide Chat, show Discover.
- Restore deck progress and selected candidate insight.
- Return focus to `Bắt đầu mock chat` CTA.

Mỗi candidate ID có thread riêng. `enterChat("U003")` không thấy messages U002. Replay deck không xóa threads; đổi selected user/profile reset toàn bộ threads.

## 9. Local chat safety

Chat uses plain text only via `textContent`; no Markdown/HTML.

`validateMockMessage(text)` rejects:

- Empty/whitespace.
- Over 500 characters.
- Sexual/coercive terms already used by Safety Gate: `tình dục`, `gây áp lực`, `ép buộc`, `phải đồng ý`.
- Private-contact/location requests: `địa chỉ nhà`, `tọa độ chính xác`, `số điện thoại`.

On rejection:

- Show inline Vietnamese error.
- Do not append bubble.
- Do not trigger scripted reply.
- Preserve draft for editing.

This is demo UX protection, not a claim of comprehensive moderation.

## 10. Accessibility and responsive behavior

- Chat header/composer remains visible without covering messages.
- Conversation has `role="log"`, `aria-live="polite"`, `aria-relevant="additions"`.
- Typing indicator has accessible text `{name} đang nhập…`.
- Enter sends only without Shift; IME composition must not submit.
- Focus enters composer and returns to chat CTA on Back.
- Controls ≥48×48px and clear focus-visible.
- Desktop centers a phone-like chat surface; mobile uses full viewport height.
- Bubbles max width 76%, wrap long words, page never overflows horizontally.
- Reduced motion avoids animated scroll and long typing transitions.

## 11. Error handling

- Missing/invalid selected candidate prevents Chat entry.
- Missing candidate name/image uses ID/initials.
- Opener belongs only to top structured candidate; never prefill another candidate with U002 opener.
- Pending reply cannot write into a different active thread.
- Reload/profile reset clears local messages.
- Clipboard/API/network are not used by mock chat.

## 12. Tests

### Static/unit contracts

- Chat DOM IDs exist.
- `SCRIPTED_REPLIES`, `enterChat`, `exitChat`, `sendMockMessage`, `validateMockMessage` exist.
- No `fetch` inside mock chat functions.
- Chat renderer uses `textContent`, no `innerHTML`.

### Browser golden path

- Select U002 → CTA appears → Chat opens with opener prefilled, no bubble yet.
- Edit/send → user bubble appears, then typing, then U002 scripted reply.
- Enter sends; Shift+Enter newline; composing event does not send.
- Back restores Discover state and insight.
- U003 thread starts empty and does not show U002 messages/opener.
- Re-enter U002 restores U002 thread.
- Safety/empty/501-char message does not create bubble/reply.
- Chat creates no `/api/compare` or other network request.
- Desktop/mobile no overflow and no console errors.

### Regression

- Markdown/Discover 109/110 threshold and candidate-gating tests continue to pass.
- All Python tests, py_compile, node syntax, HTTP and live provider smoke remain green.

## 13. Completion criteria

- Quẹt phải candidate leads naturally from insight to local Mock Chat.
- Opener is editable draft, not auto-sent.
- Deterministic candidate replies make the demo interactive without backend/LLM.
- Threads remain isolated and restore correctly during the page session.
- Local safety, accessibility and mobile behavior pass tests.
- Existing Compare/Discover/debug behavior remains intact.
