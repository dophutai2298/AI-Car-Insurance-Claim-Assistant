from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleManufacturerWriteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Vehicle manufacturer name cannot be blank")
        return normalized


class VehicleManufacturerUpdateRequest(VehicleManufacturerWriteRequest):
    is_active: bool


class VehicleManufacturerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
