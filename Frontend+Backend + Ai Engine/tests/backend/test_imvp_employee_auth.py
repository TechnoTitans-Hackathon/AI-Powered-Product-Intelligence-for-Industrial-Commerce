import pytest
from fastapi.testclient import TestClient


def test_prototype_employee_login_success(client: TestClient):
    # 1. Login with prototype credentials
    res = client.post("/api/v1/auth/login", json={
        "email": "employee@demo.com",
        "password": "demo123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "employee@demo.com"
    assert data["tenant"]["id"] == "demo"
    assert "Demo Industrial Catalog" in data["tenant"]["name"]


def test_prototype_employee_login_invalid_password(client: TestClient):
    res = client.post("/api/v1/auth/login", json={
        "email": "employee@demo.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_prototype_employee_login_invalid_email(client: TestClient):
    res = client.post("/api/v1/auth/login", json={
        "email": "unknown@example.com",
        "password": "demo123"
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_authenticated_me_endpoint(client: TestClient):
    # Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": "employee@demo.com",
        "password": "demo123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Call /auth/me with Bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["email"] == "employee@demo.com"
    assert me_data["tenant"]["id"] == "demo"
