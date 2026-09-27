import hashlib
import random
import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentEvent, PaymentStatus


class PaymentServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _apply_payment_outcome(booking: Booking, payment: Payment, outcome: PaymentStatus) -> None:
    payment.status = outcome
    if outcome == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED
    elif outcome == PaymentStatus.FAILED:
        booking.status = BookingStatus.FAILED


def simulate_payment(
    db: Session,
    booking_id: int,
    force_outcome: PaymentStatus | None = None,
) -> Payment:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise PaymentServiceError("Booking not found", 404)
    if booking.status == BookingStatus.CANCELLED:
        raise PaymentServiceError("Cannot pay for a cancelled booking", 400)
    if booking.status == BookingStatus.CONFIRMED:
        raise PaymentServiceError("Booking is already confirmed", 400)

    existing_success = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking_id,
            Payment.status == PaymentStatus.SUCCESS,
        )
        .first()
    )
    if existing_success:
        raise PaymentServiceError("Booking already has a successful payment", 400)

    if force_outcome is not None and force_outcome not in (
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
    ):
        raise PaymentServiceError("force_outcome must be SUCCESS or FAILED", 422)

    if force_outcome is not None:
        outcome = force_outcome
    else:
        outcome = (
            PaymentStatus.SUCCESS
            if random.random() < settings.payment_success_rate
            else PaymentStatus.FAILED
        )

    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=PaymentStatus.PENDING,
        provider_reference=f"sim_{uuid.uuid4().hex}",
    )
    db.add(payment)
    db.flush()

    _apply_payment_outcome(booking, payment, outcome)
    db.commit()
    db.refresh(payment)
    return payment


def process_webhook(db: Session, payload: dict) -> tuple[Payment | None, Booking | None, bool]:
    """
    Idempotent webhook processing. Returns (payment, booking, is_duplicate).
    """
    event_id = payload["event_id"]
    status_value = PaymentStatus(payload["status"])

    existing_event = db.query(PaymentEvent).filter(PaymentEvent.event_id == event_id).first()
    if existing_event:
        payment = db.get(Payment, existing_event.payment_id) if existing_event.payment_id else None
        booking = db.get(Booking, payment.booking_id) if payment else None
        return payment, booking, True

    payload_hash = hashlib.sha256(repr(sorted(payload.items())).encode()).hexdigest()

    payment: Payment | None = None
    if payload.get("payment_id"):
        payment = db.get(Payment, payload["payment_id"])
    elif payload.get("provider_reference"):
        payment = (
            db.query(Payment)
            .filter(Payment.provider_reference == payload["provider_reference"])
            .first()
        )

    booking: Booking | None = None
    if payment:
        booking = db.get(Booking, payment.booking_id)
    elif payload.get("booking_id"):
        booking = db.get(Booking, payload["booking_id"])
        if booking and payment is None:
            payment = (
                db.query(Payment)
                .filter(Payment.booking_id == booking.id)
                .order_by(Payment.id.desc())
                .first()
            )

    if booking is None:
        raise PaymentServiceError("Booking not found for webhook", 404)

    if payment is None:
        amount = payload.get("amount") or booking.amount
        payment = Payment(
            booking_id=booking.id,
            amount=Decimal(str(amount)),
            status=PaymentStatus.PENDING,
            provider_reference=payload.get("provider_reference"),
        )
        db.add(payment)
        db.flush()

    if booking.status == BookingStatus.CANCELLED:
        raise PaymentServiceError("Cannot update payment for cancelled booking", 400)

    _apply_payment_outcome(booking, payment, status_value)

    event = PaymentEvent(event_id=event_id, payment_id=payment.id, payload_hash=payload_hash)
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_event = db.query(PaymentEvent).filter(PaymentEvent.event_id == event_id).first()
        if existing_event and existing_event.payment_id:
            payment = db.get(Payment, existing_event.payment_id)
            booking = db.get(Booking, payment.booking_id) if payment else booking
        return payment, booking, True

    db.refresh(payment)
    db.refresh(booking)
    return payment, booking, False
