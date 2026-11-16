def test_client_cannot_create_profile(client, auth):
    headers = auth("c@test.com", "client")
    cat = client.get("/categories").json()[0]["id"]
    r = client.post("/masters", headers=headers, json={"city": "Київ", "category_id": cat})
    assert r.status_code == 403


def test_profile_created_once(client, master):
    r = client.post("/masters", headers=master["headers"],
                    json={"city": "Львів", "category_id": master["category_id"]})
    assert r.status_code == 409


def test_profile_unknown_category(client, auth):
    headers = auth("m2@test.com", "master")
    r = client.post("/masters", headers=headers, json={"city": "Київ", "category_id": 9999})
    assert r.status_code == 400


def test_master_actions_need_profile(client, auth):
    headers = auth("m3@test.com", "master")
    r = client.post("/masters/me/services", headers=headers,
                    json={"name": "X", "price": 100, "duration_min": 30})
    assert r.status_code == 404


def test_client_cannot_add_service(client, auth):
    headers = auth("c@test.com", "client")
    r = client.post("/masters/me/services", headers=headers,
                    json={"name": "X", "price": 100, "duration_min": 30})
    assert r.status_code == 403


def test_get_master_and_services(client, master):
    r = client.get(f"/masters/{master['id']}")
    assert r.status_code == 200 and r.json()["rating"] is None
    assert r.json()["reviews_count"] == 0
    services = client.get(f"/masters/{master['id']}/services").json()
    assert services[0]["price"] == 500
    assert len(client.get(f"/masters/{master['id']}/schedule").json()) == 7


def test_unknown_master_404(client):
    assert client.get("/masters/999").status_code == 404
    assert client.get("/masters/999/services").status_code == 404
    assert client.get("/masters/999/schedule").status_code == 404
    assert client.get("/masters/999/reviews").status_code == 404
    assert client.get("/masters/999/slots?service_id=1&date=2030-01-01").status_code == 404


def test_search_filters(client, master):
    assert len(client.get("/masters").json()) == 1
    assert len(client.get("/masters?city=київ").json()) == 1
    assert client.get("/masters?city=Одеса").json() == []
    assert client.get("/masters?category_id=9999").json() == []
    assert len(client.get("/masters?q=манік").json()) == 1
    assert len(client.get("/masters?q=олена").json()) == 1
    assert client.get("/masters?q=nonexistent").json() == []
    assert len(client.get("/masters?min_price=400&max_price=600").json()) == 1
    assert client.get("/masters?min_price=600").json() == []
    assert client.get("/masters?max_price=100").json() == []
    assert client.get("/masters?min_rating=4").json() == []


def test_search_validation(client):
    assert client.get("/masters?limit=0").status_code == 422
    assert client.get("/masters?min_price=-1").status_code == 422
    assert client.get("/masters?min_rating=6").status_code == 422


def test_search_empty_db(client):
    assert client.get("/masters").json() == []


def test_service_validation(client, master):
    h = master["headers"]
    assert client.post("/masters/me/services", headers=h,
                       json={"name": "X", "price": 0, "duration_min": 30}).status_code == 422
    assert client.post("/masters/me/services", headers=h,
                       json={"name": "X", "price": -5, "duration_min": 30}).status_code == 422
    assert client.post("/masters/me/services", headers=h,
                       json={"name": "X", "price": 100, "duration_min": 0}).status_code == 422
    assert client.post("/masters/me/services", headers=h,
                       json={"name": "", "price": 100, "duration_min": 30}).status_code == 422


def test_schedule_validation(client, master):
    h = master["headers"]
    bad = [{"weekday": 0, "start_time": "18:00", "end_time": "09:00"}]
    assert client.put("/masters/me/schedule", headers=h, json=bad).status_code == 422
    bad = [{"weekday": 7, "start_time": "09:00", "end_time": "18:00"}]
    assert client.put("/masters/me/schedule", headers=h, json=bad).status_code == 422
    dup = [{"weekday": 1, "start_time": "09:00", "end_time": "12:00"},
           {"weekday": 1, "start_time": "13:00", "end_time": "18:00"}]
    assert client.put("/masters/me/schedule", headers=h, json=dup).status_code == 400


def test_delete_service(client, master):
    h = master["headers"]
    r = client.post("/masters/me/services", headers=h,
                    json={"name": "Зайва", "price": 100, "duration_min": 30})
    sid = r.json()["id"]
    assert client.delete(f"/masters/me/services/{sid}", headers=h).status_code == 204
    assert client.delete(f"/masters/me/services/{sid}", headers=h).status_code == 404


def test_cannot_delete_service_with_bookings(client, master, auth, slot):
    c = auth("c@test.com", "client")
    client.post("/bookings", headers=c, json={"service_id": master["service_id"], "start_at": slot()})
    r = client.delete(f"/masters/me/services/{master['service_id']}", headers=master["headers"])
    assert r.status_code == 409
