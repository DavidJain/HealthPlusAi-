"""OpenRouterClient construction and streaming — no network, no real key."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from healthplus.core.exceptions import ConfigurationError
from healthplus.llm import OpenRouterClient


def _settings(api_key=None):
    return SimpleNamespace(
        app_name="HealthPlus AI",
        openai_model="gpt-4o-mini",
        claude_max_tokens=1024,
        openrouter_api_key=api_key,
        openrouter_model="inclusionai/ling-3.2-flash:free",
        openrouter_base_url="https://openrouter.ai/api/v1",
    )


def _chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class _FakeSDK:
    """Records the create() call and replays a canned stream."""

    def __init__(self, chunks):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._chunks = chunks

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self._chunks)


def test_missing_api_key_fails_fast():
    with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(settings=_settings(api_key=None))


def test_uses_openrouter_model_not_openai_model():
    fake = _FakeSDK([_chunk("ok")])
    client = OpenRouterClient(settings=_settings(), client=fake)
    list(client.stream_reply("sys", [{"role": "user", "content": "hi"}]))
    assert fake.calls[0]["model"] == "inclusionai/ling-3.2-flash:free"
    assert fake.calls[0]["messages"][0] == {"role": "system", "content": "sys"}


def test_sends_fallback_models_and_disables_reasoning():
    settings = _settings()
    settings.openrouter_fallback_models = ["a/b:free", "inclusionai/ling-3.2-flash:free"]
    fake = _FakeSDK([_chunk("ok")])
    list(OpenRouterClient(settings=settings, client=fake).stream_reply("sys", []))
    body = fake.calls[0]["extra_body"]
    # Primary first, duplicates of the primary dropped from the fallbacks.
    assert body["models"] == ["inclusionai/ling-3.2-flash:free", "a/b:free"]
    assert body["reasoning"] == {"enabled": False}


def test_data_collection_deny_is_opt_in():
    fake = _FakeSDK([_chunk("ok")])
    list(OpenRouterClient(settings=_settings(), client=fake).stream_reply("sys", []))
    assert "provider" not in fake.calls[0]["extra_body"]

    settings = _settings()
    settings.openrouter_deny_data_collection = True
    fake = _FakeSDK([_chunk("ok")])
    list(OpenRouterClient(settings=settings, client=fake).stream_reply("sys", []))
    assert fake.calls[0]["extra_body"]["provider"] == {"data_collection": "deny"}


def test_stream_skips_chunks_without_choices():
    # OpenRouter interleaves usage / keep-alive chunks with empty choices.
    fake = _FakeSDK([_chunk("Hel"), SimpleNamespace(choices=[]), _chunk(None), _chunk("lo")])
    client = OpenRouterClient(settings=_settings(), client=fake)
    assert "".join(client.stream_reply("sys", [])) == "Hello"
