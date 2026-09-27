from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWebhookPayload, WebhookResponse
from app.services.payment_service import PaymentServiceError, process_webhook, simulate_payment

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse)
def create_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentResponse:
    from app.models.booking import Booking

    booking = db.get(Booking, body.booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        payment = simulate_payment(db, body.booking_id, body.force_outcome)
    except PaymentServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    return payment


@router.post("/webhook/", response_model=WebhookResponse)
def payment_webhook(body: PaymentWebhookPayload, db: Session = Depends(get_db)) -> WebhookResponse:
    if body.payment_id is None and body.booking_id is None and body.provider_reference is None:
        raise HTTPException(
            status_code=422,
            detail="At least one of payment_id, booking_id, or provider_reference is required",
        )
    from app.models.payment import PaymentStatus

    if body.status == PaymentStatus.PENDING:
        raise HTTPException(status_code=422, detail="Webhook status must be SUCCESS or FAILED")

    try:
        payment, booking, duplicate = process_webhook(db, body.model_dump())
    except PaymentServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    return WebhookResponse(
        message="Event already processed" if duplicate else "Webhook processed",
        payment_id=payment.id if payment else None,
        booking_id=booking.id if booking else None,
        duplicate=duplicate,
    )
