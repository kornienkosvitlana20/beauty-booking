from datetime import datetime, timedelta


def book(client, headers, service_id, start_at):
    return client.post("/bookings", headers=headers,
                       json={"service_id": service_id, "start_at": start_at})


def test_slots_listed(client, master, slot):
    day = slot()[:10]
    r = client.get(f"/masters/{master['id']}/slots",
                   params={"service_id": master["service_id"], "date": day})
    slots = r.json()["slots"]
    assert r.status_code == 200
    assert slots[0].endswith("09:00:00") and slots[-1].endswith("17:00:00")


def test_slots_empty_on_day_off(client, master, auth):
    client.put("/masters/me/schedule", headers=master["headers"], json=[])
    r = client.get(f"/masters/{master['id']}/slots",
                   params={"service_id": master["service_id"], "date": "2030-01-01"})
    assert r.json()["slots"] == []


def test_slots_wrong_service(client, master):
    r = client.get(f"/masters/{master['id']}/slots",
                   params={"service_id": 999, "date": "2030-01-01"})
    assert r.status_code == 404


def test_create_booking_and_slot_disappears(client, master, auth, slot):
    c = auth("c@test.com", "client")
    r = book(client, c, master["service_id"], slot(10))
    assert r.status_code == 201 and r.json()["status"] == "booked"
    day = slot()[:10]
    slots = client.get(f"/masters/{master['id']}/slots",
                       params={"service_id": master["service_id"], "date": day}).json()["slots"]
    assert not any(s.endswith("10:00:00") or s.endswith("10:30:00") for s in slots)


def test_double_booking_rejected(client, master, auth, slot):
    c1, c2 = auth("c1@test.com", "client"), auth("c2@test.com", "client")
    assert book(client, c1, master["service_id"], slot(10)).status_code == 201
    assert book(client, c2, master["service_id"], slot(10)).status_code == 409


def test_overlapping_booking_rejected(client, master, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(10)).status_code == 201
    assert book(client, c, master["service_id"], slot(10, 30)).status_code == 409
    assert book(client, c, master["service_id"], slot(9, 30)).status_code == 409
    assert book(client, c, master["service_id"], slot(11)).status_code == 201


def test_booking_in_past_rejected(client, master, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(10, days=-2)).status_code == 400


def test_booking_outside_schedule_rejected(client, master, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(8)).status_code == 400
    assert book(client, c, master["service_id"], slot(17, 30)).status_code == 400
    assert book(client, c, master["service_id"], slot(23)).status_code == 400


def test_booking_boundary_values(client, master, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(9)).status_code == 201    # початок зміни
    assert book(client, c, master["service_id"], slot(17)).status_code == 201   # кінець рівно о 18:00


def test_booking_off_grid_rejected(client, master, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(10, 15)).status_code == 400


def test_booking_day_off_rejected(client, master, auth, slot):
    client.put("/masters/me/schedule", headers=master["headers"], json=[])
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(10)).status_code == 400


def test_booking_unknown_service(client, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, 999, slot()).status_code == 404


def test_booking_invalid_payload(client, master, auth):
    c = auth("c@test.com", "client")
    r = client.post("/bookings", headers=c, json={"service_id": master["service_id"],
                                                  "start_at": "not-a-date"})
    assert r.status_code == 422


def test_master_cannot_book(client, master, slot):
    assert book(client, master["headers"], master["service_id"], slot()).status_code == 403


def test_booking_requires_auth(client, master, slot):
    r = client.post("/bookings", json={"service_id": master["service_id"], "start_at": slot()})
    assert r.status_code == 401


def test_timezone_suffix_is_ignored(client, master, auth, slot):
    c = auth("c@test.com", "client")
    assert book(client, c, master["service_id"], slot(12) + "Z").status_code == 201


def test_cancel_frees_slot(client, master, auth, slot):
    c1, c2 = auth("c1@test.com", "client"), auth("c2@test.com", "client")
    bid = book(client, c1, master["service_id"], slot(10)).json()["id"]
    r = client.post(f"/bookings/{bid}/cancel", headers=c1)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert book(client, c2, master["service_id"], slot(10)).status_code == 201


def test_cancel_rules(client, master, auth, slot):
    c1, c2 = auth("c1@test.com", "client"), auth("c2@test.com", "client")
    bid = book(client, c1, master["service_id"], slot(10)).json()["id"]
    assert client.post(f"/bookings/{bid}/cancel", headers=c2).status_code == 403
    assert client.post("/bookings/999/cancel", headers=c1).status_code == 404
    assert client.post(f"/bookings/{bid}/cancel", headers=master["headers"]).status_code == 200
    assert client.post(f"/bookings/{bid}/cancel", headers=c1).status_code == 400


def test_cannot_cancel_past_booking(client, master, auth, session_factory):
    c = auth("c@test.com", "client")
    bid = make_past_booking(client, session_factory, master, c)
    assert client.post(f"/bookings/{bid}/cancel", headers=c).status_code == 400


def test_reschedule(client, master, auth, slot):
    c = auth("c@test.com", "client")
    bid = book(client, c, master["service_id"], slot(10)).json()["id"]
    r = client.post(f"/bookings/{bid}/reschedule", headers=c, json={"start_at": slot(14)})
    assert r.status_code == 200 and r.json()["start_at"].endswith("14:00:00")
    # старий слот знову вільний
    assert book(client, auth("c2@test.com", "client"), master["service_id"],
                slot(10)).status_code == 201


def test_reschedule_into_own_overlap_allowed(client, master, auth, slot):
    c = auth("c@test.com", "client")
    bid = book(client, c, master["service_id"], slot(10)).json()["id"]
    r = client.post(f"/bookings/{bid}/reschedule", headers=c, json={"start_at": slot(10, 30)})
    assert r.status_code == 200


def test_reschedule_to_taken_slot(client, master, auth, slot):
    c1, c2 = auth("c1@test.com", "client"), auth("c2@test.com", "client")
    book(client, c2, master["service_id"], slot(14))
    bid = book(client, c1, master["service_id"], slot(10)).json()["id"]
    r = client.post(f"/bookings/{bid}/reschedule", headers=c1, json={"start_at": slot(14)})
    assert r.status_code == 409


def test_reschedule_rules(client, master, auth, slot):
    c1, c2 = auth("c1@test.com", "client"), auth("c2@test.com", "client")
    bid = book(client, c1, master["service_id"], slot(10)).json()["id"]
    assert client.post(f"/bookings/{bid}/reschedule", headers=c2,
                       json={"start_at": slot(12)}).status_code == 403
    assert client.post(f"/bookings/{bid}/reschedule", headers=master["headers"],
                       json={"start_at": slot(12)}).status_code == 403
    client.post(f"/bookings/{bid}/cancel", headers=c1)
    assert client.post(f"/bookings/{bid}/reschedule", headers=c1,
                       json={"start_at": slot(12)}).status_code == 400


def test_my_bookings(client, master, auth, slot):
    c = auth("c@test.com", "client")
    book(client, c, master["service_id"], slot(10))
    mine = client.get("/bookings/my", headers=c).json()
    assert len(mine) == 1 and mine[0]["service_name"] == "Манікюр"
    assert len(client.get("/bookings/my", headers=master["headers"]).json()) == 1
    other = auth("c2@test.com", "client")
    assert client.get("/bookings/my", headers=other).json() == []
    no_profile = auth("m9@test.com", "master")
    assert client.get("/bookings/my", headers=no_profile).json() == []


def make_past_booking(client, session_factory, master, client_headers):
    """Створює запис у минулому напряму в БД (через API це заборонено)."""
    from app.models import Booking  # pylint: disable=import-outside-toplevel

    me = client.get("/auth/me", headers=client_headers).json()
    start = datetime.now() - timedelta(days=2)
    with session_factory() as db:
        b = Booking(client_id=me["id"], service_id=master["service_id"], master_id=master["id"],
                    start_at=start, end_at=start + timedelta(hours=1), status="booked")
        db.add(b)
        db.commit()
        return b.id
