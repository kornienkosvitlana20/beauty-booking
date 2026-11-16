from .test_bookings import book, make_past_booking


def test_review_flow_updates_rating(client, master, auth, session_factory):
    c = auth("c@test.com", "client", "Марія")
    bid = make_past_booking(client, session_factory, master, c)
    r = client.post("/reviews", headers=c, json={"booking_id": bid, "rating": 5, "text": "Супер!"})
    assert r.status_code == 201 and r.json()["author"] == "Марія"
    m = client.get(f"/masters/{master['id']}").json()
    assert m["rating"] == 5.0 and m["reviews_count"] == 1
    assert client.get("/masters?min_rating=4.5").json()[0]["id"] == master["id"]
    assert client.get("/masters?min_rating=5").json()[0]["rating"] == 5.0
    reviews = client.get(f"/masters/{master['id']}/reviews").json()
    assert reviews[0]["text"] == "Супер!"


def test_duplicate_review_rejected(client, master, auth, session_factory):
    c = auth("c@test.com", "client")
    bid = make_past_booking(client, session_factory, master, c)
    assert client.post("/reviews", headers=c, json={"booking_id": bid, "rating": 4}).status_code == 201
    assert client.post("/reviews", headers=c, json={"booking_id": bid, "rating": 3}).status_code == 409


def test_review_before_visit_rejected(client, master, auth, slot):
    c = auth("c@test.com", "client")
    bid = book(client, c, master["service_id"], slot(10)).json()["id"]
    assert client.post("/reviews", headers=c, json={"booking_id": bid, "rating": 5}).status_code == 400


def test_review_of_foreign_booking_rejected(client, master, auth, session_factory):
    c1, c2 = auth("c1@test.com", "client"), auth("c2@test.com", "client")
    bid = make_past_booking(client, session_factory, master, c1)
    assert client.post("/reviews", headers=c2, json={"booking_id": bid, "rating": 5}).status_code == 403


def test_review_unknown_booking(client, auth):
    c = auth("c@test.com", "client")
    assert client.post("/reviews", headers=c, json={"booking_id": 999, "rating": 5}).status_code == 404


def test_review_rating_bounds(client, master, auth, session_factory):
    c = auth("c@test.com", "client")
    bid = make_past_booking(client, session_factory, master, c)
    for bad in (0, 6, -1):
        r = client.post("/reviews", headers=c, json={"booking_id": bid, "rating": bad})
        assert r.status_code == 422
    r = client.post("/reviews", headers=c, json={"booking_id": bid, "rating": 5, "text": "x" * 1001})
    assert r.status_code == 422
