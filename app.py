"""
backend/app.py
---------------
A pure JSON API for the assistant — no HTML rendering here at all. The
frontend/ folder is a fully separate, static HTML/JS app that talks to
this over fetch(). That split means:
  - the backend can run on a server, a Raspberry Pi, wherever
  - the frontend is just static files — open the HTML directly, or
    serve it from any static host (nginx, GitHub Pages, etc.)
  - you could swap the frontend for a mobile app later and this API
    wouldn't need to change

Auth here is a signed token (not a cookie session) specifically because
cookies get messy once frontend and backend are different origins/ports.
Login returns a token; the frontend stores it (localStorage) and sends
it as `Authorization: Bearer <token>` on every request after that.

Run with:  python -m backend.app
API root:  http://localhost:5000
"""

import os
from functools import wraps
from flask import Flask, request, jsonify, send_file
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from ai_brain import config, memory, commands, ai_client, auth, files
from ai_brain.creator import video_generator

app = Flask(__name__)

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or "dev-only-change-me"  # see README before hosting beyond localhost
TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
_signer = URLSafeTimedSerializer(SECRET_KEY, salt="video-generator-auth")

# Frontend origin(s) allowed to call this API. Override with
# FRONTEND_ORIGIN if you're serving the frontend from somewhere other
# than the default local dev setup.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = FRONTEND_ORIGIN
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def cors_preflight(_any):
    return "", 204


def _make_token() -> str:
    return _signer.dumps({"authed": True})


def _token_is_valid(token: str) -> bool:
    try:
        _signer.loads(token, max_age=TOKEN_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not auth.is_configured():
            return view(*args, **kwargs)  # no password set — API is open, see auth.py
        header = request.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip()
        if not token or not _token_is_valid(token):
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)
    return wrapped


@app.route("/api/session", methods=["GET"])
def api_session():
    """Frontend calls this on load to know whether a login screen is needed."""
    return jsonify({"auth_required": auth.is_configured()})


@app.route("/api/login", methods=["POST"])
def api_login():
    if not auth.is_configured():
        return jsonify({"token": None, "auth_required": False})

    password = (request.json or {}).get("password", "")
    if not auth.verify(password):
        return jsonify({"error": "incorrect password"}), 401
    return jsonify({"token": _make_token()})


@app.route("/api/message", methods=["POST"])
@require_auth
def api_message():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "empty message"}), 400

    if commands.is_command(text):
        reply = commands.run_command(text)
        return jsonify({"reply": reply})

    history = memory.load_history()
    history = memory.append_message(history, "user", text)
    reply = ai_client.get_ai_reply(history)
    memory.append_message(history, "assistant", reply)
    return jsonify({"reply": reply})


@app.route("/api/history", methods=["GET"])
@require_auth
def api_history():
    return jsonify({"history": memory.load_history()})


@app.route("/api/projects", methods=["GET"])
@require_auth
def api_projects():
    config.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    project_list = []
    for p in sorted(config.PROJECTS_DIR.iterdir()):
        if not p.is_dir():
            continue
        outputs = [f.name for f in p.glob("*.mp4")]
        project_list.append({"name": p.name, "outputs": outputs})
    return jsonify({"projects": project_list})


@app.route("/api/download/<project>/<filename>", methods=["GET"])
def api_download(project, filename):
    # Browser navigation (clicking a download link) can't set an
    # Authorization header, so this endpoint also accepts the token as
    # a query param: /api/download/x/y.mp4?token=...
    if auth.is_configured():
        token = request.args.get("token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token or not _token_is_valid(token):
            return jsonify({"error": "unauthorized"}), 401

    safe_path = files._resolve_safe(f"{project}/{filename}")
    if not safe_path.exists():
        return jsonify({"error": "not found"}), 404
    return send_file(safe_path, as_attachment=True)


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "assistant_name": config.ASSISTANT_NAME})


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
