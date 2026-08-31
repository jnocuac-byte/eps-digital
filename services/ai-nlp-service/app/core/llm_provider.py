from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv

from .logger import log_event


class LLMProviderError(Exception):
    """Error base para fallos de proveedores LLM."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class RateLimitError(LLMProviderError):
    """HTTP 429 - Cuota agotada."""

    pass


class ProviderUnavailableError(LLMProviderError):
    """HTTP 5xx o error de conexión."""

    pass


class AllProvidersFailedError(Exception):
    """Todos los proveedores fallaron."""

    def __init__(self, errors: list[LLMProviderError]):
        self.errors = errors
        summary = "; ".join(str(e) for e in errors)
        super().__init__(f"Todos los proveedores fallaron: {summary}")


class LLMProvider(ABC):
    """Interfaz abstracta para cualquier proveedor LLM."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre legible del proveedor."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Nombre del modelo usado."""
        ...

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 400,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        """
        Envía messages y retorna el texto de respuesta.

        Raises:
            RateLimitError: si el proveedor retorna 429.
            ProviderUnavailableError: si hay error 5xx o de conexión.
            LLMProviderError: para otros errores del proveedor.
        """
        ...


class GroqProvider(LLMProvider):
    """Proveedor Groq (GPT-OSS-120B)."""

    def __init__(self, api_key: str):
        from groq import Groq

        self._client = Groq(api_key=api_key, timeout=30.0)
        self._model = "openai/gpt-oss-120b"

    @property
    def name(self) -> str:
        return "groq"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 400,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            _raise_provider_error("groq", exc)

        if not response.choices:
            raise LLMProviderError("groq", "Respuesta sin choices")
        return response.choices[0].message.content or ""


class GeminiProvider(LLMProvider):
    """Proveedor Google Gemini (Flash)."""

    def __init__(self, api_key: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = "gemini-3.6-flash"

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 400,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        system_msg = ""
        contents: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        if not contents:
            raise LLMProviderError("gemini", "No hay mensajes de usuario para procesar")

        config: dict[str, Any] = {"max_output_tokens": max_tokens}
        if temperature is not None:
            config["temperature"] = temperature
        if system_msg.strip():
            config["system_instruction"] = system_msg.strip()

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            _raise_provider_error("gemini", exc)

        if not response.text:
            raise LLMProviderError("gemini", "Respuesta vacía")
        return response.text


class CerebrasProvider(LLMProvider):
    """Proveedor Cerebras AI (GPT-OSS-120B)."""

    def __init__(self, api_key: str):
        from cerebras.cloud.sdk import Cerebras

        self._client = Cerebras(api_key=api_key)
        self._model = "gpt-oss-120b"

    @property
    def name(self) -> str:
        return "cerebras"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 400,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            _raise_provider_error("cerebras", exc)

        if not response.choices:
            raise LLMProviderError("cerebras", "Respuesta sin choices")
        return response.choices[0].message.content or ""


class MistralProvider(LLMProvider):
    """Proveedor Mistral AI."""

    def __init__(self, api_key: str):
        try:
            from mistralai import MistralClient as _MistralClient
        except ImportError:
            try:
                from mistralai.client import MistralClient as _MistralClient
            except ImportError:
                raise LLMProviderError(
                    "mistral",
                    "No se pudo importar el SDK de Mistral. "
                    "Verifica que mistralai esté instalado correctamente.",
                )
        self._client = _MistralClient(api_key=api_key)
        self._model = "mistral-small-latest"

    @property
    def name(self) -> str:
        return "mistral"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 400,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            response = self._client.chat.complete(**kwargs)
        except Exception as exc:
            _raise_provider_error("mistral", exc)

        if not response.choices:
            raise LLMProviderError("mistral", "Respuesta sin choices")
        return response.choices[0].message.content or ""


def _raise_provider_error(provider: str, exc: Exception) -> None:
    """Clasifica una excepción del SDK y lanza el error correspondiente."""
    exc_str = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)

    if status == 429 or "rate" in exc_str or "limit" in exc_str:
        raise RateLimitError(provider, str(exc)) from exc
    if status and isinstance(status, int) and 500 <= status < 600:
        raise ProviderUnavailableError(provider, str(exc)) from exc
    if "connect" in exc_str or "timeout" in exc_str:
        raise ProviderUnavailableError(provider, str(exc)) from exc
    raise LLMProviderError(provider, str(exc)) from exc


def _build_providers() -> list[LLMProvider]:
    """Construye la lista de proveedores disponibles según las env vars."""
    load_dotenv()
    providers: list[LLMProvider] = []

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        providers.append(GeminiProvider(api_key=gemini_key))

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        providers.append(GroqProvider(api_key=groq_key))

    cerebras_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        providers.append(CerebrasProvider(api_key=cerebras_key))

    mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if mistral_key:
        try:
            providers.append(MistralProvider(api_key=mistral_key))
        except LLMProviderError as exc:
            log_event("LLM", "INIT", "warning", f"Mistral omitido: {exc}")

    return providers


class LLMProviderFactory:
    """
    Factory con fallback que intenta proveedores en orden de prioridad.
    Si un proveedor falla con 429 o 5xx, pasa al siguiente automáticamente.
    """

    def __init__(self, providers: list[LLMProvider] | None = None):
        self._providers = providers or _build_providers()
        if not self._providers:
            raise ValueError(
                "No hay proveedores LLM configurados. "
                "Configura al menos GEMINI_API_KEY o GROQ_API_KEY."
            )
        log_event(
            "LLM", "INIT", "info",
            f"Factory inicializado con {len(self._providers)} proveedores: "
            f"{[p.name for p in self._providers]}"
        )

    @property
    def provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 400,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> tuple[str, str]:
        """
        Intenta completar el chat con fallback automático.

        Returns:
            tuple(respuesta_texto, nombre_proveedor_usado)

        Raises:
            AllProvidersFailedError si todos los proveedores fallaron.
        """
        errors: list[LLMProviderError] = []

        for provider in self._providers:
            try:
                texto = provider.complete(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )
                log_event("LLM", "SUCCESS", "info", f"Respuesta exitosa via {provider.name} ({provider.model})")
                return texto, provider.name
            except (RateLimitError, ProviderUnavailableError) as exc:
                log_event(
                    "LLM", "FALLBACK", "warning",
                    f"Proveedor {provider.name} falló: {exc}. Intentando siguiente..."
                )
                errors.append(exc)
                continue
            except LLMProviderError as exc:
                log_event("LLM", "ERROR", "error", f"Error no recuperable en {provider.name}: {exc}")
                errors.append(exc)
                continue

        raise AllProvidersFailedError(errors)


_factory: LLMProviderFactory | None = None


def get_llm_factory() -> LLMProviderFactory:
    """Retorna la instancia global del factory."""
    if _factory is None:
        raise RuntimeError(
            "LLMProviderFactory no inicializado. Llama init_llm_factory() primero."
        )
    return _factory


def init_llm_factory() -> LLMProviderFactory:
    """Inicializa el factory global (llamar en el lifespan de FastAPI)."""
    global _factory
    _factory = LLMProviderFactory()
    return _factory
