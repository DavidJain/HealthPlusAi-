"""OpenRouter API adapter.

OpenRouter exposes an OpenAI-compatible Chat Completions API in front of
many model vendors, so this is the OpenAI adapter pointed at a different
base URL with a different key and model. Streaming, error translation and
the stream_reply contract are inherited unchanged.
"""

from __future__ import annotations

import httpx
import openai as openai_sdk

from healthplus.config import Settings, get_settings
from healthplus.core.exceptions import ConfigurationError
from healthplus.llm.claude_client import _get_ca_bundle
from healthplus.llm.openai_client import OpenAIClient


class OpenRouterClient(OpenAIClient):
    """Chat via OpenRouter (default model: a free inclusionAI Ling model)."""

    label = "OpenRouter"

    def __init__(
        self,
        settings: Settings | None = None,
        client: openai_sdk.OpenAI | None = None,
    ) -> None:
        settings = settings or get_settings()
        if client is None:
            if settings.openrouter_api_key is None:
                raise ConfigurationError(
                    "OPENROUTER_API_KEY is not set. Add it to your .env file — "
                    "the chat feature cannot start without it."
                )
            client = openai_sdk.OpenAI(
                api_key=settings.openrouter_api_key.get_secret_value(),
                base_url=settings.openrouter_base_url,
                http_client=httpx.Client(verify=_get_ca_bundle()),
                # Optional attribution headers OpenRouter uses for its
                # app rankings; harmless if ignored.
                default_headers={"X-Title": settings.app_name},
            )
        super().__init__(settings=settings, client=client)
        self._model = settings.openrouter_model
