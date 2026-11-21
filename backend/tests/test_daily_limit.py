"""The daily limit: at most config.MAX_STUDY_SETS_PER_DAY new study sets per user in any 24 hours."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app import config
from app.db import SessionLocal
from app.models import StudySetCreation, User

# Fails quickly in the mock pipeline (too short for chapters), which is all these tests need:
# a failed set counts the same as a ready one.
SHORT = "Too short to make chapters from."


def create(client):
    return client.post("/api/study-sets", data={"text": SHORT})


@pytest.fixture
def limit(monkeypatch):
    """Set the daily limit for one test: limit(2)."""
    return lambda n: monkeypatch.setattr(config, "MAX_STUDY_SETS_PER_DAY", n)


def test_the_limit_refuses_one_set_too_many(client, limit):
    limit(2)
    assert client.get("/api/study-sets/usage").json() == {"limit": 2, "used": 0, "next_free_at": None}
    assert create(client).status_code == 201
    assert create(client).status_code == 201

    response = create(client)
    assert response.status_code == 429
    assert response.json()["detail"] == {"code": "daily_limit_reached", "values": {"max": 2}}

    usage = client.get("/api/study-sets/usage").json()
    assert usage["used"] == 2
    # the next one is allowed when the first set is 24 hours old
    with SessionLocal() as db:
        first = db.scalar(select(func.min(StudySetCreation.created_at)))
    assert datetime.fromisoformat(usage["next_free_at"]) == first + timedelta(hours=24)


def test_deleting_a_set_does_not_give_its_slot_back(client, limit):
    limit(1)
    set_id = create(client).json()["id"]
    assert client.delete(f"/api/study-sets/{set_id}").status_code == 204
    assert create(client).status_code == 429


def test_retrying_a_failed_set_does_not_count(client, limit):
    limit(1)
    set_id = create(client).json()["id"]
    assert client.post(f"/api/study-sets/{set_id}/retry").status_code == 200
    assert client.get("/api/study-sets/usage").json()["used"] == 1


def test_sets_older_than_24_hours_no_longer_count(client, limit):
    limit(1)
    create(client)
    # move that creation 25 hours into the past
    with SessionLocal() as db:
        creation = db.scalar(select(StudySetCreation))
        creation.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db.commit()

    assert client.get("/api/study-sets/usage").json()["used"] == 0
    assert create(client).status_code == 201
    # the old creation time was removed by that upload; only the new one is left
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudySetCreation)) == 1


def test_other_users_sets_do_not_count(client, limit):
    limit(1)
    with SessionLocal() as db:
        other = User(auth_id="someone-else")
        db.add(other)
        db.flush()
        db.add_all([StudySetCreation(user_id=other.id) for _ in range(3)])
        db.commit()

    assert client.get("/api/study-sets/usage").json()["used"] == 0
    assert create(client).status_code == 201


def test_zero_means_no_limit(client, limit):
    limit(0)
    for _ in range(3):
        assert create(client).status_code == 201
    assert client.get("/api/study-sets/usage").json() == {"limit": 0, "used": 3, "next_free_at": None}


def test_a_refused_upload_does_not_count(client, limit):
    limit(1)
    response = client.post("/api/study-sets", files={"files": ("notes.exe", b"MZ", "application/octet-stream")})
    assert response.status_code == 400
    assert client.get("/api/study-sets/usage").json()["used"] == 0
