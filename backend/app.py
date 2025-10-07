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

# ---------------- Chat Endpoint ----------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    model = data.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens")

    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "'messages' (non-empty list) is required"}), 400

    if _client is None:
        return jsonify({
            "error": "OpenAI client not initialized. Ensure 'openai' is installed and OPENAI_API_KEY is set."
        }), 500

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
        return jsonify({
            "reply": content,
            "usage": usage,
            "model": model,
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
    anime_ids = [101922, 15125, 11061, 20507, 20, 21459, 40748, 21435, 30276, 21735]
    chosen_ids = random.sample(anime_ids, min(count, len(anime_ids)))

    results = []
    query = '''
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
    url = "https://graphql.anilist.co"

    for anime_id in chosen_ids:
        variables = {"id": anime_id}
        resp = requests.post(url, json={"query": query, "variables": variables})
        if resp.status_code == 200:
            anime = resp.json().get("data", {}).get("Media")
            if anime:
                results.append(anime)

    if results:
        return jsonify(results)
    return jsonify({"error": "Could not fetch anime"}), 500

# ---------------- Run Flask ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
