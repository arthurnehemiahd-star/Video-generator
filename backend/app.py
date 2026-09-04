"""
backend/app.py
---------------
JSON API for the assistant and AI video generator.

The frontend is a separate static app that talks to this backend
using fetch().

Run with:
    python -m backend.app

API root:
    http://localhost:5000
"""

import os
from functools import wraps

from flask import Flask, request, jsonify, send_file
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired,
)

from ai_brain import config, memory, commands, ai_client, auth, files
from ai_brain.creator import video_generator


app = Flask(__name__)


# ============================================================
# AUTHENTICATION
# ============================================================

SECRET_KEY = (
    os.environ.get("FLASK_SECRET_KEY")
    or "dev-only-change-me"
)

TOKEN_MAX_AGE = 60 * 60 * 24 * 7

_signer = URLSafeTimedSerializer(
    SECRET_KEY,
    salt="personal-ai-auth",
)


# ============================================================
# CORS
# ============================================================

FRONTEND_ORIGIN = os.environ.get(
    "FRONTEND_ORIGIN",
    "*",
)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = (
        FRONTEND_ORIGIN
    )

    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization"
    )

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, OPTIONS"
    )

    return response


@app.route(
    "/api/<path:_any>",
    methods=["OPTIONS"],
)
def cors_preflight(_any):
    return "", 204


# ============================================================
# TOKEN FUNCTIONS
# ============================================================

def _make_token() -> str:
    return _signer.dumps({
        "authed": True
    })


def _token_is_valid(token: str) -> bool:
    try:
        _signer.loads(
            token,
            max_age=TOKEN_MAX_AGE,
        )
        return True

    except (
        BadSignature,
        SignatureExpired,
    ):
        return False


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if not auth.is_configured():
            return view(*args, **kwargs)

        header = request.headers.get(
            "Authorization",
            "",
        )

        token = (
            header
            .removeprefix("Bearer ")
            .strip()
        )

        if not token or not _token_is_valid(token):
            return jsonify({
                "error": "unauthorized"
            }), 401

        return view(*args, **kwargs)

    return wrapped


# ============================================================
# SESSION
# ============================================================

@app.route(
    "/api/session",
    methods=["GET"],
)
def api_session():

    return jsonify({
        "auth_required": auth.is_configured()
    })


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/api/login",
    methods=["POST"],
)
def api_login():

    password = (
        (request.json or {})
        .get("password", "")
    )

    if not auth.is_configured():

        return jsonify({
            "token": None,
            "auth_required": False,
        })

    if not auth.verify(password):

        return jsonify({
            "error": "incorrect password"
        }), 401

    return jsonify({
        "token": _make_token()
    })


# ============================================================
# CHAT
# ============================================================

@app.route(
    "/api/message",
    methods=["POST"],
)
@require_auth
def api_message():

    text = (
        (request.json or {})
        .get("text", "")
        .strip()
    )

    if not text:

        return jsonify({
            "error": "empty message"
        }), 400

    if commands.is_command(text):

        reply = commands.run_command(text)

        return jsonify({
            "reply": reply
        })

    history = memory.load_history()

    history = memory.append_message(
        history,
        "user",
        text,
    )

    reply = ai_client.get_ai_reply(
        history
    )

    memory.append_message(
        history,
        "assistant",
        reply,
    )

    return jsonify({
        "reply": reply
    })


# ============================================================
# CHAT HISTORY
# ============================================================

@app.route(
    "/api/history",
    methods=["GET"],
)
@require_auth
def api_history():

    return jsonify({
        "history": memory.load_history()
    })


# ============================================================
# PROJECTS
# ============================================================

@app.route(
    "/api/projects",
    methods=["GET"],
)
@require_auth
def api_projects():

    config.PROJECTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    project_list = []

    for p in sorted(
        config.PROJECTS_DIR.iterdir()
    ):

        if not p.is_dir():
            continue

        outputs = [
            f.name
            for f in p.glob("*.mp4")
        ]

        project_list.append({
            "name": p.name,
            "outputs": outputs,
        })

    return jsonify({
        "projects": project_list
    })


# ============================================================
# AI VIDEO GENERATOR
# ============================================================

@app.route(
    "/api/generate-video",
    methods=["POST"],
)
@require_auth
def api_generate_video():

    data = request.get_json(
        silent=True
    ) or {}

    description = str(
        data.get("description", "")
    ).strip()

    duration = data.get(
        "duration",
        10,
    )

    if not description:

        return jsonify({
            "success": False,
            "error": "Video description cannot be empty."
        }), 400

    try:

        duration = int(duration)

    except (
        TypeError,
        ValueError,
    ):

        return jsonify({
            "success": False,
            "error": "Video duration must be a number."
        }), 400

    if duration < 5:

        return jsonify({
            "success": False,
            "error": "Video duration must be at least 5 seconds."
        }), 400

    if duration > 120:

        return jsonify({
            "success": False,
            "error": "Video duration cannot exceed 120 seconds."
        }), 400

    try:

        final_path = video_generator.generate_video(
            description=description,
            duration=duration,
        )

        project_name = final_path.parent.name
        filename = final_path.name

        return jsonify({
            "success": True,
            "project": project_name,
            "filename": filename,
            "download_url": (
                f"/api/download/"
                f"{project_name}/"
                f"{filename}"
            ),
        })

    except Exception as e:

        print(
            "VIDEO GENERATION ERROR:",
            repr(e),
        )

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# ============================================================
# DOWNLOAD
# ============================================================

@app.route(
    "/api/download/<project>/<filename>",
    methods=["GET"],
)
def api_download(
    project,
    filename,
):

    if auth.is_configured():

        token = (
            request.args.get("token")
            or
            request.headers.get(
                "Authorization",
                "",
            ).removeprefix("Bearer ").strip()
        )

        if (
            not token
            or not _token_is_valid(token)
        ):

            return jsonify({
                "error": "unauthorized"
            }), 401

    safe_path = files._resolve_safe(
        f"{project}/{filename}"
    )

    if not safe_path.exists():

        return jsonify({
            "error": "not found"
        }), 404

    return send_file(
        safe_path,
        as_attachment=True,
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/api/health",
    methods=["GET"],
)
def api_health():

    return jsonify({
        "status": "ok",
        "assistant_name": config.ASSISTANT_NAME,
    })


# ============================================================
# JSON ERROR HANDLING
# ============================================================

@app.errorhandler(404)
def handle_404(error):

    return jsonify({
        "success": False,
        "error": "API route not found.",
    }), 404


@app.errorhandler(405)
def handle_405(error):

    return jsonify({
        "success": False,
        "error": "Method not allowed for this API route.",
    }), 405


@app.errorhandler(500)
def handle_500(error):

    return jsonify({
        "success": False,
        "error": "Internal server error.",
    }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=False,
        host="127.0.0.1",
        port=5000,
    )
