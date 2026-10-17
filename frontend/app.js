// Chat UI. Owner: Manveer, UI lane. Talks to POST /api/ask, GET /api/categories,
// GET /api/surprise (docs/ARCHITECTURE.md § 3). Design: docs/brain/status/manveer.md.
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const stopBtn = document.getElementById("stop");
const toBottom = document.getElementById("to-bottom");
const homeTemplate = document.getElementById("home").cloneNode(true);
const history = [];
let busy = false;
let controller = null;
let turnCount = 0;
let topicLabels = {};

// Checked against the real dataset: each gets a grounded or partial answer, not "not found".
const EXAMPLES = ["What is langar?", "Can a non-Sikh visit a Gurdwara?", "Can Sikhs eat meat?", "What is Vaisakhi?", "What happens at a Gurdwara?"];

const ICON = {
  arrow: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>',
  spark: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/></svg>',
  copy: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>',
  check: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>',
  retry: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>',
};

// ---- tiny DOM helpers (all user/API text goes through textContent or esc) ----
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  el.append(...kids.filter(k => k != null));
  return el;
}
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Minimal markdown: paragraphs, bullet/numbered lists, **bold**, *italic*, and [n] citation chips.
function inline(text, turn, altNs) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, "$1<em>$2</em>")
    .replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (_, ns) => ns.split(",").map(n => {
      n = n.trim();
      const alt = altNs.has(Number(n)) ? " alt" : "";
      return `<button type="button" class="cite${alt}" data-cite="${turn}-${n}" aria-label="Source ${n}">${n}</button>`;
    }).join(""));
}
function markdown(md, turn, altNs = new Set()) {
  const out = [];
  for (const block of String(md || "").trim().split(/\n{2,}/)) {
    const lines = block.split("\n");
    if (lines.every(l => /^\s*[-*]\s+/.test(l))) {
      out.push("<ul>" + lines.map(l => `<li>${inline(l.replace(/^\s*[-*]\s+/, ""), turn, altNs)}</li>`).join("") + "</ul>");
    } else if (lines.every(l => /^\s*\d+[.)]\s+/.test(l))) {
      out.push("<ol>" + lines.map(l => `<li>${inline(l.replace(/^\s*\d+[.)]\s+/, ""), turn, altNs)}</li>`).join("") + "</ol>");
    } else {
      out.push(`<p>${lines.map(l => inline(l.replace(/^#+\s*/, ""), turn, altNs)).join("<br>")}</p>`);
    }
  }
  return out.join("");
}
const plain = md => String(md || "").replace(/\*\*?/g, "").replace(/^#+\s*/gm, "").trim();

// ---- scrolling: follow new content only if the reader is already at the bottom ----
const nearBottom = () => window.innerHeight + window.scrollY >= document.body.scrollHeight - 140;
let following = true;
function scrollToEnd(smooth = true) {
  window.scrollTo({ top: document.body.scrollHeight, behavior: smooth ? "smooth" : "auto" });
}
function afterAppend() {
  if (following) scrollToEnd();
  else toBottom.hidden = false;
}
window.addEventListener("scroll", () => {
  following = nearBottom();
  if (following) toBottom.hidden = true;
  else if (document.body.classList.contains("has-chat")) toBottom.hidden = false;
}, { passive: true });
toBottom.addEventListener("click", () => { following = true; toBottom.hidden = true; scrollToEnd(); });

function startChat() {
  document.getElementById("home")?.remove();
  document.body.classList.add("has-chat");
}
function newChat() {
  if (controller) controller.abort();
  history.length = 0;
  chat.replaceChildren(homeTemplate.cloneNode(true));
  document.body.classList.remove("has-chat");
  toBottom.hidden = true;
  fillTopics();
  window.scrollTo({ top: 0 });
  input.focus();
}
document.getElementById("new-chat").addEventListener("click", newChat);

// ---- R1: source cards ----
// Primary records are SikhNet forum posts whatever the import file was called (e.g. "qa-sample-300");
// they're community answers, not official rulings (see DATASHEET.md), so say "forum answer".
function sourceLabel(c) {
  if (c.source_type === "secondary") return `${c.source || "Other source"} · other source`;
  return "SikhNet Q&A · forum answer";
}
function renderSources(citations, turn) {
  if (!citations?.length) return null;
  const cards = citations.map((c, i) => h("details", { class: "source", id: `src-${turn}-${c.n}`, ...(i === 0 ? { open: "" } : {}) },
    h("summary", {},
      h("span", { class: "num", "aria-hidden": "true" }, String(c.n)),
      h("span", { class: "source-head" },
        h("span", { class: "source-q" }, c.question),
        h("span", { class: "source-meta" }, sourceLabel(c)))),
    c.answer_excerpt ? h("p", {}, c.answer_excerpt) : null,
    c.source_url ? h("a", { href: c.source_url, target: "_blank", rel: "noopener" }, "Read the full entry") : null,
  ));
  return h("section", { class: "block", "aria-label": "Sources" },
    h("h2", { class: "eyebrow" }, `Where this answer comes from · ${citations.length}`),
    h("div", { class: "sources" }, ...cards));
}

// ---- R4 (+R3 secondary material): other perspectives ----
function renderPerspectives(perspectives, turn, altNs) {
  if (!perspectives?.length) return null;
  return h("section", { class: "block perspectives", "aria-label": "Other perspectives" },
    h("div", { class: "perspectives-head" },
      h("h2", {}, "Other perspectives"),
      h("span", {}, "Shown only when our sources contain them")),
    ...perspectives.map(p => h("div", { class: "view" },
      h("div", { class: "view-label" }, p.label || "Another interpretation"),
      h("p", { html: inline(p.text || "", turn, altNs) }))));
}

// ---- R2: follow-ups ----
function optionButton(q) {
  return h("button", { type: "button", class: "option", onclick: () => send(q) }, q, h("span", { html: ICON.arrow }));
}
function renderFollowUps(followUps) {
  if (!followUps?.length) return null;
  return h("section", { class: "block", "aria-label": "Suggested follow-up questions" },
    h("h2", { class: "eyebrow" }, "Keep exploring"),
    h("div", { class: "option-list" }, ...followUps.slice(0, 3).map(optionButton)));
}

// ---- per-answer actions: copy (answer + sources), ask again ----
function renderActions(res, question) {
  const copyBtn = h("button", { type: "button", class: "action", "aria-label": "Copy answer" },
    h("span", { html: ICON.copy }), h("span", { class: "action-label" }, "Copy"));
  copyBtn.addEventListener("click", async () => {
    const sources = (res.citations || []).map(c => `[${c.n}] ${c.question}${c.source_url ? ` — ${c.source_url}` : ""}`).join("\n");
    const text = plain(res.answer) + (sources ? `\n\nSources:\n${sources}` : "");
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.firstChild.innerHTML = ICON.check;
      copyBtn.lastChild.textContent = "Copied";
      setTimeout(() => { copyBtn.firstChild.innerHTML = ICON.copy; copyBtn.lastChild.textContent = "Copy"; }, 1600);
    } catch (e) {}
  });
  return h("div", { class: "actions" },
    copyBtn,
    h("button", { type: "button", class: "action", "aria-label": "Ask again", onclick: () => send(question) },
      h("span", { html: ICON.retry }), h("span", { class: "action-label" }, "Ask again")),
    res.mode === "fallback" ? h("span", { class: "mode-note" }, "Closest saved answer · AI summary off") : null);
}

function renderNotFound(res) {
  const suggestions = res.follow_ups?.length ? res.follow_ups.slice(0, 3) : ["Can a non-Sikh visit a Gurdwara?", "Can Sikhs eat meat?"];
  return h("section", { class: "notice", "aria-label": "Not in our sources" },
    h("div", { class: "notice-head" }, h("span", { html: ICON.info }), h("h2", {}, "This isn't in our sources")),
    h("p", {}, "We only answer from SikhNet's collection, so we won't guess. Try one of these, or explore a topic."),
    h("div", { class: "option-list" },
      ...suggestions.map(optionButton),
      h("button", { type: "button", class: "btn-accent", onclick: () => surprise(document.getElementById("topic").value) },
        h("span", { html: ICON.spark }), "Surprise me")));
}

function renderAnswer(res, turn, question) {
  // Citation numbers that are only used in perspectives get the quieter chip style.
  const altNs = new Set((res.perspectives || []).flatMap(p => p.citation_ns || []));
  const mainNs = new Set([...String(res.answer || "").matchAll(/\[(\d+)\]/g)].map(m => Number(m[1])));
  mainNs.forEach(n => altNs.delete(n));

  if (res.coverage === "not_found") return h("article", { class: "turn" }, renderNotFound(res));
  return h("article", { class: "turn" },
    res.coverage === "partial" ? h("div", { class: "partial", role: "note" },
      h("span", { html: ICON.info }),
      h("span", {}, "Our sources only partly cover this. Check the entries below before relying on it.")) : null,
    h("div", { class: "answer", html: markdown(res.answer, turn, altNs) }),
    renderActions(res, question),
    renderSources(res.citations, turn),
    renderPerspectives(res.perspectives, turn, altNs),
    renderFollowUps(res.follow_ups));
}

// Loading: staged label + elapsed seconds, so people know it's working.
function renderLoading(firstLabel) {
  const label = h("span", {}, firstLabel || "Searching SikhNet's answers…");
  const timer = h("span", { class: "elapsed" }, "0s");
  const el = h("div", { class: "loading", role: "status" },
    h("div", { class: "loading-label" }, h("span", { class: "spin", html: ICON.search }), label, timer),
    h("div", { class: "bar", style: "width: 92%" }),
    h("div", { class: "bar", style: "width: 78%" }),
    h("div", { class: "bar", style: "width: 60%" }));
  const started = Date.now();
  const tick = setInterval(() => {
    const s = Math.floor((Date.now() - started) / 1000);
    timer.textContent = `${s}s`;
    // Answers with Claude take ~10-15s; keep saying what's happening.
    if (s >= 12) label.textContent = "Still working. Careful answers take a moment…";
    else if (s >= 6) label.textContent = "Weighing what different members said…";
    else if (s >= 2) label.textContent = "Reading the sources and writing an answer…";
  }, 500);
  el.stop = () => clearInterval(tick);
  return el;
}

function setBusy(on) {
  busy = on;
  sendBtn.hidden = on;
  stopBtn.hidden = !on;
  updateSend();
  document.querySelectorAll("[data-surprise] button").forEach(b => { b.disabled = on; });
}
function updateSend() { sendBtn.disabled = busy || !input.value.trim(); }

// opts.retry: called instead of showing "not in our sources" (Surprise me picks another question).
// ---- streaming transport ----
// POST /api/ask/stream is Server-Sent Events (docs/ARCHITECTURE.md § 3,
// decision 005): citations -> delta* -> meta -> done, or error. citations
// arrive before the model has written a word, so the source cards can render
// while the answer is still coming in.
async function streamAsk(body, signal, on) {
  const r = await fetch("/api/ask/stream", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok || !r.body) throw new Error(`HTTP ${r.status}`);
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i);
      buf = buf.slice(i + 2);
      let event = "message", data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (data) on(event, JSON.parse(data));
    }
  }
}

async function send(question, opts = {}) {
  question = question.trim();
  if (!question || busy) return;
  let retry = null;
  startChat();
  setBusy(true);
  following = true;
  const turn = ++turnCount;
  const userMsg = h("div", { class: "user-msg" }, question);
  chat.append(userMsg);
  const pending = renderLoading(opts.loadingLabel);
  chat.append(pending);
  afterAppend();
  controller = new AbortController();

  // Built up as events arrive; shaped exactly like an /api/ask response so the
  // existing renderers can finish the turn.
  const res = { answer: "", citations: [], perspectives: [], follow_ups: [], coverage: null, mode: null };
  let article = null, answerEl = null, sourcesEl = null, queued = false;

  const paint = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (answerEl) answerEl.innerHTML = markdown(res.answer, turn, new Set());
      afterAppend();
    });
  };

  const openTurn = () => {
    if (article) return;
    answerEl = h("div", { class: "answer streaming" });
    article = h("article", { class: "turn" }, answerEl);
    pending.stop();
    pending.replaceWith(article);
  };

  try {
    await streamAsk({ question, history: history.slice(-10) }, controller.signal, (event, data) => {
      if (event === "citations") {
        res.citations = data.citations || [];
        res.mode = data.mode;
        // Sources are known before the first token — show them immediately.
        if (res.citations.length) {
          openTurn();
          sourcesEl = renderSources(res.citations, turn);
          if (sourcesEl) article.append(sourcesEl);
        }
      } else if (event === "delta") {
        openTurn();
        res.answer += data.text;
        paint();
      } else if (event === "meta") {
        Object.assign(res, {
          coverage: data.coverage,
          perspectives: data.perspectives || [],
          follow_ups: data.follow_ups || [],
          // meta.citations is authoritative: empty on not_found, so the cards
          // rendered from the earlier event have to go.
          citations: data.citations || [],
          mode: data.mode ?? res.mode,
        });
      } else if (event === "error") {
        throw new Error(data.message || "stream failed");
      }
    });

    if (res.coverage === "not_found" && opts.retry) {
      userMsg.remove();
      (article || pending).remove();
      retry = opts.retry;
      return;
    }
    // Re-render the finished turn through the normal path, so a streamed answer
    // and a non-streamed one are identical once complete.
    const finished = renderAnswer(res, turn, question);
    if (article) article.replaceWith(finished); else pending.replaceWith(finished);
    article = finished;
    history.push({ role: "user", content: question }, { role: "assistant", content: res.answer || "" });
  } catch (e) {
    const stopped = e.name === "AbortError";
    // Keep whatever already streamed; just say it was cut short.
    const notice = h("section", { class: "notice", role: stopped ? "status" : "alert" },
      h("div", { class: "notice-head" }, h("span", { html: ICON.info }),
        h("h2", {}, stopped ? "Stopped" : "Couldn't reach the server")),
      h("p", {}, stopped ? "You stopped this answer." : "Check your connection and try again."),
      h("div", { class: "option-list" }, optionButton(question)));
    if (article && res.answer) {
      answerEl.classList.remove("streaming");
      article.append(notice);
    } else if (article) {
      article.replaceWith(notice);
    } else {
      pending.replaceWith(notice);
    }
  } finally {
    if (answerEl) answerEl.classList.remove("streaming");
    pending.stop();
    controller = null;
    setBusy(false);
    afterAppend();
    if (retry) retry();
  }
}
stopBtn.addEventListener("click", () => controller?.abort());

// Clicking a [n] chip opens and highlights its source card.
chat.addEventListener("click", e => {
  const chip = e.target.closest("[data-cite]");
  if (!chip) return;
  const card = document.getElementById(`src-${chip.dataset.cite}`);
  if (!card) return;
  card.open = true;
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  card.classList.add("flash");
  setTimeout(() => card.classList.remove("flash"), 1200);
});

// ---- R5: topics + Surprise me (labels and free-text subjects: decision 004) ----
let topicKeys = [];
function fillTopics() {
  const opts = [["", "Any topic"], ...topicKeys.map(c => [c, topicLabels[c] || c])];
  document.querySelectorAll("[data-topics]").forEach(sel => {
    const keep = sel.value;
    sel.replaceChildren(...opts.map(([v, t]) => h("option", { value: v }, t)));
    sel.value = keep;
  });
}
async function loadTopics() {
  try {
    const res = await (await fetch("/api/categories")).json();
    topicKeys = res.categories || [];
    topicLabels = res.labels || {};
  } catch (e) {}
  fillTopics();
}
// A pick can come back "not in our sources" (e.g. a vague forum title when no hook was written);
// quietly try another rather than show a dead end, up to SURPRISE_TRIES picks.
const SURPRISE_TRIES = 3;
async function surprise(category, attempt = 1) {
  if (busy) return;
  try {
    const qs = category ? `?category=${encodeURIComponent(category)}` : "";
    const res = await (await fetch(`/api/surprise${qs}`)).json();
    if (res.question) return send(res.question, {
      loadingLabel: attempt > 1 ? "Finding a better question for you…" : "Finding a rabbit hole…",
      retry: attempt < SURPRISE_TRIES ? () => surprise(category, attempt + 1) : null,
    });
  } catch (e) {}
  startChat();
  chat.append(h("section", { class: "notice", role: "status" },
    h("div", { class: "notice-head" }, h("span", { html: ICON.info }), h("h2", {}, "Nothing to surprise you with yet")),
    h("p", {}, "We couldn't find a question on that. Try another topic.")));
  afterAppend();
}
document.addEventListener("submit", e => {
  const f = e.target.closest("[data-surprise]");
  if (!f) return;
  e.preventDefault();
  const sel = f.querySelector("[data-topics]");
  const free = f.querySelector("[data-topic-free]")?.value.trim();
  document.querySelectorAll("[data-topics]").forEach(s => { s.value = sel.value; });
  surprise(free || sel.value);
});
document.addEventListener("click", e => {
  const b = e.target.closest("[data-ask]");
  if (b) send(b.textContent);
});

// ---- composer ----
form.addEventListener("submit", e => {
  e.preventDefault();
  const q = input.value;
  if (!q.trim() || busy) return;
  input.value = "";
  autosize();
  updateSend();
  send(q);
});
document.querySelector(".composer-box").addEventListener("click", e => { if (!e.target.closest("button")) input.focus(); });
function autosize() { input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 200)}px`; }
input.addEventListener("input", () => { autosize(); updateSend(); });
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
});
// "/" jumps to the composer from anywhere; Escape stops a pending answer.
document.addEventListener("keydown", e => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
  if (e.key === "/" && !typing) { e.preventDefault(); input.focus(); }
  if (e.key === "Escape" && busy) controller?.abort();
});

// Rotating example questions in the empty composer.
let exampleIdx = 0;
setInterval(() => {
  if (input.value || document.activeElement === input) return;
  exampleIdx = (exampleIdx + 1) % EXAMPLES.length;
  input.placeholder = `Try “${EXAMPLES[exampleIdx]}”`;
}, 3500);

// ---- Intro: Khanda screen; a cursor move, click, tap or key fades it into the app ----
(function intro() {
  const el = document.getElementById("intro");
  const force = new URLSearchParams(location.search).has("intro");
  let seen = false;
  try { seen = sessionStorage.getItem("introSeen") === "1"; } catch (e) {}
  if (seen && !force) { document.body.classList.remove("intro-active"); return; }
  el.hidden = false;
  let armed = false, done = false, start = null;
  setTimeout(() => { armed = true; }, 1400);  // let the Khanda draw before a stray move dismisses it
  function enter() {
    if (done) return;
    done = true;
    try { sessionStorage.setItem("introSeen", "1"); } catch (e) {}
    el.classList.add("leaving");
    document.body.classList.remove("intro-active");
    setTimeout(() => {
      el.remove();
      if (matchMedia("(pointer: fine)").matches) input.focus();
    }, 850);
  }
  el.addEventListener("click", enter);
  document.getElementById("intro-enter").addEventListener("click", e => { e.stopPropagation(); enter(); });
  window.addEventListener("pointermove", e => {
    if (done || !armed || e.pointerType !== "mouse") return;
    if (!start) { start = [e.clientX, e.clientY]; return; }
    if (Math.hypot(e.clientX - start[0], e.clientY - start[1]) > 40) enter();
  });
  window.addEventListener("keydown", e => { if (!done && !["Shift", "Meta", "Control", "Alt", "Tab"].includes(e.key)) { e.preventDefault(); enter(); } }, { capture: true });
  document.getElementById("intro-enter").focus({ preventScroll: true });
})();

fetch("/api/health").then(r => r.json()).then(hl => {
  document.getElementById("status").textContent = `Answers from SikhNet's Q&A · ${hl.records} entries`;
}).catch(() => {});
loadTopics();
if (!document.body.classList.contains("intro-active") && matchMedia("(pointer: fine)").matches) input.focus();  // no surprise keyboard on phones
