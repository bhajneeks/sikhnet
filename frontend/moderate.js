// Moderator queue. Owner: Bhajneek (decision 006). Uses common.js (SN) and /api/mod/*.
const { h, api } = SN;
const listEl = document.getElementById("mod-list");
let data = null, tab = "held";
const FLAG_TEXT = { crisis: "Crisis: needs a person", link: "Contains a link", caps: "Shouting", junk: "Looks like junk",
  profanity: "Profanity", reported: "Reported by users", "ai:hate": "Claude: hate", "ai:harassment": "Claude: harassment",
  "ai:spam": "Claude: spam", "ai:sexual": "Claude: sexual", "ai:crisis": "Claude: crisis" };

function token() { try { return sessionStorage.getItem("sn-mod-token") || ""; } catch (e) { return ""; } }
const headers = () => (token() ? { "x-admin-token": token() } : {});

async function load() {
  try {
    data = await api("/api/mod/queue", undefined, { headers: headers() });
  } catch (e) {
    document.getElementById("mod-msg").textContent = e.message;
    document.getElementById("mod-app").hidden = true;
    return;
  }
  document.getElementById("mod-login").hidden = true;
  document.getElementById("mod-app").hidden = false;
  try { sessionStorage.setItem("sn-mod", "1"); } catch (e) {}
  const s = data.stats;
  document.getElementById("mod-stats").replaceChildren(...[
    ["waiting for review", s.held], ["questions on the board", s.threads], ["replies", s.replies],
    ["votes cast", s.votes], ["questions asked", s.asks]].map(([k, v]) => h("div", {}, h("dt", {}, k), h("dd", {}, String(v)))));
  render();
}

async function act(id, action) {
  try { await api(`/api/mod/post/${id}`, { action }, { headers: headers() }); load(); }
  catch (e) { alertRow(e.message); }
}
function alertRow(text) { listEl.prepend(h("p", { class: "form-msg err" }, text)); }

function postRow(p) {
  const crisis = p.flags.includes("crisis") || p.flags.includes("ai:crisis");
  return h("article", { class: `mod-item${crisis ? " crisis" : ""}` },
    h("div", { class: "thread-tags" }, ...p.flags.map(f => h("span", { class: `tag${f.includes("crisis") ? " age-adult" : ""}` }, FLAG_TEXT[f] || f)),
      p.reports ? h("span", { class: "tag" }, `${p.reports} report${p.reports === 1 ? "" : "s"}`) : null,
      h("span", { class: "tag" }, p.parent_id ? "Reply" : "Question")),
    p.parent_id && p.thread_title ? h("p", { class: "mod-context" }, `On: ${p.thread_title}`) : null,
    p.title ? h("h3", {}, p.title) : null,
    h("p", { class: "reply-body" }, p.body),
    crisis ? h("p", { class: "pending-note" }, "Reach out through SikhNet's partner organisations. Don't publish this.") : null,
    h("div", { class: "reply-foot" },
      h("span", { class: "thread-meta" }, h("span", {}, p.author), h("span", {}, SN.timeAgo(p.created))),
      h("div", { class: "mod-actions" },
        crisis ? null : h("button", { type: "button", class: "btn-ghost", onclick: () => act(p.id, "approve") }, "Approve"),
        p.status === "visible" ? h("button", { type: "button", class: "btn-ghost", onclick: () => act(p.id, "hide") }, "Hide") : null,
        h("button", { type: "button", class: "btn-ghost danger", onclick: () => act(p.id, "delete") }, "Delete"),
        h("a", { class: "btn-ghost", href: `community.html#t=${p.parent_id || p.id}` }, "View"))));
}

function render() {
  document.querySelectorAll("[data-tab]").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  let items = [];
  if (tab === "held") items = data.held.map(postRow);
  if (tab === "reported") items = data.reported.map(postRow);
  if (tab === "low") items = data.low_rated.map(v => h("article", { class: "mod-item" },
    h("div", { class: "thread-tags" }, h("span", { class: "tag" }, v.target.startsWith("source:") ? "Archive answer" : "Bot answer"),
      h("span", { class: "tag age-teen" }, `${v.up} 👍 · ${v.down} 👎`)),
    h("h3", {}, v.title || v.target),
    v.reasons ? h("p", { class: "reply-body" }, `Reasons given: ${v.reasons}`) : null,
    v.title ? h("a", { class: "btn-ghost", href: `./?q=${encodeURIComponent(v.title)}` }, "See it in the app") : null));
  if (tab === "log") items = data.log.map(l => h("div", { class: "log-row" },
    h("span", {}, SN.timeAgo(l.created)), h("strong", {}, l.action), h("span", {}, l.target), h("span", { class: "muted" }, l.reason || "")));
  listEl.replaceChildren(...(items.length ? items : [h("div", { class: "empty-board" }, h("h3", {}, "All clear"), h("p", {}, "Nothing here right now."))]));
}

document.querySelectorAll("[data-tab]").forEach(b => b.addEventListener("click", () => { tab = b.dataset.tab; render(); }));
document.getElementById("mod-login").addEventListener("submit", e => {
  e.preventDefault();
  try { sessionStorage.setItem("sn-mod-token", document.getElementById("mod-token").value.trim()); } catch (err) {}
  load();
});
load();
setInterval(() => { if (data) load(); }, 20000);
