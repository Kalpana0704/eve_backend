import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database_module
from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

database_module.engine = engine
database_module.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    client.post(
        "/auth/signup",
        json={"email": "patient@example.com", "password": "securepass1", "full_name": "Test Patient"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "patient@example.com", "password": "securepass1"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_centre(client):
    centre = client.post("/centres", json={"name": "EVE Lab Mumbai", "location": "Andheri, Mumbai"})
    centre_id = centre.json()["id"]
    test = client.post(
        f"/centres/{centre_id}/tests",
        json={"name": "Complete Blood Count", "price": "499.00"},
    )
    return {"centre_id": centre_id, "test_id": test.json()["id"]}
