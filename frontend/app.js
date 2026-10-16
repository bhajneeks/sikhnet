// Chat UI. Owner: Manveer, UI lane. Talks to POST /api/ask (docs/ARCHITECTURE.md § 3).
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const history = [];

fetch("/api/health").then(r => r.json()).then(h => {
  document.getElementById("status").textContent =
    `${h.records} entries · ${h.llm ? "Claude" : "fallback mode (no API key)"}`;
}).catch(() => {});

function addMsg(cls, text) {
  document.getElementById("empty")?.remove();
  const el = document.createElement("div");
  el.className = `msg ${cls}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
  return el;
}

function renderCitations(el, res) {
  if (res.citations?.length) {
    const box = document.createElement("div");
    box.className = "cites";
    for (const c of res.citations) {
      const d = document.createElement("details");
      const s = document.createElement("summary");
      s.textContent = `[${c.n}] ${c.question}`;
      const p = document.createElement("p");
      p.textContent = c.answer_excerpt;
      d.append(s, p);
      if (c.source_url) {
        const a = document.createElement("a");
        a.href = c.source_url; a.target = "_blank"; a.rel = "noopener"; a.textContent = "source";
        d.append(a);
      }
      box.append(d);
    }
    el.append(box);
  }
  const badge = document.createElement("div");
  badge.className = "badge";
  badge.textContent = `coverage: ${res.coverage}`;
  el.append(badge);
}

async function send(question) {
  addMsg("user", question);
  const pending = addMsg("bot thinking", "Searching the question bank…");
  try {
    const r = await fetch("/api/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
    const res = await r.json();
    pending.className = "msg bot";
    pending.textContent = res.answer;
    renderCitations(pending, res);
    history.push({ role: "user", content: question }, { role: "assistant", content: res.answer });
  } catch (e) {
    pending.className = "msg bot";
    pending.textContent = "Something went wrong reaching the server.";
  }
}

form.addEventListener("submit", e => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  send(q);
});
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
});
document.querySelectorAll(".starters button").forEach(b => b.addEventListener("click", () => send(b.textContent)));
