// Shared by every page: anonymous id, "who's asking" (age group), votes, crisis help.
// Owner: Bhajneek (community features, decision 006). Talks to /api/vote, /api/ratings,
// /api/check, /api/track, /api/popular, /api/board*.
const SN = (() => {
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  // Anonymous: a random id kept in this browser, never tied to a person.
  let voter = store.get("sn-voter");
  if (!voter || !/^[A-Za-z0-9_-]{8,64}$/.test(voter)) {
    const rnd = crypto.getRandomValues ? Array.from(crypto.getRandomValues(new Uint8Array(12)), b => b.toString(16).padStart(2, "0")).join("")
      : String(Math.random()).slice(2) + Date.now();
    voter = `v_${rnd}`;
    store.set("sn-voter", voter);
  }

  const listeners = [];
  let audience = store.get("sn-audience") || "";
  function setAudience(a, persist = true) {
    audience = a || "";
    if (persist) store.set("sn-audience", audience);
    document.querySelectorAll("[data-audience-select]").forEach(s => { s.value = audience; });
    document.querySelectorAll("[data-audience]").forEach(b => {
      const on = b.dataset.audience === audience && store.get("sn-audience") !== null;
      b.classList.toggle("on", on);
      b.setAttribute("aria-checked", on ? "true" : "false");
    });
    listeners.forEach(fn => fn(audience));
  }

  function h(tag, attrs = {}, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    el.append(...kids.flat().filter(k => k != null && k !== false));
    return el;
  }

  async function api(path, body, opts = {}) {
    const r = await fetch(path, body === undefined ? opts : {
      method: "POST", headers: { "content-type": "application/json", ...(opts.headers || {}) },
      body: JSON.stringify(body),
    });
    let data = null;
    try { data = await r.json(); } catch (e) {}
    if (!r.ok) throw Object.assign(new Error(data?.detail || `HTTP ${r.status}`), { status: r.status, data });
    return data;
  }

  const ICON = {
    up: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10v11H4V10zM7 10l4-7c1.7 0 3 1.3 3 3v3h5.2a2 2 0 0 1 2 2.3l-1.3 8A2 2 0 0 1 17.9 21H7"/></svg>',
    down: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 14V3h3v11zM17 14l-4 7c-1.7 0-3-1.3-3-3v-3H4.8a2 2 0 0 1-2-2.3l1.3-8A2 2 0 0 1 6.1 3H17"/></svg>',
    flag: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 21V4M5 4h11l-2 4 2 4H5"/></svg>',
    shield: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/></svg>',
    heart: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>',
    users: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6.5 6.5 0 0 1 3.5 6"/></svg>',
  };

  // A compact 👍/👎 control for any vote target ("answer:…", "source:…", "post:…").
  // opts.reasons: on 👎, offer quick reasons (stored for SikhNet's review queue).
  function voteBar(target, initial = {}, opts = {}) {
    let state = { up: 0, down: 0, mine: 0, tag: null, ...initial };
    const upB = h("button", { type: "button", class: "vote up", "aria-label": opts.upLabel || "Helpful", html: ICON.up });
    const downB = h("button", { type: "button", class: "vote down", "aria-label": opts.downLabel || "Not helpful", html: ICON.down });
    const count = h("span", { class: "vote-count", "aria-live": "polite" });
    const tag = h("span", { class: "rating-tag" });
    const why = h("div", { class: "vote-why", hidden: true });
    const wrap = h("div", { class: `votebar${opts.compact ? " compact" : ""}` },
      opts.label ? h("span", { class: "vote-label" }, opts.label) : null, upB, count, downB, tag, why);
    function paint() {
      upB.classList.toggle("on", state.mine === 1);
      downB.classList.toggle("on", state.mine === -1);
      upB.setAttribute("aria-pressed", state.mine === 1);
      downB.setAttribute("aria-pressed", state.mine === -1);
      const net = state.up - state.down;
      count.textContent = opts.net ? String(net) : (state.up + state.down ? `${state.up}` : "");
      tag.textContent = state.tag ? state.tag.label : "";
      tag.className = `rating-tag ${state.tag ? state.tag.kind : ""}`;
    }
    async function cast(v, reason) {
      const value = state.mine === v && !reason ? 0 : v;
      try {
        state = { ...state, ...(await api("/api/vote", { target, value, voter, reason: reason || null })) };
        paint();
        opts.onChange?.(state);
      } catch (e) {
        tag.textContent = e.message;
        tag.className = "rating-tag low";
      }
    }
    upB.addEventListener("click", () => { why.hidden = true; cast(1); });
    downB.addEventListener("click", () => {
      cast(-1);
      if (opts.reasons && state.mine !== -1) {
        why.replaceChildren(h("span", {}, "What was wrong?"),
          ...opts.reasons.map(r => h("button", { type: "button", class: "why-opt", onclick: () => { cast(-1, r); why.replaceChildren(h("span", {}, "Thanks. This goes to SikhNet's review queue.")); } }, r)));
        why.hidden = false;
      }
    });
    paint();
    wrap.update = s => { state = { ...state, ...s }; paint(); };
    return wrap;
  }

  async function ratings(targets) {
    if (!targets.length) return {};
    try {
      return (await api(`/api/ratings?targets=${encodeURIComponent(targets.join(","))}&voter=${voter}`)).ratings || {};
    } catch (e) { return {}; }
  }

  // Crisis: shown instead of an AI answer, or after a board post (brief non-negotiable).
  function helpCard(help) {
    return h("section", { class: "help-card", role: "alert" },
      h("div", { class: "help-head" }, h("span", { html: ICON.heart }), h("h2", {}, "You're not alone")),
      h("p", {}, help.message),
      h("ul", { class: "help-list" }, ...help.contacts.map(c => h("li", {},
        h("strong", {}, c.name), h("span", {}, c.detail),
        c.url ? h("a", { href: c.url, target: "_blank", rel: "noopener" }, "Website") : null))),
      h("p", { class: "help-human" }, help.human));
  }

  function timeAgo(t) {
    const s = Math.max(1, Math.floor(Date.now() / 1000 - t));
    if (s < 60) return "just now";
    const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
    const hr = Math.floor(m / 60); if (hr < 24) return `${hr}h ago`;
    const d = Math.floor(hr / 24); return d < 30 ? `${d}d ago` : new Date(t * 1000).toLocaleDateString();
  }

  // Wire every "who's asking" control on the page.
  document.addEventListener("change", e => {
    if (e.target.matches("[data-audience-select]")) setAudience(e.target.value);
  });
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-audience]");
    if (b) setAudience(b.dataset.audience);
  });
  document.addEventListener("DOMContentLoaded", () => setAudience(audience, false));

  return {
    voter, h, api, ICON, voteBar, ratings, helpCard, timeAgo,
    get audience() { return audience; },
    setAudience, onAudience: fn => listeners.push(fn), refreshAudience: () => setAudience(audience, false),
    audienceLabel: a => ({ kids: "Kid mode", teens: "Teen mode", adults: "Adult" }[a] || "Everyone"),
  };
})();
