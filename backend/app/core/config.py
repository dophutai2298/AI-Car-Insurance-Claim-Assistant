from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "AI Car Insurance Claim Assistant API"
    database_url: str = Field(
        default="postgresql+psycopg://claim_user:claim_password@localhost:5432/claim_assistant",
        validation_alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me-in-local-dev", validation_alias="JWT_SECRET")
    upload_root: str = Field(default="uploads", validation_alias="UPLOAD_ROOT")
    damage_model_mode: Literal["mock", "http"] = Field(default="mock", validation_alias="DAMAGE_MODEL_MODE")
    damage_model_url: str | None = Field(default=None, validation_alias="DAMAGE_MODEL_URL")
    part_search_mode: Literal["mock"] = Field(default="mock", validation_alias="PART_SEARCH_MODE")
    llm_mode: Literal["mock", "openai"] = Field(default="mock", validation_alias="LLM_MODE")
    frontend_origin: str = Field(default="http://localhost:5173", validation_alias="FRONTEND_ORIGIN")
    check_database_on_health: bool = Field(default=True, validation_alias="CHECK_DATABASE_ON_HEALTH")

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    def public_runtime(self) -> dict[str, str]:
        return {
            "damage_model_mode": self.damage_model_mode,
            "part_search_mode": self.part_search_mode,
            "llm_mode": self.llm_mode,
            "upload_root": self.upload_root,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
