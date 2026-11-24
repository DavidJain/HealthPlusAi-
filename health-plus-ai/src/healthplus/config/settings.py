"""Application configuration.

All runtime configuration is loaded from environment variables (optionally
supplied via a `.env` file) and validated once at startup.

Rule for the whole codebase: modules import `get_settings()` — nothing else
ever reads `os.environ` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# The project folder (the one holding src/, data/, pyproject.toml).
# Relative data/log paths resolve against it, not the current directory:
# hosted platforms such as Streamlit Cloud start the app from the
# repository root, where "data" would point at the wrong (empty) folder.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Single, validated source of truth for runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="HEALTHPLUS_",
        extra="ignore",
    )

    # --- Application identity ---
    app_name: str = "HealthPlus AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # --- LLM ---
    # Optional at settings load time; ClaudeClient and OpenAIClient fail fast
    # at construction if the required key is missing.
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )
    claude_model: str = "claude-sonnet-5"
    # No temperature/top_p: claude-sonnet-5 rejects non-default sampling
    # parameters — output style is steered through the system prompt instead.
    claude_max_tokens: int = Field(default=1024, gt=0)

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )
    openai_model: str = "gpt-4o-mini"

    # OpenRouter: one key, many models, OpenAI-compatible API. The default
    # is a free model so the app works without paid Anthropic/OpenAI keys.
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_model: str = "inclusionai/ling-3.2-flash:free"
    # Privacy: when true, OpenRouter only routes to providers that do not
    # store or train on prompts. Most FREE models are excluded by this (their
    # providers log prompts), so it is off by default; turn it on with paid
    # models: HEALTHPLUS_OPENROUTER_DENY_DATA_COLLECTION=true
    openrouter_deny_data_collection: bool = False
    # Larger than claude_max_tokens: some free models still spend tokens on
    # hidden reasoning before the visible answer.
    openrouter_max_tokens: int = Field(default=2048, gt=0)
    # Tried in order when the primary model is rate-limited or down.
    # Env format: HEALTHPLUS_OPENROUTER_FALLBACK_MODELS='["a/b:free","c/d:free"]'
    openrouter_fallback_models: list[str] = [
        "nvidia/nemotron-3.5-lightning:free",
        "google/gemma-4-31b-it:free",
    ]
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # --- Retrieval / RAG ---
    retrieval_top_k: int = Field(default=5, gt=0)
    # Cosine-similarity floor: hits below this are noise, not context.
    retrieval_min_score: float = Field(default=0.30, ge=-1.0, le=1.0)
    context_max_chars: int = Field(default=8000, gt=0)

    # --- Conversation ---
    memory_max_turns: int = Field(default=10, gt=0)

    # --- Storage ---
    data_dir: Path = Path("data")
    log_dir: Path = Path("logs")

    # --- Knowledge base ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chroma_collection: str = "healthplus_documents"
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)

    # --- Logging ---
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"log_level must be one of {sorted(_VALID_LOG_LEVELS)}, got {value!r}"
            )
        return level

    @field_validator("data_dir", "log_dir")
    @classmethod
    def _anchor_to_project_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else PROJECT_ROOT / value

    @model_validator(mode="after")
    def _overlap_smaller_than_chunk(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be smaller than "
                f"chunk_size ({self.chunk_size})"
            )
        return self

    @property
    def chroma_dir(self) -> Path:
        """Persistent home of the vector store (used from Day 4 onward)."""
        return self.data_dir / "chroma"

    def ensure_directories(self) -> None:
        """Create runtime directories that must exist before first use."""
        for directory in (self.data_dir, self.log_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings instance (built once, then cached)."""
    return Settings()
