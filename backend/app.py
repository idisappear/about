import os
import re
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
KB_DIR = Path(os.getenv("KB_DIR", "knowledge_base"))
TOP_K_SNIPPETS = int(os.getenv("TOP_K_SNIPPETS", "4"))
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://idisappear.github.io,http://localhost:5173,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "who",
    "with",
    "you",
    "your",
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


def _extract_chat_completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    content = getattr(message, "content", "") if message else ""
    return content.strip() if isinstance(content, str) else ""


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{2,}", text.lower()) if t not in STOPWORDS]


def _load_kb_snippets() -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    if not KB_DIR.exists():
        return snippets

    for path in sorted(KB_DIR.glob("**/*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw:
            continue
        for block in re.split(r"\n\s*\n", raw):
            clean = " ".join(block.split()).strip()
            if len(clean) < 25:
                continue
            snippets.append({"source": str(path.relative_to(KB_DIR)), "text": clean})
    return snippets


KB_SNIPPETS = _load_kb_snippets()


def _retrieve_context(query: str, top_k: int = TOP_K_SNIPPETS) -> list[dict[str, str]]:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return KB_SNIPPETS[:top_k]

    scored: list[tuple[float, dict[str, str]]] = []
    for snip in KB_SNIPPETS:
        s_tokens = set(_tokenize(snip["text"]))
        if not s_tokens:
            continue
        overlap = q_tokens & s_tokens
        if not overlap:
            continue
        score = len(overlap) / (len(q_tokens) ** 0.5)
        scored.append((score, snip))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        return [item[1] for item in scored[:top_k]]

    # Fallback for broad questions: prioritize project snippets, then any snippets.
    query_l = query.lower()
    if any(term in query_l for term in {"project", "projects", "portfolio", "work", "built"}):
        project_snips = [s for s in KB_SNIPPETS if "project" in s["source"].lower()]
        if project_snips:
            return project_snips[:top_k]

    return KB_SNIPPETS[:top_k]


def _build_context_block(snippets: list[dict[str, str]]) -> str:
    if not snippets:
        return "No relevant knowledge-base snippets were retrieved."

    lines = []
    for idx, snip in enumerate(snippets, start=1):
        lines.append(f"[{idx}] source={snip['source']}\n{snip['text']}")
    return "\n\n".join(lines)


def _extract_project_names_from_kb(limit: int = 3) -> list[str]:
    names: list[str] = []
    pattern = re.compile(r"^\s{0,3}#{1,6}\s+\d+\)\s*(.+?)\s*$")

    project_file = KB_DIR / "projects.md"
    if project_file.exists():
        raw = project_file.read_text(encoding="utf-8", errors="ignore")
        for raw_line in raw.splitlines():
            m = pattern.match(raw_line)
            if m:
                name = m.group(1).strip()
                if name and name not in names:
                    names.append(name)
            if len(names) >= limit:
                break
    return names[:limit]


@app.get("/health")
def health() -> Any:
    return jsonify(
        {
            "ok": True,
            "kb_snippets": len(KB_SNIPPETS),
            "kb_sources": sorted({s["source"] for s in KB_SNIPPETS}),
        }
    )


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

    latest_user_message = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), str):
            latest_user_message = m.get("content", "").strip()
            if latest_user_message:
                break

    retrieved = _retrieve_context(latest_user_message)
    context_block = _build_context_block(retrieved)

    query_l = latest_user_message.lower()
    if any(k in query_l for k in {"top 3 projects", "name top 3 projects", "top three projects"}):
        names = _extract_project_names_from_kb(limit=3)
        if names:
            bullet_lines = "\n".join(f"- {n}" for n in names)
            return (
                jsonify(
                    {
                        "reply": (
                            "Top 3 projects from the knowledge base:\n"
                            f"{bullet_lines}"
                        )
                    }
                ),
                200,
                _cors_headers(origin),
            )

    input_items = [
        {
            "role": "system",
            "content": (
                "You are the website owner's assistant. Rules:\n"
                "1) Use ONLY the provided knowledge-base context.\n"
                "2) Avoid generic filler and broad advice.\n"
                "3) If context is missing, say exactly what is missing and ask one specific follow-up question.\n"
                "4) Keep response concise (max 6 sentences).\n"
                "5) When possible, include source references like [1], [2].\n"
                "6) If asked about projects/famous/notable work and project names exist in context, list those names directly.\n"
                "7) Do NOT answer with 'context does not specify' when project snippets are present."
            ),
        },
        {
            "role": "system",
            "content": f"Knowledge base context:\n{context_block}",
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
        if hasattr(client, "responses"):
            response = client.responses.create(model=model, input=input_items)
            reply = _extract_output_text(response) or "I could not generate a response."
        else:
            completion = client.chat.completions.create(
                model=model,
                messages=input_items,
            )
            reply = _extract_chat_completion_text(completion) or "I could not generate a response."
        return (jsonify({"reply": reply}), 200, _cors_headers(origin))
    except Exception as exc:  # pragma: no cover
        return (jsonify({"error": str(exc)}), 500, _cors_headers(origin))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
