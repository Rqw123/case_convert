from __future__ import annotations

import json
import time
from typing import Any

import httpx


class DeepSeekClient:
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.0, timeout_seconds: int = 60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    async def chat(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        return {
            "request_payload": payload,
            "response_text": content,
            "response_json": body,
            "http_status": response.status_code,
            "token_usage": body.get("usage", {}),
            "latency_ms": latency_ms,
        }


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
