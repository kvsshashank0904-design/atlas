def _signup_and_token(client, email="rahul@example.com"):
    client.post(
        "/auth/signup", json={"name": "Rahul", "email": email, "password": "password123"}
    )
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    return login.json()["access_token"]


def test_onboarding_creates_profile_and_goal(client):
    token = _signup_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/students/onboarding",
        headers=headers,
        json={
            "available_time_minutes_per_day": 180,
            "days_available_per_week": 6,
            "preparation_level": "some_chapters_completed",
            "goal": {
                "exam_type": "jee_main",
                "target_score": 180,
                "exam_date": "2027-01-15",
            },
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["available_time_minutes_per_day"] == 180
    assert body["goals"][0]["target_score"] == 180

    # can't onboard twice
    dup = client.post(
        "/students/onboarding",
        headers=headers,
        json={
            "available_time_minutes_per_day": 60,
            "days_available_per_week": 3,
            "preparation_level": "just_starting",
            "goal": {"exam_type": "jee_main", "target_score": 150, "exam_date": "2027-01-15"},
        },
    )
    assert dup.status_code == 400

    fetched = client.get("/students/me/profile", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["days_available_per_week"] == 6
