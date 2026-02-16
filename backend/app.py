import os
from typing import Any

from flask import Flask, jsonify, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://idisappear.github.io,http://localhost:5173,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
}


def _cors_headers(origin: str | None) -> dict[str, str]:
    headers = {
        "Vary": "Origin",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
    if origin and origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
    return headers


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", "") == "output_text":
                text = getattr(content, "text", "")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    return "\n".join(parts).strip()


@app.get("/health")
def health() -> Any:
    return jsonify({"ok": True})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat() -> Any:
    origin = request.headers.get("Origin")

    if request.method == "OPTIONS":
        return ("", 204, _cors_headers(origin))

    if origin and origin not in ALLOWED_ORIGINS:
        return (jsonify({"error": "Origin not allowed"}), 403, _cors_headers(origin))

    if not OPENAI_API_KEY:
        return (
            jsonify({"error": "Server missing OPENAI_API_KEY"}),
            500,
            _cors_headers(origin),
        )

    payload = request.get_json(silent=True) or {}
    model = payload.get("model") or DEFAULT_MODEL
    messages = payload.get("messages") or []

    if not isinstance(messages, list) or not messages:
        return (
            jsonify({"error": "messages must be a non-empty array"}),
            400,
            _cors_headers(origin),
        )

    input_items = [
        {
            "role": "system",
            "content": "You are the website owner's AI assistant. Keep responses concise and useful.",
        }
    ]

    for m in messages[-12:]:
        role = m.get("role") if isinstance(m, dict) else None
        content = m.get("content") if isinstance(m, dict) else None
        if role in {"user", "assistant", "system"} and isinstance(content, str) and content.strip():
            input_items.append({"role": role, "content": content.strip()})

    if len(input_items) < 2:
        return (
            jsonify({"error": "No valid messages to send"}),
            400,
            _cors_headers(origin),
        )

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(model=model, input=input_items)
        reply = _extract_output_text(response) or "I could not generate a response."
        return (jsonify({"reply": reply}), 200, _cors_headers(origin))
    except Exception as exc:  # pragma: no cover
        return (jsonify({"error": str(exc)}), 500, _cors_headers(origin))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
