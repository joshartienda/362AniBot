import os
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------- Flask Setup ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")  # Ensure absolute path
app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path="")
CORS(app)

# ---------------- OpenAI Chat Client ----------------
try:
    from openai import OpenAI
    _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    _client = None

# ---------------- Serve Frontend ----------------
@app.route("/")
def root():
    # Serve public/index.html
    return app.send_static_file("index.html")

# ---------------- Serve JS/CSS explicitly ----------------
@app.route("/<path:filename>")
def static_files(filename):
    return app.send_static_file(filename)

ANILIST_ANIME_IDS = [101922, 15125, 11061, 20507, 20, 21459, 40748, 21435, 30276, 21735]
ANILIST_QUERY = '''
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { romaji english native }
    genres
    coverImage { large }
    averageScore
    description
  }
}
'''
ANILIST_URL = "https://graphql.anilist.co"


def fetch_anilist_recommendations(count=5):
    """Fetch a randomized subset of AniList favorites."""
    chosen_ids = random.sample(ANILIST_ANIME_IDS, min(count, len(ANILIST_ANIME_IDS)))
    results = []

    for anime_id in chosen_ids:
        variables = {"id": anime_id}
        try:
            resp = requests.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=10)
        except requests.RequestException as exc:
            print(f"[AniList] Request error for ID {anime_id}: {exc}")
            continue

        if resp.status_code == 200:
            anime = resp.json().get("data", {}).get("Media")
            if anime:
                results.append(anime)
            else:
                print(f"[AniList] Empty payload returned for ID {anime_id}.")
        else:
            print(f"[AniList] Request failed for ID {anime_id}: {resp.status_code} {resp.text}")

    if not results:
        print("[AniList] No anime results were retrieved from the GraphQL endpoint.")

    return results


def recommendations_to_prompt(anime_list):
    """Convert AniList data into a concise string for the chat model."""
    if not anime_list:
        return ""

    lines = ["AniList provided the following anime to reference:"]
    for anime in anime_list:
        title = anime.get("title", {}) or {}
        english = title.get("english") or title.get("romaji") or title.get("native") or "Unknown title"
        score = anime.get("averageScore")
        genres = ", ".join(anime.get("genres") or []) or "Genres unavailable"
        line = f"- {english} (Score: {score or 'N/A'}, Genres: {genres})"
        lines.append(line)
    lines.append("Be explicit when these AniList results inform your recommendation.")
    return "\n".join(lines)


def log_anilist_console_feedback(user_messages, anilist_results, reply_text=None):
    """Emit console output to show AniList data interaction with chat content."""
    if not anilist_results:
        print("[AniList] No dataset available for comparison.")
        return

    user_text = " ".join(
        (msg.get("content") or "")
        for msg in user_messages
        if isinstance(msg, dict) and msg.get("role") == "user"
    ).lower()
    reply_text = (reply_text or "").lower()

    known_titles = set()
    for anime in anilist_results:
        title = anime.get("title", {}) or {}
        for key in ("english", "romaji", "native"):
            name = title.get(key)
            if name:
                known_titles.add(name.lower())

    user_hits = sorted({name for name in known_titles if name and name in user_text})
    reply_hits = sorted({name for name in known_titles if name and name in reply_text})

    print("[AniList] Comparing chat content against AniList dataset...")
    if user_hits:
        print(f"[AniList] User prompt referenced: {', '.join(user_hits)}")
    else:
        print("[AniList] User prompt did not mention known AniList entries.")

    if reply_text:
        if reply_hits:
            print(f"[AniList] Model reply referenced AniList titles: {', '.join(reply_hits)}")
        else:
            print("[AniList] Model reply did not explicitly mention the sampled AniList titles.")


# ---------------- Chat Endpoint ----------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = list(data.get("messages") or [])
    user_messages = [msg for msg in messages if isinstance(msg, dict) and msg.get("role") == "user"]
    model = data.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens")
    include_flag = data.get("include_recommendations")
    include_recommendations = True if include_flag is None else bool(include_flag)
    recommendation_count = int(data.get("recommendation_count", 5))

    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "'messages' (non-empty list) is required"}), 400

    if _client is None:
        return jsonify({
            "error": "OpenAI client not initialized. Ensure 'openai' is installed and OPENAI_API_KEY is set."
        }), 500

    # Inject AniList results as optional context so the UI can detect data provenance.
    anilist_results = []
    if include_recommendations:
        try:
            anilist_results = fetch_anilist_recommendations(recommendation_count)
            prompt_block = recommendations_to_prompt(anilist_results)
            if prompt_block:
                messages = messages + [{"role": "system", "content": prompt_block}]
            if anilist_results:
                print(f"[AniList] Injected {len(anilist_results)} anime into chat context.")
            else:
                print("[AniList] No anime found for the requested count.")
        except Exception as exc:
            # Loggable placeholder; still continue with the chat request.
            print(f"Failed to fetch AniList recommendations: {exc}")

    try:
        kwargs = {"model": model, "messages": messages, "temperature": float(temperature)}
        if isinstance(max_tokens, int):
            kwargs["max_tokens"] = max_tokens

        resp = _client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        usage = getattr(resp, "usage", None)
        if usage is not None:
            if hasattr(usage, "model_dump"):
                usage = usage.model_dump()
            elif hasattr(usage, "dict"):
                usage = usage.dict()
        log_anilist_console_feedback(user_messages, anilist_results, content)
        return jsonify({
            "reply": content,
            "usage": usage,
            "model": model,
            "recommendations": anilist_results or None,
            "metadata": {
                "anilist_used": bool(anilist_results),
                "source": "AniList" if anilist_results else None,
            }
        })
    except Exception as e:
        status = 500
        msg = str(e)
        if "Invalid API key" in msg:
            status = 401
        return jsonify({"error": msg}), status

# ---------------- Recommendation Endpoint ----------------
@app.route("/api/recommendation", methods=["GET"])
def recommendation():
    count = int(request.args.get("count", 5))
    results = fetch_anilist_recommendations(count)

    if results:
        return jsonify(results)
    return jsonify({"error": "Could not fetch anime"}), 500

# ---------------- Run Flask ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
