const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const messages = document.getElementById("messages");

const SPARKLE_SVG =
  '<svg viewBox="0 0 24 24" width="14" height="14" fill="none"><path d="M12 3L13.8 9.2L20 11L13.8 12.8L12 19L10.2 12.8L4 11L10.2 9.2L12 3Z" fill="currentColor"/></svg>';

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInline(text) {
  const links = [];

  // markdown-style [text](url) links
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
    links.push(`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`);
    return `@@LINK${links.length - 1}@@`;
  });

  // bare URLs
  text = text.replace(/(https?:\/\/[^\s<]+)/g, (match) => {
    let url = match;
    let trail = "";
    const trailMatch = url.match(/[.,;:!?)\]"']+$/);
    if (trailMatch) {
      trail = trailMatch[0];
      url = url.slice(0, -trail.length);
    }
    links.push(`<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`);
    return `@@LINK${links.length - 1}@@${trail}`;
  });

  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/@@LINK(\d+)@@/g, (_, idx) => links[Number(idx)]);

  return text;
}

function renderMarkdown(raw) {
  const lines = escapeHtml(raw).split(/\r?\n/);
  let html = "";
  let i = 0;

  const isBullet = (l) => /^\s*[-*]\s+/.test(l);
  const isOrdered = (l) => /^\s*\d+\.\s+/.test(l);

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") {
      i++;
      continue;
    }

    if (isBullet(line)) {
      const items = [];
      while (i < lines.length && isBullet(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      html += "<ul>" + items.map((it) => `<li>${renderInline(it)}</li>`).join("") + "</ul>";
      continue;
    }

    if (isOrdered(line)) {
      const items = [];
      while (i < lines.length && isOrdered(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      html += "<ol>" + items.map((it) => `<li>${renderInline(it)}</li>`).join("") + "</ol>";
      continue;
    }

    const paraLines = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !isBullet(lines[i]) && !isOrdered(lines[i])) {
      paraLines.push(lines[i]);
      i++;
    }
    html += `<p>${paraLines.map(renderInline).join("<br>")}</p>`;
  }

  return html;
}

function addMessage(text, role) {
  const row = document.createElement("div");
  row.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role}-avatar`;
  avatar.innerHTML = role === "user" ? "U" : SPARKLE_SVG;
  avatar.setAttribute("aria-hidden", "true");

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (role === "assistant") {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }

  if (role === "user") {
    row.appendChild(bubble);
    row.appendChild(avatar);
  } else {
    row.appendChild(avatar);
    row.appendChild(bubble);
  }

  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function addTypingIndicator() {
  const row = document.createElement("div");
  row.className = "message assistant";
  row.id = "typing-indicator";

  const avatar = document.createElement("div");
  avatar.className = "avatar assistant-avatar";
  avatar.innerHTML = SPARKLE_SVG;
  avatar.setAttribute("aria-hidden", "true");

  const bubble = document.createElement("div");
  bubble.className = "bubble typing";
  bubble.innerHTML = "<span></span><span></span><span></span>";

  row.appendChild(avatar);
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  addTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    removeTypingIndicator();

    if (!res.ok) {
      addMessage(`Error: request failed (${res.status})`, "assistant").classList.add("error");
    } else {
      const data = await res.json();
      addMessage(data.response, "assistant");
    }
  } catch (err) {
    removeTypingIndicator();
    addMessage(`Error: ${err.message}`, "assistant").classList.add("error");
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
});
