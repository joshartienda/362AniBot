const $ = (sel) => document.querySelector(sel);
const messagesEl = $("#messages");
const form = $("#chat-form");
const input = $("#prompt");
const sendBtn = $("#send");
const modelSel = $("#model");
const tempInput = $("#temperature");

const SYSTEM_PROMPT = [
  "You are AniBot, an enthusiastic expert on anime, manga, and related Japanese animation culture.",
  "Scope & refusal policy:",
  "- Engage only with anime-focused questions (series, characters, creators, genres, recommendations, production, conventions, manga tie-ins).",
  "- For anything outside that scope, refuse with a short apology and explain you only discuss anime; do not provide the requested information.",
  "- If a request is unsafe or disallowed, refuse in line with the platform's safety rules.",
].join(" ");

const MAX_USER_MESSAGES = 10; // Keeps the chat to roughly 10-20 total turns
const CLOSING_SUGGESTIONS = [
  "Check out 'Mob Psycho 100' if you enjoy heartfelt stories with stylish action.",
  "Give 'March Comes in Like a Lion' a try for a grounded character drama.",
  "'Made in Abyss' offers stunning adventure if you can handle darker themes.",
  "If you like classic shonen energy, revisit 'Yu Yu Hakusho' - it still holds up.",
  "For a cozy watch, 'Barakamon' delivers warm slice-of-life vibes.",
];

let conversationClosed = false;

// In-memory conversation; seed with a strict system prompt
const conversation = [
  { role: "system", content: SYSTEM_PROMPT },
];

function addMessage(role, content) {
  const li = document.createElement("li");
  li.className = `msg ${role === 'user' ? 'user' : role === 'assistant' ? 'assistant' : 'sys'}`;
  li.textContent = content;
  messagesEl.appendChild(li);
  li.scrollIntoView({ behavior: "smooth", block: "end" });
}

function setSending(sending) {
  const disabled = sending || conversationClosed;
  input.disabled = disabled;
  sendBtn.disabled = disabled;
  if (conversationClosed) {
    modelSel.disabled = true;
    tempInput.disabled = true;
  }
}

function userMessageCount() {
  return conversation.filter((msg) => msg.role === "user").length;
}

function closeConversationWithSuggestion() {
  if (conversationClosed) return;
  conversationClosed = true;
  const pick = Math.floor(Math.random() * CLOSING_SUGGESTIONS.length);
  const suggestion = CLOSING_SUGGESTIONS[pick];
  const closingLine = `Thanks for chatting about anime! Before we wrap up, here's a final recommendation: ${suggestion}`;
  conversation.push({ role: "assistant", content: closingLine });
  addMessage("assistant", closingLine);
  setSending(false);
}

function maybeCloseConversation() {
  if (!conversationClosed && userMessageCount() >= MAX_USER_MESSAGES) {
    closeConversationWithSuggestion();
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (conversationClosed) {
    addMessage("assistant", "We've already wrapped up this session. Refresh the page to start a new anime chat!");
    return;
  }

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
      addMessage("system", `[Error] ${msg}`);
      return;
    }

    const data = await res.json();
    const assistantText = data.reply || "(no content)";
    conversation.push({ role: "assistant", content: assistantText });
    addMessage("assistant", assistantText);
    maybeCloseConversation();
  } catch (err) {
    addMessage("system", `[Error] Network issue: ${err.message || err}`);
  } finally {
    if (!conversationClosed) {
      setSending(false);
    }
  }
});

// Initial tip for the user
addMessage("system", "Ask me anything about anime to get started.");
