from datetime import UTC, datetime, timedelta


def _create_booking(client, auth_headers, seeded_centre) -> int:
    appointment = (datetime.now(UTC) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    resp = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "test_id": seeded_centre["test_id"],
            "centre_id": seeded_centre["centre_id"],
            "appointment_at": appointment,
        },
    )
    return resp.json()["id"]


def test_simulated_payment_success(client, auth_headers, seeded_centre):
    booking_id = _create_booking(client, auth_headers, seeded_centre)
    pay = client.post(
        "/payments/",
        headers=auth_headers,
        json={"booking_id": booking_id, "force_outcome": "SUCCESS"},
    )
    assert pay.status_code == 200
    assert pay.json()["status"] == "SUCCESS"

    booking = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking.json()["status"] == "CONFIRMED"


def test_simulated_payment_failed(client, auth_headers, seeded_centre):
    booking_id = _create_booking(client, auth_headers, seeded_centre)
    pay = client.post(
        "/payments/",
        headers=auth_headers,
        json={"booking_id": booking_id, "force_outcome": "FAILED"},
    )
    assert pay.status_code == 200
    booking = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking.json()["status"] == "FAILED"


def test_webhook_idempotency(client, auth_headers, seeded_centre):
    booking_id = _create_booking(client, auth_headers, seeded_centre)
    payload = {
        "event_id": "evt_12345",
        "booking_id": booking_id,
        "status": "SUCCESS",
        "amount": "499.00",
    }
    first = client.post("/payments/webhook/", json=payload)
    assert first.status_code == 200
    assert first.json()["duplicate"] is False

    second = client.post("/payments/webhook/", json=payload)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    booking = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking.json()["status"] == "CONFIRMED"


def test_webhook_invalid_booking(client):
    resp = client.post(
        "/payments/webhook/",
        json={"event_id": "evt_missing", "booking_id": 99999, "status": "SUCCESS"},
    )
    assert resp.status_code == 404
