def test_signup_and_login(client):
    signup = client.post(
        "/auth/signup",
        json={"email": "a@example.com", "password": "password12", "full_name": "Alice"},
    )
    assert signup.status_code == 201
    assert signup.json()["email"] == "a@example.com"

    dup = client.post(
        "/auth/signup",
        json={"email": "a@example.com", "password": "password12", "full_name": "Alice"},
    )
    assert dup.status_code == 409

    bad_login = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    login = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "password12"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_signup_validation(client):
    resp = client.post(
        "/auth/signup",
        json={"email": "not-an-email", "password": "short", "full_name": ""},
    )
    assert resp.status_code == 422
