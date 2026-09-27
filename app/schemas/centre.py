from decimal import Decimal

from pydantic import BaseModel, Field


class DiagnosticTestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(gt=0, decimal_places=2)


class DiagnosticTestResponse(BaseModel):
    id: int
    centre_id: int
    name: str
    description: str | None
    price: Decimal

    model_config = {"from_attributes": True}


class DiagnosticCentreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=512)


class DiagnosticCentreResponse(BaseModel):
    id: int
    name: str
    location: str
    tests: list[DiagnosticTestResponse] = []

    model_config = {"from_attributes": True}


class DiagnosticCentreListItem(BaseModel):
    id: int
    name: str
    location: str

    model_config = {"from_attributes": True}
