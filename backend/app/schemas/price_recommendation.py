from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PriceRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recommendation: Literal["SUPPORTS_REPAIR", "SUPPORTS_REPLACEMENT", "MANUAL_REVIEW"]
    rationale: str = Field(min_length=1, max_length=1200, description="Qualitative explanation only: no digits, monetary amounts, currency units, or claim approval/rejection statements.")
