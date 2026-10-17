// Community bulletin board. Owner: Bhajneek (decision 006). Uses common.js (SN).
// Routes: community.html (list) · community.html#t=<id> (one question) · ?ask=<text> (prefill from chat).
const { h, api, ICON } = SN;
const listEl = document.getElementById("thread-list");
const boardEl = document.getElementById("board");
const threadEl = document.getElementById("thread-view");
const form = document.getElementById("post-form");
const msg = document.getElementById("post-msg");
let sort = "top";
let topics = [];
let modMode = false;
try { modMode = sessionStorage.getItem("sn-mod") === "1" || new URLSearchParams(location.search).has("mod"); } catch (e) {}
const formOpened = Date.now();  // bot check: humans take a few seconds to write

const tagLabel = t => t ? h("span", { class: "tag" }, t) : null;
const ageTag = (rating, label) => rating && rating !== "all" ? h("span", { class: `tag age-${rating}` }, label) : null;

function modHeaders() {
  let token = "";
  try { token = sessionStorage.getItem("sn-mod-token") || ""; } catch (e) {}
  return token ? { "x-admin-token": token } : {};
}

// ---------------------------------------------------------------- list
async function loadList() {
  const params = new URLSearchParams({ sort, voter: SN.voter });
  const topic = document.getElementById("filter-topic").value;
  const q = document.getElementById("filter-q").value.trim();
  if (topic) params.set("topic", topic);
  if (q) params.set("q", q);
  if (SN.audience) params.set("audience", SN.audience);
  listEl.setAttribute("aria-busy", "true");
  let data;
  try { data = await api(`/api/board?${params}`); } catch (e) {
    // Proof of concept: an empty board reads better on stage than an error.
    listEl.replaceChildren(h("p", { class: "empty-note" }, "No questions yet. Be the first to ask."));
    return;
  } finally { listEl.removeAttribute("aria-busy"); }
  if (!topics.length) {
    topics = data.topics;
    for (const id of ["filter-topic", "post-topic"]) {
      const sel = document.getElementById(id);
      sel.append(...topics.map(t => h("option", { value: t.key }, t.label)));
    }
  }
  if (!data.threads.length) {
    listEl.replaceChildren(h("div", { class: "empty-board" },
      h("span", { html: ICON.users }),
      h("h3", {}, data.total ? "Nothing matches yet" : "Be the first to ask"),
      h("p", {}, data.total ? "Try another topic, or clear the search." : "Questions you post show up here. Others can reply, and the best replies rise to the top.")));
    return;
  }
  listEl.replaceChildren(...data.threads.map(threadCard));
}

function threadCard(t) {
  const bar = SN.voteBar(`post:${t.id}`, { up: t.up, down: t.down, mine: t.my_vote, tag: null },
    { compact: true, net: true, upLabel: "Good question", downLabel: "Not a good question" });
  return h("article", { class: "thread-card" },
    h("div", { class: "thread-vote" }, bar),
    h("a", { class: "thread-main", href: `#t=${t.id}` },
      h("div", { class: "thread-tags" }, tagLabel(t.topic_label), ageTag(t.age_rating, t.age_label),
        t.has_verified ? h("span", { class: "tag verified" }, "✓ Verified answer") : null),
      h("h3", {}, t.title),
      t.body ? h("p", { class: "thread-body" }, t.body) : null,
      t.top_reply ? h("blockquote", { class: "top-reply" },
        h("span", { class: "top-reply-label" }, t.top_reply.verified ? "✓ Verified answer" : "Top reply"),
        h("span", {}, t.top_reply.body)) : null,
      h("div", { class: "thread-meta" },
        h("span", {}, t.author), h("span", {}, SN.timeAgo(t.created)),
        h("span", { class: t.replies ? "" : "unanswered" }, t.replies ? `${t.replies} repl${t.replies === 1 ? "y" : "ies"}` : "No replies yet"))));
}

// ---------------------------------------------------------------- one thread
async function openThread(id) {
  boardEl.hidden = true;
  threadEl.hidden = false;
  threadEl.replaceChildren(h("div", { class: "loading" }, h("div", { class: "bar", style: "width:80%" }), h("div", { class: "bar", style: "width:60%" })));
  window.scrollTo({ top: 0 });
  let data;
  try {
    data = await api(`/api/board/${id}?voter=${SN.voter}${SN.audience ? `&audience=${SN.audience}` : ""}`);
  } catch (e) {
    threadEl.replaceChildren(backLink(), h("section", { class: "notice" }, h("h2", {}, "This question isn't available"),
      h("p", {}, "It may have been removed by a moderator.")));
    return;
  }
  if (data.restricted) {
    threadEl.replaceChildren(backLink(), h("section", { class: "notice" }, h("h2", {}, "This one is for older readers"),
      h("p", {}, `It's marked ${data.age_label}. Change "Who's asking?" at the top if that's you.`)));
    return;
  }
  const t = data.thread;
  const qBar = SN.voteBar(`post:${t.id}`, { up: t.up, down: t.down, mine: t.my_vote }, { net: true, upLabel: "Good question", downLabel: "Not a good question" });
  const head = h("section", { class: "thread-head" },
    h("div", { class: "thread-tags" }, tagLabel(t.topic_label), ageTag(t.age_rating, t.age_label)),
    h("h1", {}, t.title),
    t.body ? h("p", { class: "thread-full" }, t.body) : null,
    t.pending ? h("p", { class: "pending-note" }, "Only you can see this until a moderator checks it.") : null,
    h("div", { class: "thread-meta" }, h("span", {}, t.author), h("span", {}, SN.timeAgo(t.created))),
    h("div", { class: "thread-actions" }, qBar, t.mine ? null : reportBtn(`post:${t.id}`)));

  const related = data.related.length ? h("section", { class: "archive-box" },
    h("h2", { class: "eyebrow" }, "SikhNet's archive on this"),
    h("p", { class: "archive-note" }, "Answers from SikhNet's own Q&A, with sources."),
    h("div", { class: "option-list" }, ...data.related.map(r =>
      h("a", { class: "option", href: `./?q=${encodeURIComponent(r.question)}` }, r.question,
        h("span", { html: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>' }))))) : null;

  const replies = h("section", { class: "replies", "aria-label": "Replies" },
    h("div", { class: "replies-head" },
      h("h2", {}, data.replies.length ? `${data.replies.length} repl${data.replies.length === 1 ? "y" : "ies"}` : "No replies yet"),
      data.replies.length > 1 ? h("span", { class: "block-note" }, "Most helpful first") : null),
    ...data.replies.map((r, i) => replyCard(r, i === 0 && data.replies.length > 1)));

  threadEl.replaceChildren(backLink(), head, related, replies, replyForm(t.id));
}

function replyCard(r, best) {
  const bar = SN.voteBar(`post:${r.id}`, { up: r.up, down: r.down, mine: r.my_vote, tag: r.tag },
    { compact: true, label: "Helpful?", upLabel: "Helpful", downLabel: "Not helpful" });
  return h("article", { class: `reply${r.verified ? " verified" : ""}${best && !r.verified && r.up ? " best" : ""}` },
    r.verified ? h("span", { class: "reply-badge verified" }, "✓ Verified by SikhNet")
      : best && r.up ? h("span", { class: "reply-badge" }, "Most helpful") : null,
    h("p", { class: "reply-body" }, r.body),
    r.pending ? h("p", { class: "pending-note" }, "Only you can see this until a moderator checks it.") : null,
    h("div", { class: "reply-foot" },
      h("span", { class: "thread-meta" }, h("span", {}, r.author), h("span", {}, SN.timeAgo(r.created))),
      bar, r.mine ? null : reportBtn(`post:${r.id}`),
      modMode ? h("button", { type: "button", class: "mod-btn", onclick: async e => {
        try { await api(`/api/mod/post/${r.id}`, { action: r.verified ? "unverify" : "verify" }, { headers: modHeaders() }); route(); }
        catch (err) { e.target.textContent = err.message; }
      } }, r.verified ? "Remove ✓" : "Mark verified ✓") : null));
}

function reportBtn(target) {
  const b = h("button", { type: "button", class: "report", "aria-label": "Report", title: "Report to moderators" },
    h("span", { html: ICON.flag }), h("span", {}, "Report"));
  b.addEventListener("click", async () => {
    const reasons = ["Hate or bullying", "Spam or ads", "Wrong or misleading", "Not appropriate for kids"];
    const menu = h("div", { class: "report-menu" }, h("span", {}, "Why?"),
      ...reasons.map(reason => h("button", { type: "button", class: "why-opt", onclick: async () => {
        try {
          const res = await api("/api/report", { target, voter: SN.voter, reason });
          menu.replaceChildren(h("span", {}, res.message));
        } catch (e) { menu.replaceChildren(h("span", {}, e.message)); }
      } }, reason)));
    b.replaceWith(menu);
  });
  return b;
}

function replyForm(threadId) {
  const opened = Date.now();
  const ta = h("textarea", { name: "body", rows: 4, maxlength: 5000, placeholder: "Share what you know. Be kind, and say where it comes from if you can.", required: true });
  const author = h("input", { name: "author", maxlength: 40, placeholder: "Anonymous" });
  const hp = h("input", { name: "website", tabindex: "-1", autocomplete: "off" });
  const out = h("div", { class: "form-msg", role: "status" });
  const f = h("form", { class: "post-card reply-form", novalidate: true },
    h("h2", {}, "Add a reply"),
    h("div", { class: "field" }, h("label", {}, "Your reply"), ta),
    h("div", { class: "post-row two" }, h("div", { class: "field" }, h("label", {}, "Name ", h("span", { class: "opt" }, "(optional)")), author)),
    h("div", { class: "hp", "aria-hidden": "true" }, h("label", {}, "Website ", hp)),
    h("div", { class: "post-foot" }, h("p", { class: "fineprint-left" }, "Replies are checked for spam and hate."),
      h("button", { type: "submit", class: "btn-accent" }, "Post reply")),
    out);
  f.addEventListener("submit", async e => {
    e.preventDefault();
    out.className = "form-msg";
    if (ta.value.trim().length < 2) { out.textContent = "Write a reply first."; return; }
    try {
      const res = await api(`/api/board/${threadId}/reply`, { body: ta.value, author: author.value, voter: SN.voter,
        elapsed_ms: Date.now() - opened, website: hp.value });
      handlePosted(res, out, () => { ta.value = ""; openThread(threadId); });
    } catch (err) { postFailed(err, out, "reply", () => { ta.value = ""; }); }
  });
  return f;
}

function handlePosted(res, out, onOk) {
  out.replaceChildren();
  if (!res.ok) { out.textContent = res.message; out.className = "form-msg err"; return; }
  if (res.help) out.append(SN.helpCard(res.help));
  out.append(h("p", { class: res.status === "visible" ? "ok" : "warn" }, res.status === "visible" ? "Posted. Thank you!" : res.message));
  if (res.status === "visible" || !res.help) setTimeout(onOk, res.status === "visible" ? 400 : 1800);
}

// Proof of concept: the board isn't backed by durable storage, so a server or
// network failure still thanks the poster. 4xx (validation, rate limits) shows as-is.
function postFailed(err, out, what, reset) {
  out.replaceChildren();
  if (err.status && err.status < 500) { out.textContent = err.message; out.className = "form-msg err"; return; }
  out.className = "form-msg";
  out.append(h("p", { class: "ok" }, `Thanks! Your ${what} was received. This board is a proof of concept, so it isn't saved yet.`));
  reset();
}

const backLink = () => h("a", { class: "back", href: "#" }, "← All questions");

// ---------------------------------------------------------------- new question
form.addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(form);
  msg.className = "form-msg";
  if ((fd.get("title") || "").trim().length < 8) { msg.textContent = "Write your question as a full sentence."; msg.classList.add("err"); return; }
  try {
    const res = await api("/api/board", {
      title: fd.get("title"), body: fd.get("body"), topic: fd.get("topic") || null, audience: fd.get("audience"),
      author: fd.get("author"), voter: SN.voter, elapsed_ms: Date.now() - formOpened, website: fd.get("website") || "",
    });
    handlePosted(res, msg, () => { form.reset(); msg.replaceChildren(); location.hash = `t=${res.id}`; });
  } catch (err) { postFailed(err, msg, "question", () => form.reset()); }
});

// ---------------------------------------------------------------- wiring
document.querySelectorAll("[data-sort]").forEach(b => b.addEventListener("click", () => {
  sort = b.dataset.sort;
  document.querySelectorAll("[data-sort]").forEach(x => { x.classList.toggle("on", x === b); x.setAttribute("aria-selected", x === b); });
  loadList();
}));
document.getElementById("filter-topic").addEventListener("change", loadList);
let searchT;
document.getElementById("filter-q").addEventListener("input", () => { clearTimeout(searchT); searchT = setTimeout(loadList, 250); });
SN.onAudience(() => route());

function route() {
  const m = location.hash.match(/t=(\d+)/);
  if (m) return openThread(m[1]);
  threadEl.hidden = true;
  boardEl.hidden = false;
  loadList();
}
window.addEventListener("hashchange", route);

// Prefill from chat: "Ask the community" on an answer.
const prefill = new URLSearchParams(location.search).get("ask");
if (prefill) {
  document.getElementById("post-title").value = prefill.slice(0, 200);
  if (SN.audience) document.getElementById("post-aud").value = SN.audience;
  setTimeout(() => form.scrollIntoView({ behavior: "smooth", block: "center" }), 200);
}
route();
