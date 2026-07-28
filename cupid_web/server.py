import json
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app import load_mock_profiles, run_comparison
from providers import get_llm_provider
from tools import get_user_profile

WEB_ROOT = Path(__file__).resolve().parent
app = Flask(__name__)


def _api_error(code, message, status):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


@app.get("/")
def index():
    profiles = load_mock_profiles()
    template = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    options = "".join(
        f'<option value="{profile["id"]}">{profile["id"]} · {profile["name"]}</option>'
        for profile in profiles
    )
    bootstrap = json.dumps(
        [
            {
                "id": profile["id"],
                "name": profile["name"],
                "age": profile["age"],
                "location": profile["location"],
            }
            for profile in profiles
        ],
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    return render_template_string(
        template.replace("<!-- PROFILE_OPTIONS -->", options).replace(
            "__PROFILE_BOOTSTRAP__", bootstrap
        )
    )


@app.get("/<path:filename>")
def static_file(filename):
    if filename not in {"styles.css", "app.js"}:
        return _api_error("NOT_FOUND", "Không tìm thấy tài nguyên", 404)
    return send_from_directory(WEB_ROOT, filename)


@app.post("/api/compare")
def compare():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _api_error("INVALID_INPUT", "Body phải là JSON object", 400)

    user_id = payload.get("user_id")
    message = payload.get("message")
    if (
        not isinstance(user_id, str)
        or not isinstance(message, str)
        or not message.strip()
        or len(message) > 1000
    ):
        return _api_error("INVALID_INPUT", "user_id và message không hợp lệ", 400)

    profile = get_user_profile(user_id)
    if not profile["ok"]:
        return jsonify({"ok": False, "error": profile["error"]}), 404

    data = run_comparison(message.strip(), get_llm_provider(), user_id)
    react_error = data["react"].get("error") or {}
    if react_error.get("code") == "PROVIDER_ERROR":
        return jsonify({"ok": False, "error": react_error}), 502
    return jsonify({"ok": True, "data": data})


@app.errorhandler(Exception)
def unexpected_error(error):
    if app.config.get("TESTING"):
        raise error
    return _api_error("INTERNAL_ERROR", "Không thể xử lý yêu cầu", 500)


if __name__ == "__main__":
    app.run(port=8000, debug=False)
