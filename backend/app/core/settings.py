from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Verity"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/verity"
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    CLERK_DOMAIN: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_SECRET_KEY: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "models/gemini-2.0-flash"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    STT_PROVIDER: str = "mock"
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"
    CANARY_QWEN_MODEL: str = "nvidia/canary-qwen-2.5b"

    TTS_PROVIDER: str = "mock"
    TTS_VOICE: str = "en-US-JennyNeural"
    VIBEVOICE_SPEAKER: str = "en-Carter_man"
    VIBEVOICE_MODEL: str = "microsoft/VibeVoice-Realtime-0.5B"

    @property
    def clerk_jwks_url(self) -> str:
        if self.CLERK_JWKS_URL:
            return self.CLERK_JWKS_URL
        if self.CLERK_DOMAIN:
            return f"https://{self.CLERK_DOMAIN}/.well-known/jwks.json"
        return ""


settings = Settings()
