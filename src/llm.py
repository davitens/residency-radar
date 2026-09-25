from __future__ import annotations

import os

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "llama3.2")


def chat(system: str, user: str, *, model: str | None = None, provider: str | None = None,
         base_url: str | None = None, api_key: str | None = None) -> str:
    """Call a local Ollama daemon (default) or any OpenAI-compatible endpoint."""
    import httpx

    provider = provider or os.environ.get("LLM_PROVIDER", "ollama")
    model = model or DEFAULT_MODEL
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    if provider == "ollama":
        base = (base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        # `format: json` constrains output to valid JSON; callers all want JSON objects.
        resp = httpx.post(
            f"{base}/api/chat",
            json={"model": model, "stream": False, "format": "json", "messages": messages,
                  "options": {"temperature": 0}},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    base = (base_url or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
    key = api_key or os.environ.get("LLM_API_KEY", "")
    resp = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": messages, "response_format": {"type": "json_object"}},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def available(*, provider: str | None = None, base_url: str | None = None) -> bool:
    """Cheap reachability probe so the pipeline can skip LLM work when no daemon is running."""
    provider = provider or os.environ.get("LLM_PROVIDER", "ollama")
    if provider != "ollama":
        return bool(os.environ.get("LLM_API_KEY"))
    import httpx

    base = (base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    try:
        return httpx.get(f"{base}/api/tags", timeout=3).status_code == 200
    except Exception:
        return False
