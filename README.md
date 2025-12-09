# 362AniBot
Web application with Anime recommendations ChatBot
Made by Ian Gerodias, Josh Artienda, and Javier Lopez for CPSC 362 at CSUF

## Getting Started (Starter Web + Python Backend)

This repo now includes a minimal Flask backend that proxies ChatGPT API calls and a simple frontend chat UI.

### Project Structure
- `backend/app.py` – Flask app with `/api/chat` endpoint and static file serving.
- `backend/requirements.txt` – Python dependencies.
- `backend/.env.example` – Example environment variables.
- `public/index.html` – Starter chat interface.
- `public/styles.css` – Basic styling.
- `public/app.js` – Frontend logic to call the backend.

### Prerequisites
- Python 3.10+
- An OpenAI API key with access to Chat Completions.

### Setup
1. Create and activate a virtual environment.
   - Windows (PowerShell):
     - `python -m venv .venv`
     - `.\.venv\Scripts\Activate.ps1`
2. Install dependencies:
   - `pip install -r backend/requirements.txt`
3. Configure environment variables:
   - Copy `backend/.env.example` to `backend/.env` and set `OPENAI_API_KEY`.

### Run
- From the repo root, start the server:
  - `python backend/app.py`
- Open the app in your browser:
  - `http://localhost:5000`

### Environment Variables
- `OPENAI_API_KEY` – your OpenAI key (required)
- `OPENAI_MODEL` – optional, defaults to `gpt-4o-mini`
- `PORT` – optional, defaults to `5000`

### API: `POST /api/chat`
Request JSON:
```11
{
  "messages": [ { "role": "system|user|assistant", "content": "..." } ],
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 2000
}
```
Response JSON:
```
{ "reply": "...", "usage": { ... }, "model": "..." }
```
