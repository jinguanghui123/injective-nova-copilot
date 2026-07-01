"""Thin Ollama client. Direct HTTP via httpx — no extra dep.

The Ollama server exposes a stable HTTP API at /api/chat. We use JSON mode
(`format: "json"`) so the model's response is forced to be valid JSON, which
we then validate with Pydantic at the boundary.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


class LLMError(RuntimeError):
    """Raised when the LLM is unreachable or returns malformed output."""


class OllamaClient:
    """Minimal async client for Ollama's /api/chat endpoint."""

    def __init__(self, *, host: str | None = None, model: str | None = None, timeout: float = 60.0) -> None:
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.environ.get("LLM_MODEL", "qwen2.5:latest")
        self.timeout = timeout

    async def chat_json(self, *, system: str, user: str) -> dict[str, Any]:
        """Send a system+user turn, force JSON mode, return parsed JSON.

        Raises LLMError on connection failure or non-JSON response.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},  # low temp for deterministic structured output
        }
        try:
            # trust_env=False so httpx ignores HTTP_PROXY/HTTPS_PROXY env vars.
            # This box runs a global proxy at 127.0.0.1:5780 which 502s on localhost.
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as http:
                resp = await http.post(f"{self.host}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"ollama request failed: {exc!r}") from exc

        content = data.get("message", {}).get("content", "")
        if not content:
            raise LLMError(f"ollama returned empty content: {data!r}")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"ollama returned non-JSON content: {content[:200]!r}") from exc

    async def ping(self) -> bool:
        """Cheap health check — does the server respond?"""
        try:
            async with httpx.AsyncClient(timeout=3.0, trust_env=False) as http:
                resp = await http.get(f"{self.host}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
