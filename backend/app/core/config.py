"""Central settings.

Every adapter reads its mode from here, so moving from mock to live is a
.env change, never an application-code change. Production guards make it
impossible to boot with demo/mock adapters when APP_ENV=production.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    DEMO = "demo"
    PRODUCTION = "production"


class AuthMode(str, Enum):
    MOCK = "mock"
    SUPABASE = "supabase"


class DigiLockerMode(str, Enum):
    SANDBOX = "sandbox"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: AppEnv = AppEnv.DEVELOPMENT
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database (same code path for local Docker Postgres and Supabase)
    database_url: str
    db_ssl_required: bool = False
    db_transaction_pooler: bool = False  # True only for Supabase port 6543

    # Auth
    auth_mode: AuthMode = AuthMode.MOCK
    mock_user_id: str = "00000000-0000-4000-8000-000000000001"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""  # legacy HS256 projects only

    # OCR (ordered fallback chain)
    ocr_provider_chain: list[str] = ["google_vision", "tesseract"]
    ocr_timeout_seconds: float = 12.0
    google_application_credentials: str = ""
    tesseract_cmd: str = ""
    tesseract_langs: str = "eng+hin+guj"

    # LLM (any OpenAI-compatible endpoint; OpenRouter by default)
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek/deepseek-chat"
    llm_timeout_seconds: float = 20.0

    # Translation / transliteration (Sarvam AI)
    sarvam_api_key: str = ""
    sarvam_translate_url: str = "https://api.sarvam.ai/translate"
    sarvam_transliterate_url: str = "https://api.sarvam.ai/transliterate"
    sarvam_translate_model: str = "mayura:v1"
    sarvam_translate_mode: str = "formal"
    rag_output_strategy: str = "translate"  # "translate" | "native"

    # DigiLocker
    digilocker_mode: DigiLockerMode = DigiLockerMode.SANDBOX
    sandbox_consent_url: str = "http://localhost:3000/digilocker/consent"
    digilocker_client_id: str = ""
    digilocker_client_secret: str = ""
    digilocker_redirect_uri: str = "http://localhost:3000/verify"
    digilocker_authorize_url: str = ""
    digilocker_token_url: str = ""
    digilocker_api_base: str = ""
    digilocker_eaadhaar_path: str = ""

    @model_validator(mode="after")
    def _guard_environment(self) -> Settings:
        if self.app_env is AppEnv.PRODUCTION:
            if self.auth_mode is AuthMode.MOCK:
                raise ValueError("AUTH_MODE=mock is forbidden when APP_ENV=production")
            if self.digilocker_mode is DigiLockerMode.SANDBOX:
                raise ValueError("DIGILOCKER_MODE=sandbox is forbidden when APP_ENV=production")
            if "demo_fixture" in self.ocr_provider_chain:
                raise ValueError("The demo_fixture OCR provider is forbidden in production")
        if self.auth_mode is AuthMode.SUPABASE and not self.supabase_url:
            raise ValueError("SUPABASE_URL is required when AUTH_MODE=supabase")
        if self.rag_output_strategy not in {"translate", "native"}:
            raise ValueError("RAG_OUTPUT_STRATEGY must be 'translate' or 'native'")
        return self

    @property
    def shows_demo_data(self) -> bool:
        """True whenever any response could contain simulated data."""
        return self.digilocker_mode is DigiLockerMode.SANDBOX or "demo_fixture" in self.ocr_provider_chain


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
