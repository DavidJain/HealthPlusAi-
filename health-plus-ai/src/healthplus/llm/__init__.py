"""LLM adapter layer: the only modules that talk to external LLM APIs.

Keeping each SDK behind one class means the rest of the application depends
on our contract (stream_reply), not on any vendor's SDK — swapping models or
mocking in tests touches exactly one seam.

Imports are lazy: each vendor SDK is heavy (Anthropic ~6 s, OpenAI ~3 s on
a cold start), so a client's module is only imported when that client is
first used. `from healthplus.llm import OpenRouterClient` still works.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

_CLIENT_MODULES = {
    "ClaudeClient": "healthplus.llm.claude_client",
    "OpenAIClient": "healthplus.llm.openai_client",
    "OpenRouterClient": "healthplus.llm.openrouter_client",
}

__all__ = list(_CLIENT_MODULES)

if TYPE_CHECKING:  # pragma: no cover - for type checkers and IDEs only
    from healthplus.llm.claude_client import ClaudeClient
    from healthplus.llm.openai_client import OpenAIClient
    from healthplus.llm.openrouter_client import OpenRouterClient


def __getattr__(name: str) -> Any:
    module = _CLIENT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)
