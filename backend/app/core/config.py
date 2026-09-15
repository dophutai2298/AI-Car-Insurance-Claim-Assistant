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
    jwt_secret: str = Field(min_length=16, validation_alias="JWT_SECRET")
    jwt_access_token_minutes: int = Field(default=480, validation_alias="JWT_ACCESS_TOKEN_MINUTES")
    admin_email: str = Field(default="admin@example.com", validation_alias="ADMIN_EMAIL")
    admin_password: str = Field(default="Admin123!", validation_alias="ADMIN_PASSWORD")
    adjuster_email: str = Field(default="adjuster@example.com", validation_alias="ADJUSTER_EMAIL")
    adjuster_password: str = Field(default="Adjuster123!", validation_alias="ADJUSTER_PASSWORD")
    upload_root: str = Field(default="uploads", validation_alias="UPLOAD_ROOT")
    max_evidence_files: int = Field(default=10, ge=1, validation_alias="MAX_EVIDENCE_FILES")
    max_evidence_file_size_bytes: int = Field(
        default=10 * 1024 * 1024, ge=1, validation_alias="MAX_EVIDENCE_FILE_SIZE_BYTES"
    )
    damage_model_mode: Literal["mock", "http"] = Field(default="mock", validation_alias="DAMAGE_MODEL_MODE")
    damage_model_url: str | None = Field(default=None, validation_alias="DAMAGE_MODEL_URL")
    damage_confidence_threshold: float = Field(
        default=0.70, ge=0, le=1, validation_alias="DAMAGE_CONFIDENCE_THRESHOLD"
    )
    damage_repair_max_percentage: float = Field(
        default=40, ge=0, le=100, validation_alias="DAMAGE_REPAIR_MAX_PERCENTAGE"
    )
    damage_replacement_min_percentage: float = Field(
        default=60, ge=0, le=100, validation_alias="DAMAGE_REPLACEMENT_MIN_PERCENTAGE"
    )
    part_search_mode: Literal["mock", "unavailable"] = Field(
        default="mock", validation_alias="PART_SEARCH_MODE"
    )
    llm_mode: Literal["mock", "openai"] = Field(default="mock", validation_alias="LLM_MODE")
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str | None = Field(default=None, validation_alias="OPENAI_MODEL")
    frontend_origin: str = Field(default="http://localhost:5173", validation_alias="FRONTEND_ORIGIN")
    check_database_on_health: bool = Field(default=True, validation_alias="CHECK_DATABASE_ON_HEALTH")

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    def public_runtime(self) -> dict[str, str]:
        return {
            "damage_model_mode": self.damage_model_mode,
            "damage_confidence_threshold": str(self.damage_confidence_threshold),
            "part_search_mode": self.part_search_mode,
            "llm_mode": self.llm_mode,
            "upload_root": self.upload_root,
        }

    def upload_root_path(self) -> Path:
        configured_root = Path(self.upload_root)
        return configured_root if configured_root.is_absolute() else ROOT_DIR / configured_root


@lru_cache
def get_settings() -> Settings:
    return Settings()
