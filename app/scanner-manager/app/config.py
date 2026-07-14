from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "WicScan Scanner Manager"
    API_V1_PREFIX: str = "/api/v1"

    SONARQUBE_URL: str = "http://sonarqube:9000"
    SONARQUBE_TOKEN: str = ""           # if set, used directly; otherwise bootstrapped from admin creds
    SONARQUBE_ADMIN_USER: str = "admin"
    SONARQUBE_ADMIN_PASSWORD: str = "admin"

    NUCLEI_URL:  str = "http://nuclei:9100"
    MOBSF_URL:   str = "http://mobsf:8000"
    MOBSF_API_KEY: str = "mobsf_secret_key"
    OPENVAS_URL: str = "http://openvas-api:9200"

    REDIS_URL: str = "redis://redis:6379/0"
    BACKEND_URL: str = "http://backend:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
