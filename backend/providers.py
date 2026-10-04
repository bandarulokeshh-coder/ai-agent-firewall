"""AI provider abstraction: Ollama + OpenAI-compatible backends.

The firewall NEVER talks to a vendor SDK directly — it goes through these
adapters so the enforcement layer stays vendor-neutral.
"""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import httpx


class AIProviderError(Exception):
    """Raised when a provider call fails."""


class AIProvider(ABC):
    """Base class for all AI providers."""

    name: str = "base"

    @abstractmethod
    async def chat(self, prompt: str, model: str, system: str | None = None) -> dict:
        """Send a prompt to the provider. Returns {"text", "model", "duration_ms"}."""


class OllamaProvider(AIProvider):
    """Local Ollama server (default, zero external data flow)."""

    name = "ollama"

    def __init__(self, base_url: str | None = None, default_model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.default_model = default_model or os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    async def chat(self, prompt: str, model: str | None = None, system: str | None = None) -> dict:
        model = model or self.default_model
        started = time.time()
        payload: Dict[str, any] = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=3.0)) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                # Ollama returns 404 when the model tag isn't pulled — surface a clear error.
                if resp.status_code == 404:
                    raise AIProviderError(
                        f"Ollama model '{model}' is not installed. Available: "
                        f"{', '.join(await self.list_models()) or 'none'.strip()}). Pull it with: ollama pull {model}"
                    )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Ollama at {self.base_url} failed: {exc}") from exc
        return {
            "text": data.get("response", ""),
            "model": model,
            "provider": self.name,
            "duration_ms": int((time.time() - started) * 1000),
        }

    async def list_models(self) -> List[str]:
        """Return model tags currently installed on the Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
        except httpx.HTTPError:
            return []


class OpenAICompatibleProvider(AIProvider):
    """OpenAI-compatible API (OpenAI, Azure, LM Studio, vLLM, etc.).

    The API key is read from the environment — never passed from the frontend.
    """

    name = "openai"

    def __init__(self, base_url: str | None = None, api_key: str | None = None, default_model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.default_model = default_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def chat(self, prompt: str, model: str | None = None, system: str | None = None) -> dict:
        if not self.api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")
        model = model or self.default_model
        started = time.time()
        messages: List[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=3.0)) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": model, "messages": messages},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise AIProviderError(f"OpenAI-compatible API failed: {exc}") from exc
        text = ""
        choices = data.get("choices") or []
        if choices:
            text = choices[0].get("message", {}).get("content", "")
        return {
            "text": text,
            "model": model,
            "provider": self.name,
            "duration_ms": int((time.time() - started) * 1000),
        }


_PROVIDERS: Dict[str, type] = {
    "ollama": OllamaProvider,
    "openai": OpenAICompatibleProvider,
}


def get_provider(name: str) -> AIProvider:
    """Factory: resolve a provider by name (never imported by frontend)."""
    cls = _PROVIDERS.get((name or "ollama").lower())
    if cls is None:
        raise AIProviderError(f"Unknown provider '{name}'. Available: {list(_PROVIDERS)}")
    return cls()


def list_providers() -> List[dict]:
    """Provider registry info for the frontend (no secrets)."""
    configured = []
    for key, cls in _PROVIDERS.items():
        configured.append({
            "name": key,
            "default_model": getattr(cls(), "default_model", None),
            "configured": key == "ollama" or bool(os.getenv("OPENAI_API_KEY")),
        })
    return configured


async def list_provider_models(name: str) -> List[str]:
    """Installed model tags for a provider (Ollama only; others return [])."""
    try:
        provider = get_provider(name)
    except AIProviderError:
        return []
    if isinstance(provider, OllamaProvider):
        return await provider.list_models()
    return []