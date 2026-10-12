"""LLM provider abstraction — OllamaProvider and CloudProvider with common interface."""
from __future__ import annotations
import logging
import httpx
from abc import ABC, abstractmethod
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class LLMResponse:
    def __init__(
        self,
        content: str,
        provider: str,
        model: str,
        error: str | None = None,
        fallback_from: str | None = None,
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.error = error
        self.fallback_from = fallback_from


def with_provider_fallback_notice(response: LLMResponse) -> str:
    if not response.fallback_from:
        return response.content
    return (
        f"**Provider fallback:** {response.fallback_from} was unavailable; "
        f"this response was generated with {response.provider}/{response.model}.\n\n"
        f"{response.content}"
    )


class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], system_prompt: str = "") -> LLMResponse:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str | None = None):
        self._model = model or settings.ollama_model
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._timeout = settings.ollama_timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                # Check if model (or base name) is present
                model_base = self._model.split(":")[0]
                return any(self._model in m or model_base in m for m in models)
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    async def complete(self, messages: list[dict], system_prompt: str = "") -> LLMResponse:
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(messages)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": ollama_messages,
                        "stream": False,
                        "options": {"temperature": 0.7},
                    },
                )
                if resp.status_code != 200:
                    return LLMResponse("", self.provider_name, self._model,
                                       error=f"Ollama returned HTTP {resp.status_code}")
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                return LLMResponse(content, self.provider_name, self._model)
        except httpx.TimeoutException:
            msg = (
                f"Ollama request timed out after {self._timeout}s. "
                "Long generations may need more time; try a faster local model or "
                "increase OLLAMA_TIMEOUT in the backend environment."
            )
            return LLMResponse("", self.provider_name, self._model, error=msg)
        except httpx.ConnectError:
            msg = "Cannot connect to Ollama. Ensure Ollama is running: `ollama serve`"
            return LLMResponse("", self.provider_name, self._model, error=msg)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return LLMResponse("", self.provider_name, self._model, error=str(e))


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self._model = model
        self._api_key = settings.anthropic_api_key
        self._timeout = settings.cloud_timeout

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    async def is_available(self) -> bool:
        return bool(self._api_key and len(self._api_key) > 10)

    async def complete(self, messages: list[dict], system_prompt: str = "") -> LLMResponse:
        if not self._api_key:
            return LLMResponse("", self.provider_name, self._model,
                               error="Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "max_tokens": 2048,
                        "system": system_prompt or "You are a helpful product management and growth expert.",
                        "messages": messages,
                    },
                )
                if resp.status_code != 200:
                    data = resp.json()
                    err = data.get("error", {}).get("message", f"HTTP {resp.status_code}")
                    return LLMResponse("", self.provider_name, self._model, error=f"Anthropic error: {err}")
                data = resp.json()
                content = data["content"][0]["text"]
                return LLMResponse(content, self.provider_name, self._model)
        except httpx.TimeoutException:
            return LLMResponse("", self.provider_name, self._model, error="Anthropic request timed out.")
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return LLMResponse("", self.provider_name, self._model, error=str(e))


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        self._model = model
        self._api_key = settings.openai_api_key
        self._timeout = settings.cloud_timeout

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def is_available(self) -> bool:
        return bool(self._api_key and len(self._api_key) > 10)

    async def complete(self, messages: list[dict], system_prompt: str = "") -> LLMResponse:
        if not self._api_key:
            return LLMResponse("", self.provider_name, self._model,
                               error="OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={"model": self._model, "messages": all_messages, "max_tokens": 2048},
                )
                if resp.status_code != 200:
                    data = resp.json()
                    err = data.get("error", {}).get("message", f"HTTP {resp.status_code}")
                    return LLMResponse("", self.provider_name, self._model, error=f"OpenAI error: {err}")
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return LLMResponse(content, self.provider_name, self._model)
        except httpx.TimeoutException:
            return LLMResponse("", self.provider_name, self._model, error="OpenAI request timed out.")
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return LLMResponse("", self.provider_name, self._model, error=str(e))


class ModelRouter:
    """Routes requests to the appropriate LLM provider."""

    def get_provider(self, provider: str, model: str) -> BaseLLMProvider:
        provider = provider.lower()
        if provider == "ollama":
            return OllamaProvider(model=model)
        elif provider == "anthropic":
            return AnthropicProvider(model=model)
        elif provider == "openai":
            return OpenAIProvider(model=model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def complete_with_fallback(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system_prompt: str = "",
    ) -> LLMResponse:
        selected = self.get_provider(provider, model)
        response = await selected.complete(messages, system_prompt=system_prompt)
        if not response.error or provider.lower() == "ollama":
            return response

        fallback = OllamaProvider(model=settings.ollama_model)
        if not await fallback.is_available():
            return LLMResponse(
                "",
                selected.provider_name,
                selected.model_name,
                error=f"{response.error} Ollama fallback is unavailable.",
            )

        fallback_response = await fallback.complete(messages, system_prompt=system_prompt)
        if fallback_response.error:
            return LLMResponse(
                "",
                selected.provider_name,
                selected.model_name,
                error=f"{response.error} Ollama fallback failed: {fallback_response.error}",
            )

        logger.warning(
            "Provider %s/%s failed; completed request with Ollama/%s",
            selected.provider_name,
            selected.model_name,
            fallback.model_name,
        )
        return LLMResponse(
            fallback_response.content,
            fallback.provider_name,
            fallback.model_name,
            fallback_from=f"{selected.provider_name}/{selected.model_name}",
        )

    async def get_available_models(self) -> list[dict]:
        models = []

        # Ollama models
        ollama = OllamaProvider()
        ollama_available = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        models.append({
                            "id": m["name"],
                            "name": m["name"],
                            "provider": "ollama",
                            "available": True,
                            "description": f"Local Ollama model ({m.get('size', '')})",
                        })
                    ollama_available = True
        except Exception as exc:
            logger.warning(
                "ollama_model_discovery_failed",
                extra={"exception_type": type(exc).__name__},
            )

        if not ollama_available:
            models.append({
                "id": settings.ollama_model,
                "name": settings.ollama_model,
                "provider": "ollama",
                "available": False,
                "description": "Ollama not running. Start with: ollama serve",
            })

        # Cloud models
        if settings.anthropic_api_key:
            for mid, name in [("claude-3-haiku-20240307", "Claude 3 Haiku"), ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet")]:
                models.append({"id": mid, "name": name, "provider": "anthropic", "available": True, "description": "Anthropic cloud model"})

        if settings.openai_api_key:
            for mid, name in [("gpt-4o-mini", "GPT-4o Mini"), ("gpt-4o", "GPT-4o")]:
                models.append({"id": mid, "name": name, "provider": "openai", "available": True, "description": "OpenAI cloud model"})

        return models
