from fastapi.testclient import TestClient

from app.main import app


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_unhandled_error_returns_json_500(client):
    def boom():
        raise RuntimeError("boom")

    app.add_api_route("/__boom", boom)
    try:
        r = TestClient(app, raise_server_exceptions=False).get("/__boom")
    finally:
        app.router.routes.pop()
    assert r.status_code == 500
    assert r.json() == {"detail": "Внутрішня помилка сервера"}
    assert client.get("/health").status_code == 200  # сервер продовжує працювати
