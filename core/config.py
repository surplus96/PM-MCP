"""Centralized application settings (pydantic-settings).

FR-B05: PM_MCP_ROOT hardcoding removal.
FR-B14: GEMINI_MODEL naming normalization.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal


try:
    from pydantic import Field, field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict
    try:
        from pydantic_settings import NoDecode  # 2.2+
    except ImportError:
        NoDecode = None  # type: ignore[assignment]
    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # pragma: no cover - fallback for environments without pydantic-settings
    _HAS_PYDANTIC_SETTINGS = False


if _HAS_PYDANTIC_SETTINGS:

    # ``NoDecode`` keeps pydantic-settings from JSON-decoding the env
    # value before our field_validator runs. Documented format is
    # comma-separated, but EnvSettingsSource defaults to JSON for any
    # ``list[str]`` field — boot crashes on HF Spaces without this.
    _AllowedOrigins = (
        Annotated[list[str], NoDecode] if NoDecode is not None else list[str]
    )


    class Settings(BaseSettings):
        """Stock Manager backend settings loaded from env / .env."""

        # Paths
        pm_mcp_root: Path = Field(
            default=Path(__file__).resolve().parent.parent,
            description="Root of the PM-MCP codebase to add to sys.path",
        )

        # LLM
        gemini_api_key: str = Field(default="", description="Google AI Studio API key")
        gemini_model: str = Field(
            default="gemma-4-26b-a4b-it",
            description="Gemini/Gemma model id (formerly GEMMA_MODEL)",
        )
        llm_timeout_sec: int = Field(default=300, ge=10, le=600)

        # Security / networking — see _AllowedOrigins above for why this
        # is annotated rather than a plain ``list[str]``.
        allowed_origins: _AllowedOrigins = Field(  # type: ignore[valid-type]
            default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
            description="CORS allow_origins (comma-separated in env)",
        )
        # Dashboard Market Overview fans out ~15 parallel requests per load;
        # bumped from 60 so HMR reloads and multi-tab use don't trip the limiter.
        rate_limit_per_min: int = Field(default=240, ge=1)
        rate_limit_analysis_per_min: int = Field(default=10, ge=1)

        # Chat-bot + analysis-report shared model (FR-P01).
        # 2026-05-01: bumped to ``gemini-3.1-flash-lite-preview`` after a
        # live probe confirmed it returns 200 on this API tier (the same
        # tier where 3.0-flash 404'd back in April). Lite-preview is the
        # cheapest 3.x variant and answers chat-shaped prompts in ~1s
        # cold; 2.5-flash / 2.0-flash stay in the fallback chain so
        # quota/503 failures still degrade gracefully.
        default_chat_model: str = Field(default="gemini-3.1-flash-lite-preview")
        chat_use_preview: bool = Field(default=False)

        # KIS Developers (한국투자증권) — third-tier KR market data.
        # Sits behind PyKrx in the fall-through chain so cloud-egress
        # hosts (HF Spaces) and KRX special listings (REIT/ETN/A-prefix
        # codes like ``0001A0``) still resolve. Empty values disable
        # the adapter cleanly — see mcp_server/tools/kis_client.py.
        kis_app_key: str = Field(default="", description="KIS Developers app key")
        kis_app_secret: str = Field(default="", description="KIS Developers app secret")

        # Ops
        log_level: str = Field(default="INFO")
        environment: Literal["dev", "staging", "prod"] = Field(default="dev")

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=False,
        )

        @field_validator("allowed_origins", mode="before")
        @classmethod
        def _parse_origins(cls, raw):
            # ``ALLOWED_ORIGINS`` is documented as a comma-separated string,
            # but pydantic-settings defaults to JSON-decoding any env value
            # bound to a ``list[str]`` field. Without this validator the
            # process refuses to boot on Hugging Face Spaces whenever the
            # operator follows the docs and writes ``a.com,b.com``.
            if raw is None or raw == "":
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
            if isinstance(raw, list):
                return raw
            return [o.strip() for o in str(raw).split(",") if o.strip()]

else:  # Minimal stdlib fallback so server can still boot without pydantic-settings

    class Settings:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.pm_mcp_root = Path(os.getenv("PM_MCP_ROOT", str(Path(__file__).resolve().parent.parent)))
            self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
            self.gemini_model = os.getenv("GEMINI_MODEL", os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it"))
            self.llm_timeout_sec = int(os.getenv("LLM_TIMEOUT_SEC", "300"))
            raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
            self.allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
            self.rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "240"))
            self.rate_limit_analysis_per_min = int(os.getenv("RATE_LIMIT_ANALYSIS_PER_MIN", "10"))
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            self.environment = os.getenv("ENVIRONMENT", "dev")
            self.default_chat_model = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
            self.chat_use_preview = os.getenv("CHAT_USE_PREVIEW", "0") in ("1", "true", "yes")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
