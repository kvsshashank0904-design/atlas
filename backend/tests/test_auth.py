def test_signup_and_login(client):
    resp = client.post(
        "/auth/signup",
        json={"name": "Rahul", "email": "rahul@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "rahul@example.com"

    # duplicate signup rejected
    dup = client.post(
        "/auth/signup",
        json={"name": "Rahul", "email": "rahul@example.com", "password": "password123"},
    )
    assert dup.status_code == 400

    login = client.post(
        "/auth/login",
        data={"username": "rahul@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Rahul"


def test_login_wrong_password(client):
    client.post(
        "/auth/signup",
        json={"name": "A", "email": "a@example.com", "password": "correcthorse"},
    )
    resp = client.post(
        "/auth/login", data={"username": "a@example.com", "password": "wrongpass"}
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
