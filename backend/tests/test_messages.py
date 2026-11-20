"""Texts for the user are sent as a message code plus values, which the frontend translates."""
from tests.test_quiz_api import LECTURE


def test_api_errors_are_message_codes(client):
    response = client.post("/api/study-sets", data={"title": "Nothing"})
    assert response.status_code == 400
    assert response.json()["detail"] == {"code": "nothing_uploaded", "values": {}}

    response = client.post("/api/study-sets", files={"files": ("notes.exe", b"MZ", "application/octet-stream")})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "unsupported_type" and detail["values"]["filename"] == "notes.exe"

    assert client.get("/api/study-sets/999").json()["detail"] == {"code": "study_set_not_found", "values": {}}


def test_a_failed_set_gives_its_reason_as_a_code(client):
    response = client.post("/api/study-sets", data={"text": "Too short to make chapters from."})
    detail = client.get(f"/api/study-sets/{response.json()['id']}").json()
    assert detail["status"] == "failed"
    assert detail["error"] == {"code": "not_enough_material", "values": {}}
    assert detail["status_message"] is None


def test_a_ready_set_has_no_message_or_error(client):
    response = client.post("/api/study-sets", data={"text": LECTURE})
    detail = client.get(f"/api/study-sets/{response.json()['id']}").json()
    assert detail["status"] == "ready"
    assert detail["status_message"] is None and detail["error"] is None
