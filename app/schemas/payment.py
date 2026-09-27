from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    booking_id: int
    force_outcome: PaymentStatus | None = Field(
        default=None,
        description="Optional: force SUCCESS or FAILED for testing; omit for simulated random outcome",
    )


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    provider_reference: str | None

    model_config = {"from_attributes": True}


class PaymentWebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    payment_id: int | None = None
    booking_id: int | None = None
    provider_reference: str | None = None
    status: PaymentStatus
    amount: Decimal | None = None


class WebhookResponse(BaseModel):
    message: str
    payment_id: int | None = None
    booking_id: int | None = None
    duplicate: bool = False
