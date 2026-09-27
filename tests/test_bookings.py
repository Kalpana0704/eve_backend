from datetime import UTC, datetime, timedelta


def test_booking_flow(client, auth_headers, seeded_centre):
    appointment = (datetime.now(UTC) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    booking = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "test_id": seeded_centre["test_id"],
            "centre_id": seeded_centre["centre_id"],
            "appointment_at": appointment,
        },
    )
    assert booking.status_code == 201
    body = booking.json()
    assert body["status"] == "PENDING"
    assert body["amount"] == "499.00"

    other = client.post("/auth/signup", json={"email": "b@example.com", "password": "password12", "full_name": "Bob"})
    assert other.status_code == 201
    login = client.post("/auth/login", json={"email": "b@example.com", "password": "password12"})
    forbidden = client.get(f"/bookings/{body['id']}", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert forbidden.status_code == 403


def test_booking_invalid_centre_test(client, auth_headers, seeded_centre):
    appointment = (datetime.now(UTC) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    resp = client.post(
        "/bookings",
        headers=auth_headers,
        json={
            "test_id": seeded_centre["test_id"],
            "centre_id": 9999,
            "appointment_at": appointment,
        },
    )
    assert resp.status_code == 400
