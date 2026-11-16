from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, make_engine
from app.deps import get_db
from app.main import app, seed_categories


@pytest.fixture(name="session_factory")
def session_factory_fixture():
    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False)
    with maker() as db:
        seed_categories(db)
    yield maker
    engine.dispose()


@pytest.fixture(name="client")
def client_fixture(session_factory):
    def override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="auth")
def auth_fixture(client):
    """auth(email, role) -> заголовки Authorization."""

    def make(email: str, role: str, name: str = "Тест"):
        r = client.post("/auth/register", json={
            "email": email, "password": "password123", "full_name": name, "role": role})
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", json={"email": email, "password": "password123"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return make


@pytest.fixture(name="master")
def master_fixture(client, auth):
    """Майстер з профілем, послугою (60 хв, 500 грн) і графіком 09:00–18:00 щодня."""
    headers = auth("master@test.com", "master", "Олена Майстер")
    cat_id = client.get("/categories").json()[0]["id"]
    r = client.post("/masters", headers=headers,
                    json={"city": "Київ", "category_id": cat_id, "bio": "Манікюр"})
    assert r.status_code == 201, r.text
    master_id = r.json()["id"]
    r = client.post("/masters/me/services", headers=headers,
                    json={"name": "Манікюр", "price": 500, "duration_min": 60})
    service_id = r.json()["id"]
    schedule = [{"weekday": d, "start_time": "09:00", "end_time": "18:00"} for d in range(7)]
    assert client.put("/masters/me/schedule", headers=headers, json=schedule).status_code == 200
    return {"id": master_id, "service_id": service_id, "headers": headers, "category_id": cat_id}


@pytest.fixture(name="slot")
def slot_fixture():
    """slot(hour, minute=0, days=3) -> ISO-рядок майбутнього часу."""

    def make(hour: int = 10, minute: int = 0, days: int = 3) -> str:
        day = (datetime.now() + timedelta(days=days)).date()
        return datetime(day.year, day.month, day.day, hour, minute).isoformat()

    return make
