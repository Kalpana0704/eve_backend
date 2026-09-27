# EVE Healthcare — Diagnostic Booking Backend

FastAPI backend for diagnostic test bookings with JWT authentication, PostgreSQL persistence, simulated payments, and an **idempotent** payment webhook.

## Tech stack

- **Python 3.12**, **FastAPI**, **SQLAlchemy 2**
- **PostgreSQL** (via Docker Compose for local dev)
- **JWT** auth (`python-jose`, `passlib`/bcrypt)
- **pytest** + **httpx** TestClient for integration tests
- OpenAPI docs at `/docs` and `/redoc`

## Run locally (Docker — recommended)

```bash
docker compose up --build
```

API: http://localhost:8000  
Swagger: http://localhost:8000/docs

## Run locally (without Docker)

1. Start PostgreSQL and create database `eve_healthcare`.
2. Copy env file and adjust if needed:

```bash
cp .env.example .env
```

3. Install and run:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tables are created automatically on startup (`create_all`).

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use an in-memory SQLite database (no Postgres required).

---

## API endpoints

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | No | Register user |
| POST | `/auth/login` | No | Returns JWT `access_token` |

**Signup example**

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"password12\",\"full_name\":\"Jane Doe\"}"
```

**Login example**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"password12\"}"
```

Use header: `Authorization: Bearer <access_token>` for protected routes.

### Diagnostic centres & tests

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/centres` | No | List centres (paginated: `skip`, `limit`) |
| POST | `/centres` | No | Create centre |
| GET | `/centres/{id}` | No | Centre with nested tests |
| POST | `/centres/{id}/tests` | No | Add test with price |
| GET | `/centres/{id}/tests` | No | List tests at centre |

**Create centre + test**

```bash
curl -X POST http://localhost:8000/centres \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"EVE Diagnostics Pune\",\"location\":\"Baner, Pune\"}"

curl -X POST http://localhost:8000/centres/1/tests \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Thyroid Profile\",\"price\":\"899.00\",\"description\":\"T3,T4,TSH\"}"
```

### Bookings (authenticated)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/bookings` | Create booking (`PENDING`) |
| GET | `/bookings` | List current user's bookings |
| GET | `/bookings/{id}` | Get own booking |
| POST | `/bookings/{id}/cancel` | Cancel if not `CONFIRMED` |

**Create booking**

```bash
curl -X POST http://localhost:8000/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"test_id\":1,\"centre_id\":1,\"appointment_at\":\"2026-10-15T10:30:00Z\"}"
```

Amount is copied from the test price at booking time.

### Payments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/payments/` | Yes | Simulated payment for a booking |
| POST | `/payments/webhook/` | No* | Provider webhook (idempotent) |

\* Webhook is unauthenticated in this demo; in production you would verify HMAC signatures and IP allowlists.

**Simulated payment** (optional `force_outcome`: `SUCCESS` or `FAILED` for deterministic tests)

```bash
curl -X POST http://localhost:8000/payments/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"booking_id\":1,\"force_outcome\":\"SUCCESS\"}"
```

Without `force_outcome`, outcome is random (~85% success, configurable via `PAYMENT_SUCCESS_RATE`).

**Webhook** (must include unique `event_id`)

```bash
curl -X POST http://localhost:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d "{\"event_id\":\"evt_abc123\",\"booking_id\":1,\"status\":\"SUCCESS\",\"amount\":\"899.00\"}"
```

Repeating the same `event_id` returns `duplicate: true` and does not change state twice.

### Health

- `GET /health` → `{"status":"ok"}`

---

## Database schema

```
users
  id, email (unique), hashed_password, full_name, created_at

diagnostic_centres
  id, name, location, created_at

diagnostic_tests
  id, centre_id → diagnostic_centres, name, description, price

bookings
  id, user_id → users, test_id, centre_id, appointment_at, amount, status, created_at, updated_at
  status: PENDING | CONFIRMED | FAILED | CANCELLED

payments
  id, booking_id → bookings, amount, status, provider_reference (unique), timestamps
  status: PENDING | SUCCESS | FAILED

payment_events
  id, event_id (unique), payment_id, payload_hash, processed_at
  Used for webhook idempotency
```

**Relationships**

- A centre has many tests; a test belongs to one centre.
- A booking references user, test, and centre; amount is denormalized from test price.
- Payments link to bookings; successful payment → booking `CONFIRMED`, failed → `FAILED`.
- Each webhook `event_id` is stored once in `payment_events`.

---

## Assumptions

1. **Centre/test management** is open (no admin role) to simplify seeding for reviewers; production would use RBAC.
2. **Payment webhook** has no signature check in this assignment build; idempotency is enforced via unique `event_id`.
3. **Appointment times** must be timezone-aware ISO-8601 and in the future.
4. **Test must belong to centre** specified on the booking request.
5. Users can only read/pay/cancel **their own** bookings.
6. **One successful payment** per booking; further pay attempts are rejected after success.
7. **Cancelled bookings** cannot be paid or updated via webhook.

---

## Edge cases handled

- Duplicate signup email → `409`
- Invalid login → `401`
- Missing/invalid JWT → `401`
- Access another user's booking → `403`
- Unknown booking/test/centre → `404`
- Mismatched test/centre, past appointment, naive datetime → `400` / `422`
- Pay cancelled/confirmed booking → `400`
- Duplicate webhook `event_id` → `200` with `duplicate: true` (no double state change)
- Concurrent duplicate webhooks → unique constraint + retry path returns duplicate safely

---

## If I had more time

- Alembic migrations instead of `create_all`
- Admin role and secured centre CRUD
- Webhook HMAC verification and retry queue (Celery + Redis)
- Redis cache for centre listings
- Rate limiting on auth and webhook endpoints
- Refund flow and payment reconciliation reports
- Structured JSON logging and OpenTelemetry tracing

---

## Project layout

```
app/
  main.py              # FastAPI app, routers, lifespan
  config.py            # Settings from environment
  database.py          # SQLAlchemy engine/session
  core/security.py     # Password hashing, JWT
  dependencies/auth.py # Current user dependency
  models/              # ORM models
  schemas/             # Pydantic request/response models
  routers/             # HTTP routes
  services/            # Payment simulation & webhook logic
tests/                 # pytest integration tests
```

Good luck with your interview — the design is intentionally small so you can explain and extend it live.
