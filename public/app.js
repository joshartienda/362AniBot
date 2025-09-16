const $ = (sel) => document.querySelector(sel);
const messagesEl = $("#messages");
const form = $("#chat-form");
const input = $("#prompt");
const sendBtn = $("#send");
const modelSel = $("#model");
const tempInput = $("#temperature");

// In-memory conversation; seed with a system prompt
const conversation = [
  { role: "system", content: "You are a helpful assistant." },
];

function addMessage(role, content) {
  const li = document.createElement("li");
  li.className = `msg ${role === 'user' ? 'user' : role === 'assistant' ? 'assistant' : 'sys'}`;
  li.textContent = content;
  messagesEl.appendChild(li);
  li.scrollIntoView({ behavior: "smooth", block: "end" });
}

function setSending(sending) {
  input.disabled = sending;
  sendBtn.disabled = sending;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  const userMsg = { role: "user", content: text };
  conversation.push(userMsg);
  addMessage("user", text);
  input.value = "";
  setSending(true);

  try {
    const payload = {
      messages: conversation,
      model: modelSel.value,
      temperature: parseFloat(tempInput.value || "0.7"),
    };

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error || `Error ${res.status}`;
      addMessage("system", `⚠️ ${msg}`);
      return;
    }

    const data = await res.json();
    const assistantText = data.reply || "(no content)";
    conversation.push({ role: "assistant", content: assistantText });
    addMessage("assistant", assistantText);
  } catch (err) {
    addMessage("system", `⚠️ Network error: ${err.message || err}`);
  } finally {
    setSending(false);
  }
});

// Initial tip
addMessage("system", "Ask me anything to get started.");

