"""Clerk's "account deleted" webhook: POST /api/webhooks/clerk deletes all of that user's data."""
import base64
import hashlib
import hmac
import json
import os
import time

import pytest

from app import config, storage
from app.db import SessionLocal
from app.models import SourceFile, StudySet, User
from app.routes.webhooks import signature_is_valid
from tests.test_quiz_api import LECTURE
from tests.test_search import create_set

SECRET = "whsec_" + base64.b64encode(b"a test signing secret, 32 bytes!").decode()
DEV_USER = "dev-user"  # the user every request is in dev mode (auth.py), so the sets created below are theirs


@pytest.fixture(autouse=True)
def signing_secret(monkeypatch):
    monkeypatch.setattr(config, "CLERK_WEBHOOK_SIGNING_SECRET", SECRET)


def send(client, event, secret=SECRET, timestamp=None):
    """POST an event signed the way Clerk (Svix) signs it."""
    body = json.dumps(event).encode()
    ts = str(int(time.time()) if timestamp is None else timestamp)
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signature = base64.b64encode(hmac.new(key, f"msg_1.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    headers = {"svix-id": "msg_1", "svix-timestamp": ts, "svix-signature": f"v1,{signature}",
               "content-type": "application/json"}
    return client.post("/api/webhooks/clerk", content=body, headers=headers)


def user_deleted(auth_id):
    # the shape of Clerk's user.deleted event
    return {"type": "user.deleted", "object": "event", "data": {"id": auth_id, "deleted": True, "object": "user"}}


def stored_paths(study_set_id):
    with SessionLocal() as db:
        files = db.query(SourceFile).filter_by(study_set_id=study_set_id).all()
        return [storage._local_path(f.storage_key) for f in files]


def test_svix_test_vector():
    # the example from Svix's documentation, so the check matches what Clerk really sends
    args = ("whsec_plJ3nmyCDGBKInavdOK15jsl", "msg_loFOjxBNrRLzqYUf", "1731705121",
            b'{"event_type":"ping","data":{"success":true}}')
    good = "v1,rAvfW3dJ/X/qxhsaXPOyyCGmRKsaKWcsNccKXlIktD0="
    assert signature_is_valid(*args, good, now=1731705121)
    assert signature_is_valid(*args, "v1,wrongsignature= " + good, now=1731705121)  # one of several
    assert not signature_is_valid(*args, good.replace("rAv", "rAw"), now=1731705121)
    assert not signature_is_valid(*args, good, now=1731705121 + 600)  # older than 5 minutes
    assert not signature_is_valid(*args[:3], args[3] + b" ", good, now=1731705121)  # body changed


def test_deleting_an_account_deletes_all_its_data(client):
    # someone else's set, which must survive
    other_set = create_set(client, "Not mine", LECTURE)
    with SessionLocal() as db:
        other = User(auth_id="user_other")
        db.add(other)
        db.flush()
        db.get(StudySet, other_set["id"]).user_id = other.id
        db.commit()
    mine = [create_set(client, "Plants", LECTURE), create_set(client, "Plants 2", LECTURE)]
    client.put("/api/display-settings", json={"theme": "dark"})
    my_files = [path for s in mine for path in stored_paths(s["id"])]
    assert my_files and all(os.path.exists(p) for p in my_files)

    response = send(client, user_deleted(DEV_USER))
    assert response.status_code == 200 and response.json() == {"status": "deleted"}

    with SessionLocal() as db:
        assert db.query(User).filter_by(auth_id=DEV_USER).count() == 0  # settings went with the row
        assert [s.id for s in db.query(StudySet).all()] == [other_set["id"]]  # chapters etc. cascade
    assert not any(os.path.exists(p) for p in my_files)
    assert all(os.path.exists(p) for p in stored_paths(other_set["id"]))


def test_a_repeated_or_unknown_account_is_fine(client):
    assert send(client, user_deleted("user_never_used_agoranote")).json() == {"status": "unknown user"}


def test_other_events_are_ignored(client):
    create_set(client, "Plants", LECTURE)
    response = send(client, {"type": "user.updated", "data": {"id": DEV_USER}})
    assert response.json() == {"status": "ignored"}
    with SessionLocal() as db:
        assert db.query(StudySet).count() == 1


def test_unsigned_or_forged_messages_are_refused(client):
    create_set(client, "Plants", LECTURE)
    forged_secret = "whsec_" + base64.b64encode(b"not the real secret").decode()
    assert send(client, user_deleted(DEV_USER), secret=forged_secret).status_code == 400
    assert send(client, user_deleted(DEV_USER), timestamp=int(time.time()) - 3600).status_code == 400
    assert client.post("/api/webhooks/clerk", json=user_deleted(DEV_USER)).status_code == 400  # no headers
    with SessionLocal() as db:
        assert db.query(StudySet).count() == 1


def test_without_a_signing_secret_every_message_is_refused(client, monkeypatch):
    monkeypatch.setattr(config, "CLERK_WEBHOOK_SIGNING_SECRET", "")
    assert send(client, user_deleted(DEV_USER)).status_code == 503
