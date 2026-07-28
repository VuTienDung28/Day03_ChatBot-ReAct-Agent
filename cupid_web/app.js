"use strict";

const IMAGE_MAP = {
  U001: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=960&q=85",
  U002: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=960&q=85",
  U003: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=960&q=85",
  U004: "https://images.unsplash.com/photo-1531384441138-2736e62e0919?auto=format&fit=crop&w=960&q=85",
  U005: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=960&q=85",
  U006: "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?auto=format&fit=crop&w=960&q=85",
  U007: "https://images.unsplash.com/photo-1527980965255-d3b416303d12?auto=format&fit=crop&w=960&q=85",
  U008: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=960&q=85",
  U009: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=960&q=85",
  U010: "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=960&q=85",
  U011: "https://images.unsplash.com/photo-1507591064344-4c6ce005b128?auto=format&fit=crop&w=960&q=85",
  U012: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=960&q=85",
};

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

function visibleTraceFields(step) {
  return ["iteration", "action", "action_input", "observation"].filter((key) => key in step);
}

function shouldResolve(distance, threshold = 110) {
  return Math.abs(distance) >= threshold;
}

console.assert(!visibleTraceFields({ Thought: "secret" }).includes("Thought"), "Debug must not expose Thought.");
console.assert(!shouldResolve(109) && shouldResolve(110), "Swipe threshold must be exactly 110px.");

const profiles = JSON.parse(document.querySelector("#profile-data").textContent);
const state = {
  view: "compare",
  screen: "compare",
  data: null,
  matchIndex: 0,
  resolved: [],
  selectedCandidateId: null,
  loading: false,
  animating: false,
  drag: null,
  chats: {},
  chatCandidateId: null,
  chatReplyTimer: null,
};

const elements = {
  compareScreen: document.querySelector("#compare-screen"),
  discoverScreen: document.querySelector("#discover-screen"),
  themeToggle: document.querySelector("#theme-toggle"),
  themeColor: document.querySelector('meta[name="theme-color"]'),
  workspace: document.querySelector("#comparison-workspace"),
  profile: document.querySelector("#profile-select"),
  profileAvatar: document.querySelector("#profile-avatar"),
  profileSummary: document.querySelector("#profile-summary"),
  form: document.querySelector("#compare-form"),
  message: document.querySelector("#message-input"),
  send: document.querySelector("#send-button"),
  count: document.querySelector("#character-count"),
  error: document.querySelector("#request-error"),
  comparisonStatus: document.querySelector("#comparison-status"),
  switch: document.querySelector("#view-switch"),
  baselineAnswer: document.querySelector("#baseline-answer"),
  reactAnswer: document.querySelector("#react-answer"),
  reactBadge: document.querySelector("#react-tool-badge"),
  providerMode: document.querySelector("#provider-mode"),
  toolCount: document.querySelector("#tool-count"),
  traceList: document.querySelector("#trace-list"),
  discoverButton: document.querySelector("#discover-button"),
  back: document.querySelector("#back-to-compare"),
  discoverTitle: document.querySelector("#discover-title"),
  discoverProgress: document.querySelector("#discover-progress"),
  discoverCard: document.querySelector("#discover-card"),
  pass: document.querySelector("#pass-card"),
  select: document.querySelector("#select-card"),
  discoverInsight: document.querySelector("#discover-insight-content"),
  selectedCandidateContext: document.querySelector("#selected-candidate-context"),
  selectedCandidateAvatar: document.querySelector("#selected-candidate-avatar"),
  selectedCandidateName: document.querySelector("#selected-candidate-name"),
  selectedCandidateId: document.querySelector("#selected-candidate-id"),
  discoverTrace: document.querySelector("#discover-trace-list"),
  discoverToolCount: document.querySelector("#discover-tool-count"),
  replay: document.querySelector("#replay-deck"),
  compatibility: document.querySelector("#compatibility-result"),
  opener: document.querySelector("#opener-result"),
  openerText: document.querySelector("#opener-text"),
  copyOpener: document.querySelector("#copy-opener"),
  copyStatus: document.querySelector("#copy-status"),
  discoverLiveStatus: document.querySelector("#discover-live-status"),
  startChat: document.querySelector("#start-chat"),
  chatScreen: document.querySelector("#chat-screen"),
  backToDiscover: document.querySelector("#back-to-discover"),
  chatName: document.querySelector("#chat-candidate-name"),
  chatId: document.querySelector("#chat-candidate-id"),
  chatAvatar: document.querySelector("#chat-avatar"),
  chatLog: document.querySelector("#chat-log"),
  typing: document.querySelector("#typing-indicator"),
  chatForm: document.querySelector("#chat-form"),
  chatInput: document.querySelector("#chat-input"),
  chatCount: document.querySelector("#chat-count"),
  chatSend: document.querySelector("#chat-send"),
  chatError: document.querySelector("#chat-error"),
  suggestion: document.querySelector("#agent-suggestion"),
  chatLiveStatus: document.querySelector("#chat-live-status"),
  liveStatus: document.querySelector("#live-status"),
};

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function storedTheme() {
  try {
    const theme = localStorage.getItem("cupid-theme");
    return theme === "light" || theme === "dark" ? theme : null;
  } catch {
    return null;
  }
}

function applyTheme(theme) {
  const selected = theme === "light" || theme === "dark" ? theme : null;
  if (selected) document.documentElement.dataset.theme = selected;
  else delete document.documentElement.dataset.theme;
  const dark = selected ? selected === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  elements.themeToggle.setAttribute("aria-pressed", String(dark));
  const label = dark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối";
  elements.themeToggle.setAttribute("aria-label", label);
  elements.themeToggle.title = label;
  elements.themeColor.content = dark ? "#121012" : "#f8f8f7";
}

function saveTheme(theme) {
  try {
    localStorage.setItem("cupid-theme", theme);
  } catch {
    // Theme still applies for this page when storage is unavailable.
  }
}

function renderAvatar(target, profileId, name) {
  target.textContent = initialsFor(name);
  const source = IMAGE_MAP[profileId];
  if (!source) return;
  const image = document.createElement("img");
  image.src = source;
  image.alt = "";
  image.addEventListener("error", () => image.remove());
  target.append(image);
}

function inlineMarkdown(text) {
  const fragment = document.createDocumentFragment();
  for (const part of String(text).split(/(\*\*[^*]+\*\*)/g)) {
    const strong = part.match(/^\*\*(.+)\*\*$/);
    fragment.append(strong ? node("strong", "", strong[1]) : document.createTextNode(part));
  }
  return fragment;
}

function renderMarkdown(text) {
  const fragment = document.createDocumentFragment();
  const lines = String(text ?? "").split(/\r?\n/);
  const cells = (value) => value.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    const separator = index + 1 < lines.length && /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(lines[index + 1]);
    if (line.includes("|") && separator) {
      const table = node("table");
      const head = node("thead");
      const body = node("tbody");
      const header = node("tr");
      for (const cell of cells(line)) header.append(node("th", "", cell));
      head.append(header);
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        const row = node("tr");
        for (const cell of cells(lines[index])) row.append(node("td", "", cell));
        body.append(row);
        index += 1;
      }
      table.append(head, body);
      const wrapper = node("div", "markdown-table-wrap");
      wrapper.append(table);
      fragment.append(wrapper);
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const title = node(`h${heading[1].length}`);
      title.append(inlineMarkdown(heading[2]));
      fragment.append(title);
      index += 1;
      continue;
    }
    const listType = /^\s*[-*]\s+/.test(line) ? "ul" : /^\s*\d+\.\s+/.test(line) ? "ol" : null;
    if (listType) {
      const list = node(listType);
      const pattern = listType === "ul" ? /^\s*[-*]\s+/ : /^\s*\d+\.\s+/;
      while (index < lines.length && pattern.test(lines[index])) {
        const item = node("li");
        item.append(inlineMarkdown(lines[index].replace(pattern, "")));
        list.append(item);
        index += 1;
      }
      fragment.append(list);
      continue;
    }
    const paragraph = node("p");
    paragraph.append(inlineMarkdown(line));
    fragment.append(paragraph);
    index += 1;
  }
  return fragment;
}

function selectedProfile() {
  return profiles.find((profile) => profile.id === elements.profile.value);
}

function currentDiscoverMatch() {
  return state.data?.react?.matches?.[state.matchIndex] || null;
}

function initialsFor(name) {
  return name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function updateProfileSummary() {
  const profile = selectedProfile();
  elements.profileSummary.textContent = profile ? `${profile.name}\n${profile.age} tuổi | ${profile.location}` : "";
  if (profile) renderAvatar(elements.profileAvatar, profile.id, profile.name);
}

function pendingAnswer(label) {
  const wrap = node("div", "pending-answer");
  wrap.append(node("span", "visually-hidden", label));
  for (const width of ["84%", "68%", "92%", "54%"]) {
    const line = node("span", "pending-line");
    line.style.width = width;
    wrap.append(line);
  }
  return wrap;
}

function renderPendingComparison() {
  elements.baselineAnswer.replaceChildren(pendingAnswer("Baseline đang chuẩn bị câu trả lời."));
  elements.reactAnswer.replaceChildren(pendingAnswer("ReAct Agent đang phân tích yêu cầu."));
}

function renderComparisonError() {
  const message = "Không thể chuẩn bị câu trả lời. Hãy kiểm tra kết nối và thử lại.";
  elements.baselineAnswer.replaceChildren(node("p", "answer-error", message));
  elements.reactAnswer.replaceChildren(node("p", "answer-error", message));
}

function setLoading(value) {
  state.loading = value;
  elements.workspace.setAttribute("aria-busy", String(value));
  elements.send.disabled = value;
  elements.profile.disabled = value;
  for (const button of document.querySelectorAll(".quick-prompt")) button.disabled = value;
  elements.send.textContent = value ? "Đang so sánh..." : "So sánh hai chế độ";
  if (value) {
    elements.comparisonStatus.textContent = "Đang chuẩn bị hai câu trả lời.";
    renderPendingComparison();
    elements.liveStatus.textContent = "Đang chạy Chatbot Baseline và ReAct Agent.";
  }
}

function setView(view) {
  state.view = view;
  elements.workspace.dataset.view = view;
  for (const button of elements.switch.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.dataset.view === view));
  }
}

function renderJson(label, value) {
  const group = node("div", "trace-json");
  group.append(node("span", "trace-label", label));
  const pre = node("pre");
  pre.textContent = JSON.stringify(value, null, 2);
  group.append(pre);
  return group;
}

function traceNodes(trace) {
  return trace.map((step) => {
    const details = node("details", "trace-step");
    const summary = node("summary");
    summary.append(
      node("span", "trace-index", `0${step.iteration}`.slice(-2)),
      node("strong", "", step.action),
      node("span", step.observation?.ok ? "trace-status is-success" : "trace-status is-error", step.observation?.ok ? "Thành công" : "Lỗi"),
    );
    details.append(summary, renderJson("Action Input", step.action_input), renderJson("Observation", step.observation));
    return details;
  });
}

function renderTrace(trace) {
  elements.toolCount.textContent = String(trace.length);
  elements.discoverToolCount.textContent = String(trace.length);
  elements.reactBadge.textContent = `${trace.length} tool call${trace.length === 1 ? "" : "s"}`;
  const content = trace.length ? traceNodes(trace) : [node("p", "trace-empty", "Không có tool call cho yêu cầu này.")];
  elements.traceList.replaceChildren(...content);
  elements.discoverTrace.replaceChildren(...traceNodes(trace));
}

function renderCompatibility(compatibility) {
  if (!compatibility) { elements.compatibility.hidden = true; elements.compatibility.replaceChildren(); return; }
  const heading = node("div", "detail-heading");
  heading.append(node("h3", "", "Phân tích tương thích"), node("strong", "detail-score", `${compatibility.total_score}%`));
  const list = node("div", "breakdown-list");
  const labels = { relationship_goal: "Mục tiêu", values: "Giá trị", interests: "Sở thích", location: "Vị trí" };
  for (const [key, value] of Object.entries(compatibility.breakdown || {})) {
    const row = node("div", "breakdown-item");
    const top = node("div", "breakdown-top");
    top.append(node("span", "", labels[key] || key), node("strong", "", `${value}%`));
    const meter = node("div", "meter");
    const fill = node("span");
    fill.style.setProperty("--value", value / 100);
    meter.append(fill);
    row.append(top, meter);
    list.append(row);
  }
  const shared = node("div", "shared-list");
  for (const item of [...(compatibility.shared_interests || []), ...(compatibility.shared_values || [])]) shared.append(node("span", "shared-chip", item));
  elements.compatibility.replaceChildren(heading, list, shared);
  elements.compatibility.hidden = false;
}

function renderOpener(opener) {
  if (!opener?.message) { elements.opener.hidden = true; elements.openerText.value = ""; return; }
  elements.openerText.value = opener.message;
  elements.copyStatus.textContent = "";
  elements.opener.hidden = false;
}

function renderSelectedCandidate(match) {
  elements.selectedCandidateContext.hidden = !match;
  if (!match) {
    elements.selectedCandidateAvatar.textContent = "";
    elements.selectedCandidateName.textContent = "";
    elements.selectedCandidateId.textContent = "";
    return;
  }
  renderAvatar(elements.selectedCandidateAvatar, match.candidate_id, match.name);
  elements.selectedCandidateName.textContent = match.name;
  elements.selectedCandidateId.textContent = `${match.candidate_id} | ${match.score}% tương thích`;
}

function showDiscoverInsight(match = currentDiscoverMatch()) {
  if (!match) return;
  renderSelectedCandidate(match);
  const heading = node("div", "insight-heading");
  heading.append(node("h3", "", "Lý do phù hợp"));
  const reasons = node("ul", "insight-reasons");
  for (const reason of match.reasons || []) reasons.append(node("li", "", reason));
  elements.discoverInsight.replaceChildren(heading, reasons);

  const topCandidateId = state.data?.react?.matches?.[0]?.candidate_id;
  if (match.candidate_id === topCandidateId && state.data.react.compatibility) {
    renderCompatibility(state.data.react.compatibility);
    renderOpener(state.data.react.opener);
  } else {
    renderCompatibility(null);
    renderOpener(null);
    elements.discoverInsight.append(node("p", "insight-hint", `Chưa có phân tích chi tiết cho hồ sơ này. Quay lại chat và yêu cầu Agent phân tích ${match.candidate_id}.`));
  }
  elements.startChat.hidden = state.selectedCandidateId !== match.candidate_id;
  elements.startChat.dataset.candidateId = match.candidate_id;
}

function renderDiscover() {
  const matches = state.data?.react?.matches || [];
  elements.replay.hidden = true;
  if (state.matchIndex >= matches.length) {
    elements.discoverCard.replaceChildren(
      node("div", "discover-empty", `Bạn đã xem hết ${matches.length} hồ sơ. Đã chọn ${state.resolved.filter((item) => item.direction === "select").length} người.`),
    );
    elements.discoverProgress.textContent = `${matches.length}/${matches.length}`;
    elements.replay.hidden = false;
    elements.pass.disabled = true;
    elements.select.disabled = true;
    return;
  }

  const match = matches[state.matchIndex];
  const card = node("article", "discover-card-inner");
  const fallback = node("span", "discover-initials", initialsFor(match.name));
  const image = document.createElement("img");
  image.src = IMAGE_MAP[match.candidate_id] || "";
  image.alt = `Ảnh minh họa của ${match.name}`;
  image.addEventListener("error", () => card.classList.add("is-fallback"));
  const wash = node("div", "discover-wash");
  const passStamp = node("span", "discover-stamp discover-stamp--pass", "BỎ QUA");
  const selectStamp = node("span", "discover-stamp discover-stamp--select", "XEM INSIGHT");
  const copy = node("div", "discover-copy");
  const titleRow = node("div", "discover-title-row");
  titleRow.append(node("h3", "", match.name), node("strong", "discover-score", `${match.score}%`));
  const reasons = node("ul", "discover-reasons");
  for (const reason of match.reasons || []) reasons.append(node("li", "", reason));
  copy.append(node("span", "discover-id", match.candidate_id), titleRow, reasons);
  card.append(fallback, image, wash, passStamp, selectStamp, copy);
  elements.discoverCard.replaceChildren(card);
  elements.discoverCard.setAttribute("aria-label", `${match.name}, tương thích ${match.score}%, hồ sơ ${state.matchIndex + 1} trên ${matches.length}`);
  elements.discoverProgress.textContent = `${state.matchIndex + 1}/${matches.length}`;
  elements.pass.disabled = false;
  elements.select.disabled = false;
}

function enterDiscover() {
  if (!state.data?.react?.matches?.length) return;
  state.screen = "discover";
  state.matchIndex = 0;
  state.resolved = [];
  state.selectedCandidateId = null;
  state.animating = false;
  state.drag = null;
  elements.startChat.hidden = true;
  renderSelectedCandidate(null);
  elements.discoverInsight.replaceChildren(node("p", "insight-empty", "Chọn một hồ sơ để xem phân tích."));
  elements.compareScreen.hidden = true;
  elements.discoverScreen.hidden = false;
  elements.discoverTitle.textContent = `Có ${state.data.react.matches.length} hồ sơ để bạn xem xét.`;
  renderDiscover();
  elements.discoverCard.focus();
  elements.liveStatus.textContent = "Đã mở màn khám phá ứng viên.";
}

function exitDiscover() {
  state.screen = "compare";
  state.drag = null;
  state.animating = false;
  elements.discoverScreen.hidden = true;
  elements.compareScreen.hidden = false;
  if (!elements.discoverButton.hidden) elements.discoverButton.focus();
}

function chatCandidate(candidateId = state.chatCandidateId) {
  return state.data?.react?.matches?.find((match) => match.candidate_id === candidateId) || null;
}

function chatThread(candidateId) {
  state.chats[candidateId] ||= { messages: [], replyIndex: 0, typing: false };
  return state.chats[candidateId];
}

function localTime() {
  return new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" }).format(new Date());
}

function messageId() {
  return globalThis.crypto?.randomUUID?.() || `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function validateMockMessage(text) {
  const value = String(text);
  if (!value.trim()) return "Hãy nhập một tin nhắn.";
  if (value.length > 500) return "Tin nhắn tối đa 500 ký tự.";
  const lower = value.toLowerCase();
  const unsafe = ["tình dục", "gây áp lực", "ép buộc", "phải đồng ý", "địa chỉ nhà", "tọa độ chính xác", "số điện thoại"];
  if (unsafe.some((term) => lower.includes(term))) return "Tin nhắn này không phù hợp với demo trò chuyện an toàn.";
  return null;
}

function messageBubble(message) {
  const row = node("div", `message-row message-row--${message.sender}`);
  const bubble = node("div", "message-bubble");
  bubble.append(node("p", "", message.text), node("time", "", message.sentAt));
  row.append(bubble);
  return row;
}

function renderChat() {
  const candidate = chatCandidate();
  if (!candidate) return;
  const thread = chatThread(candidate.candidate_id);
  const content = [node("p", "chat-separator", `Bạn đã chọn xem insight của ${candidate.name}.`)];
  if (!thread.messages.length) content.push(node("p", "chat-empty", "Hãy chỉnh lời mở đầu rồi gửi khi bạn sẵn sàng."));
  else content.push(...thread.messages.map(messageBubble));
  elements.chatLog.replaceChildren(...content);
  elements.typing.hidden = !thread.typing;
  elements.typing.textContent = thread.typing ? `${candidate.name} đang nhập…` : "";
  elements.chatSend.disabled = thread.typing;
  elements.chatCount.textContent = `${elements.chatInput.value.length}/500`;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  elements.chatLog.scrollTo({ top: elements.chatLog.scrollHeight, behavior: reduced ? "auto" : "smooth" });
}

function enterChat(candidateId) {
  const candidate = chatCandidate(candidateId);
  if (!candidate || state.selectedCandidateId !== candidateId) return;
  state.screen = "chat";
  state.chatCandidateId = candidateId;
  elements.discoverScreen.hidden = true;
  elements.chatScreen.hidden = false;
  elements.chatName.textContent = candidate.name;
  elements.chatId.textContent = candidate.candidate_id;
  renderAvatar(elements.chatAvatar, candidate.candidate_id, candidate.name);
  const thread = chatThread(candidateId);
  const topCandidateId = state.data.react.matches[0]?.candidate_id;
  if (!thread.messages.length && candidateId === topCandidateId && state.data.react.opener?.message) {
    elements.chatInput.value = state.data.react.opener.message;
    elements.suggestion.hidden = false;
  } else {
    elements.chatInput.value = "";
    elements.suggestion.hidden = true;
  }
  elements.chatError.textContent = "";
  renderChat();
  elements.chatInput.focus();
}

function exitChat() {
  if (state.chatReplyTimer) window.clearTimeout(state.chatReplyTimer);
  const thread = state.chatCandidateId ? chatThread(state.chatCandidateId) : null;
  if (thread) thread.typing = false;
  state.chatReplyTimer = null;
  state.screen = "discover";
  elements.chatScreen.hidden = true;
  elements.discoverScreen.hidden = false;
  renderDiscover();
  const candidate = chatCandidate(state.chatCandidateId);
  if (candidate) showDiscoverInsight(candidate);
  elements.startChat.focus();
}

function appendMockReply(candidateId) {
  const thread = chatThread(candidateId);
  const replies = SCRIPTED_REPLIES[candidateId] || DEFAULT_REPLIES;
  const text = replies[Math.min(thread.replyIndex, replies.length - 1)];
  thread.messages.push({ id: messageId(), sender: "candidate", text, sentAt: localTime() });
  thread.replyIndex += 1;
  thread.typing = false;
  state.chatReplyTimer = null;
  if (state.screen === "chat" && state.chatCandidateId === candidateId) renderChat();
}

function sendMockMessage() {
  const error = validateMockMessage(elements.chatInput.value);
  if (error) {
    elements.chatError.textContent = error;
    return;
  }
  const candidateId = state.chatCandidateId;
  const thread = chatThread(candidateId);
  thread.messages.push({ id: messageId(), sender: "user", text: elements.chatInput.value.trim(), sentAt: localTime() });
  elements.chatInput.value = "";
  elements.suggestion.hidden = true;
  elements.chatError.textContent = "";
  thread.typing = true;
  renderChat();
  elements.chatLiveStatus.textContent = `${chatCandidate(candidateId).name} đang nhập.`;
  state.chatReplyTimer = window.setTimeout(() => appendMockReply(candidateId), 700);
}

function resetCardPosition() {
  state.drag = null;
  const card = elements.discoverCard.firstElementChild;
  if (!card) return;
  card.classList.remove("is-dragging");
  card.style.removeProperty("transform");
  for (const stamp of card.querySelectorAll(".discover-stamp")) stamp.style.opacity = "0";
}

function resolveDiscoverCard(direction) {
  const match = currentDiscoverMatch();
  if (!match || state.animating) return;
  state.animating = true;
  state.drag = null;
  state.resolved.push({ candidateId: match.candidate_id, direction });
  if (direction === "select") {
    state.selectedCandidateId = match.candidate_id;
    showDiscoverInsight(match);
  }
  const card = elements.discoverCard.firstElementChild;
  card?.classList.add(direction === "select" ? "is-exiting-right" : "is-exiting-left");
  elements.discoverLiveStatus.textContent = direction === "select" ? `Đã chọn ${match.name} để xem insight.` : `Đã bỏ qua ${match.name}.`;
  const delay = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 10 : 230;
  window.setTimeout(() => {
    state.matchIndex += 1;
    state.animating = false;
    renderDiscover();
  }, delay);
}

function pointerDown(event) {
  if (state.animating || event.button > 0 || !currentDiscoverMatch()) return;
  state.drag = { pointerId: event.pointerId, startX: event.clientX, deltaX: 0 };
  elements.discoverCard.setPointerCapture(event.pointerId);
  elements.discoverCard.firstElementChild?.classList.add("is-dragging");
}

function pointerMove(event) {
  if (!state.drag || state.drag.pointerId !== event.pointerId) return;
  state.drag.deltaX = event.clientX - state.drag.startX;
  const card = elements.discoverCard.firstElementChild;
  if (!card) return;
  const rotation = Math.max(-11, Math.min(11, state.drag.deltaX / 18));
  card.style.transform = `translate3d(${state.drag.deltaX}px, 0, 0) rotate(${rotation}deg)`;
  const progress = Math.min(Math.abs(state.drag.deltaX) / 110, 1);
  card.querySelector(".discover-stamp--select").style.opacity = state.drag.deltaX > 0 ? String(progress) : "0";
  card.querySelector(".discover-stamp--pass").style.opacity = state.drag.deltaX < 0 ? String(progress) : "0";
}

function pointerUp(event) {
  if (!state.drag || state.drag.pointerId !== event.pointerId) return;
  const distance = state.drag.deltaX;
  elements.discoverCard.releasePointerCapture(event.pointerId);
  if (shouldResolve(distance)) resolveDiscoverCard(distance > 0 ? "select" : "pass");
  else resetCardPosition();
}

function renderComparison(data) {
  state.data = data;
  state.matchIndex = 0;
  elements.baselineAnswer.replaceChildren(renderMarkdown(data.baseline.answer));
  elements.reactAnswer.replaceChildren(renderMarkdown(data.react.answer));
  elements.providerMode.textContent = data.provider_mode;
  renderTrace(data.react.trace || []);
  elements.discoverButton.hidden = !(data.react.matches || []).length;
  elements.discoverButton.firstChild.textContent = `Khám phá ${(data.react.matches || []).length} ứng viên `;
  elements.comparisonStatus.textContent = "Đã nhận đủ hai câu trả lời.";
  elements.liveStatus.textContent = "Đã nhận kết quả từ cả hai chế độ.";
}

async function submitComparison(message = elements.message.value) {
  const trimmed = message.trim();
  if (state.loading) return;
  if (!trimmed) {
    elements.error.textContent = "Hãy nhập yêu cầu để so sánh.";
    elements.message.focus();
    return;
  }
  elements.error.textContent = "";
  setLoading(true);
  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: elements.profile.value, message: trimmed }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error?.message || "Không thể chạy so sánh.");
    renderComparison(payload.data);
  } catch (error) {
    renderComparisonError();
    elements.error.textContent = error.message;
    elements.comparisonStatus.textContent = "Không thể hoàn tất. Bạn có thể thử lại.";
    elements.liveStatus.textContent = `Lỗi: ${error.message}`;
  } finally {
    setLoading(false);
  }
}

function resetForProfile() {
  if (state.chatReplyTimer) window.clearTimeout(state.chatReplyTimer);
  state.data = null;
  state.matchIndex = 0;
  state.resolved = [];
  state.chats = {};
  state.chatCandidateId = null;
  state.chatReplyTimer = null;
  elements.baselineAnswer.replaceChildren(node("p", "", "Gửi một câu hỏi để xem baseline trả lời chỉ từ context."));
  elements.reactAnswer.replaceChildren(node("p", "", "Agent sẽ gọi tool khi cần dữ liệu hồ sơ hoặc tính điểm."));
  elements.error.textContent = "";
  elements.comparisonStatus.textContent = "";
  elements.providerMode.textContent = "mock";
  elements.discoverButton.hidden = true;
  renderTrace([]);
  renderCompatibility(null);
  renderOpener(null);
  updateProfileSummary();
  exitDiscover();
}

async function copyOpener() {
  try {
    await navigator.clipboard.writeText(elements.openerText.value);
    elements.copyStatus.textContent = "Đã sao chép.";
  } catch {
    elements.openerText.focus();
    elements.openerText.select();
    elements.copyStatus.textContent = "Đã chọn nội dung. Nhấn Ctrl/Cmd + C.";
  }
}

elements.themeToggle.addEventListener("click", () => {
  const current = document.documentElement.dataset.theme;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = (current ? current === "dark" : systemDark) ? "light" : "dark";
  applyTheme(next);
  saveTheme(next);
});
elements.form.addEventListener("submit", (event) => { event.preventDefault(); submitComparison(); });
elements.message.addEventListener("input", () => { elements.count.textContent = `${elements.message.value.length}/1000`; });
elements.profile.addEventListener("change", resetForProfile);
elements.switch.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-view]");
  if (button) setView(button.dataset.view);
});
for (const button of document.querySelectorAll(".quick-prompt")) {
  button.addEventListener("click", () => {
    elements.message.value = button.dataset.prompt.replace(/U001/g, selectedProfile().id);
    elements.message.dispatchEvent(new Event("input"));
    elements.message.focus();
  });
}
elements.discoverButton.addEventListener("click", enterDiscover);
elements.startChat.addEventListener("click", () => enterChat(elements.startChat.dataset.candidateId));
elements.backToDiscover.addEventListener("click", exitChat);
elements.chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMockMessage();
});
elements.chatInput.addEventListener("input", () => {
  elements.chatCount.textContent = `${elements.chatInput.value.length}/500`;
  elements.chatError.textContent = "";
  if (elements.chatInput.value !== state.data?.react?.opener?.message) elements.suggestion.hidden = true;
});
elements.chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMockMessage();
  }
});
elements.back.addEventListener("click", exitDiscover);
elements.pass.addEventListener("click", () => resolveDiscoverCard("pass"));
elements.select.addEventListener("click", () => resolveDiscoverCard("select"));
elements.replay.addEventListener("click", enterDiscover);
elements.copyOpener.addEventListener("click", copyOpener);
elements.discoverCard.addEventListener("pointerdown", pointerDown);
elements.discoverCard.addEventListener("pointermove", pointerMove);
elements.discoverCard.addEventListener("pointerup", pointerUp);
elements.discoverCard.addEventListener("pointercancel", resetCardPosition);
document.addEventListener("keydown", (event) => {
  if (state.screen !== "discover" || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
  if (event.key === "ArrowLeft") resolveDiscoverCard("pass");
  if (event.key === "ArrowRight") resolveDiscoverCard("select");
});

applyTheme(storedTheme());
updateProfileSummary();
setView("compare");
