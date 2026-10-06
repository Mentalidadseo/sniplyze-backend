"""Configuración de la aplicación, leída de variables de entorno o de `.env`.

Las credenciales nunca se escriben en el código: solo llegan por entorno.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    dataforseo_login: str = ""
    dataforseo_password: SecretStr = SecretStr("")
    dataforseo_base_url: str = "https://api.dataforseo.com"

    default_location_code: int = 2724
    default_language_code: str = "es"

    cost_confirm_threshold: float = Field(0.50, ge=0)
    confirm_unknown_cost: bool = True
    daily_budget: float = Field(0.0, ge=0)

    max_keywords_per_request: int = Field(100, ge=1, le=1000)
    max_targets_per_request: int = Field(100, ge=1, le=1000)
    max_limit: int = Field(1000, ge=1, le=1000)
    max_serp_depth: int = Field(100, ge=10, le=200)
    max_crawl_pages: int = Field(1000, ge=1)

    data_dir: Path = Path("data")
    cache_enabled: bool = True

    http_timeout_seconds: float = Field(120.0, gt=0)

    @property
    def has_credentials(self) -> bool:
        return bool(self.dataforseo_login and self.dataforseo_password.get_secret_value())

    @property
    def db_path(self) -> Path:
        return self.data_dir / "sniplyze.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
