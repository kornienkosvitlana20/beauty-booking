import jwt

from app.config import settings
from app.security import create_token, decode_token, hash_password, verify_password


def test_register_and_login(client):
    r = client.post("/auth/register", json={
        "email": "Anna@Test.com", "password": "password123", "full_name": "Анна", "role": "client"})
    assert r.status_code == 201
    assert r.json()["email"] == "anna@test.com"
    assert "password" not in r.text
    r = client.post("/auth/login", json={"email": "anna@test.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


def test_duplicate_email(client, auth):
    auth("a@test.com", "client")
    r = client.post("/auth/register", json={
        "email": "A@test.com", "password": "password123", "full_name": "X", "role": "client"})
    assert r.status_code == 409


def test_weak_password_rejected(client):
    r = client.post("/auth/register", json={
        "email": "a@test.com", "password": "123", "full_name": "X", "role": "client"})
    assert r.status_code == 422


def test_invalid_email_rejected(client):
    r = client.post("/auth/register", json={
        "email": "", "password": "password123", "full_name": "X", "role": "client"})
    assert r.status_code == 422


def test_invalid_role_rejected(client):
    r = client.post("/auth/register", json={
        "email": "a@test.com", "password": "password123", "full_name": "X", "role": "admin"})
    assert r.status_code == 422


def test_login_wrong_password(client, auth):
    auth("a@test.com", "client")
    r = client.post("/auth/login", json={"email": "a@test.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", json={"email": "no@test.com", "password": "password123"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_ok(client, auth):
    headers = auth("a@test.com", "client", "Анна")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200 and r.json()["full_name"] == "Анна"


def test_categories_seeded(client):
    assert len(client.get("/categories").json()) >= 5


def test_password_hashing():
    stored = hash_password("secret123")
    assert verify_password("secret123", stored)
    assert not verify_password("other", stored)
    assert not verify_password("x", "not-a-valid-hash")


def test_token_roundtrip_and_tampering():
    assert decode_token(create_token(42)) == 42
    forged = jwt.encode({"sub": "1"}, "other-secret", algorithm="HS256")
    assert decode_token(forged) is None
    no_sub = jwt.encode({"x": 1}, settings.secret_key, algorithm="HS256")
    assert decode_token(no_sub) is None
