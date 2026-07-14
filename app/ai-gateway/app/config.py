from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "WicScan AI Gateway"

    # Provider selection
    DEFAULT_PROVIDER: str = "ollama"
    DEFAULT_MODEL: str = "llama3.2"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.1

    # Provider credentials
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
