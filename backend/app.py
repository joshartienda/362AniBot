import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load env vars from a local .env if present
load_dotenv()

app = Flask(__name__, static_folder="../public", static_url_path="")
CORS(app)

try:
    from openai import OpenAI
    _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception as _e:  # Defer import errors to runtime responses
    _client = None


@app.route("/")
def root():
    # Serve the starter frontend
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Proxy a chat completion to OpenAI.

    Expects JSON: { messages: [...], model?, temperature?, max_tokens? }
    """
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
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
        }
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
