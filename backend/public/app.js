const $ = (sel) => document.querySelector(sel);
const messagesEl = $("#messages");
const form = $("#chat-form");
const input = $("#prompt");
const sendBtn = $("#send");
const modelSel = $("#model");
const tempInput = $("#temperature");
const carouselContainer = $("#carousel-container");

const SYSTEM_PROMPT = [
  "You are AniBot, an enthusiastic expert on anime, manga, and related Japanese animation culture.",
  "Scope & refusal policy: Engage only with anime-focused questions.",
].join(" ");

const MAX_USER_MESSAGES = 10; // 10 things the user likes
let conversationClosed = false;
const conversation = [{ role: "system", content: SYSTEM_PROMPT }];

// ---------------- Helper Functions ----------------
function addMessage(role, content) {
  const li = document.createElement("li");
  li.className = `msg ${
    role === "user" ? "user" : role === "assistant" ? "assistant" : "sys"
  }`;
  li.textContent = content;
  messagesEl.appendChild(li);
  li.scrollIntoView({ behavior: "smooth", block: "end" });
}

function setSending(sending) {
  const disabled = sending || conversationClosed;
  input.disabled = disabled;
  sendBtn.disabled = disabled;
}

function userMessageCount() {
  return conversation.filter((msg) => msg.role === "user").length;
}

// ---------------- Drag & Scroll Carousel ----------------
function makeCarouselDraggable(carousel) {
  let isDown = false,
    startX,
    scrollLeft;
  carousel.addEventListener("mousedown", (e) => {
    isDown = true;
    carousel.classList.add("active");
    startX = e.pageX - carousel.offsetLeft;
    scrollLeft = carousel.scrollLeft;
  });
  carousel.addEventListener("mouseleave", () => {
    isDown = false;
    carousel.classList.remove("active");
  });
  carousel.addEventListener("mouseup", () => {
    isDown = false;
    carousel.classList.remove("active");
  });
  carousel.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - carousel.offsetLeft;
    carousel.scrollLeft = scrollLeft - (x - startX) * 2;
  });
}

// ---------------- Recommendation Carousel ----------------
async function closeConversationWithRecommendation() {
  if (conversationClosed) return;
  conversationClosed = true;

  try {
    // Optional: tell the user we're generating recs
    addMessage(
      "assistant",
      "Nice picks! Let me cook up some anime recommendations for you..."
    );

    const res = await fetch("/api/recommendation?count=5");
    const animeList = await res.json();

    if (!animeList || animeList.error || animeList.length === 0) {
      addMessage(
        "assistant",
        "Thanks for sharing your likes! I couldn't fetch recommendations right now."
      );
      setSending(false);
      return;
    }

    // Clear any previous carousel
    carouselContainer.innerHTML = "";

    // Add a heading above the carousel
    const heading = document.createElement("h2");
    heading.textContent = "Anime you might like:";
    heading.style.color = "#fff";
    heading.style.marginBottom = "10px";
    carouselContainer.appendChild(heading);

    const carousel = document.createElement("div");
    carousel.className = "anime-carousel";

    animeList.forEach((anime) => {
      const card = document.createElement("div");
      card.className = "anime-card";
      card.innerHTML = `
        <img src="${anime.coverImage.large}" alt="${anime.title.romaji}">
        <h2>${anime.title.english || anime.title.romaji}</h2>
        <p><strong>Genres:</strong> ${anime.genres.join(", ")}</p>
        <p><strong>Score:</strong> ${anime.averageScore}</p>
      `;
      carousel.appendChild(card);
    });

    carouselContainer.appendChild(carousel);
    makeCarouselDraggable(carousel);

    conversation.push({
      role: "assistant",
      content: "[Anime Recommendation Carousel]",
    });
  } catch (err) {
    addMessage("assistant", "Error fetching recommendations: " + err.message);
  }

  setSending(false);
}

function maybeCloseConversation() {
  if (!conversationClosed && userMessageCount() >= MAX_USER_MESSAGES) {
    closeConversationWithRecommendation();
  } else {
    const remaining = MAX_USER_MESSAGES - userMessageCount();
    if (remaining > 0) {
      addMessage(
        "system",
        `Noted! Please tell me ${remaining} more thing(s) you like.`
      );
    }
  }
}

// ---------------- Chat Submission ----------------
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (conversationClosed) {
    addMessage(
      "assistant",
      "Session closed. Refresh the page to start a new chat!"
    );
    return;
  }

  const text = input.value.trim();
  if (!text) return;

  conversation.push({ role: "user", content: text });
  addMessage("user", text);
  input.value = "";

  // If we've reached 10 likes, go straight to recommendations (no more API chat needed)
  if (userMessageCount() >= MAX_USER_MESSAGES) {
    setSending(true);
    maybeCloseConversation();
    return;
  }

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
      addMessage("system", `[Error] ${err.error || `Error ${res.status}`}`);
      return;
    }

    const data = await res.json();
    const assistantText = data.reply || "(no content)";
    conversation.push({ role: "assistant", content: assistantText });
    addMessage("assistant", assistantText);

    // After each submission, check progress toward 10 likes
    maybeCloseConversation();
  } catch (err) {
    addMessage("system", `[Error] Network issue: ${err.message || err}`);
  } finally {
    if (!conversationClosed) setSending(false);
  }
});

// Initial instructions
addMessage(
  "system",
  "Tell me 10 things you like (anime, genres, characters, vibes, or anything). " +
    "After the 10th one, I'll show you an anime carousel under this chat!"
);