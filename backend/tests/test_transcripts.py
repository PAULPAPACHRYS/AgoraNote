"""Saved transcripts: a recording is transcribed once; retries reuse the saved transcript."""
import io

from app import storage, worker
from app.db import SessionLocal
from app.models import SourceFile, StudySet


def upload_recording(client):
    """Upload a (fake) recording; the mock transcriber doesn't look at the bytes."""
    response = client.post("/api/study-sets", files={"files": ("lecture.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")})
    assert response.status_code == 201
    return response.json()["id"]


def recording_key(set_id):
    """The storage key of the set's uploaded recording."""
    with SessionLocal() as db:
        return db.query(SourceFile).filter(SourceFile.study_set_id == set_id).one().storage_key


def test_transcript_is_saved_next_to_the_recording(client):
    set_id = upload_recording(client)
    assert client.get(f"/api/study-sets/{set_id}").json()["status"] == "ready"
    key = storage.transcript_key(recording_key(set_id))
    assert storage.exists(key)
    assert "Mock transcript of lecture.mp3" in storage.read_text(key)


def test_processing_again_reuses_the_saved_transcript(client, monkeypatch):
    set_id = upload_recording(client)
    with SessionLocal() as db:
        first_text = db.get(StudySet, set_id).source_text

    # Any call to the transcriber now fails the test: the second run must use the saved transcript.
    def no_transcribing(*args, **kwargs):
        raise AssertionError("transcribed again")

    monkeypatch.setattr(worker, "transcribe", no_transcribing)
    worker.process_study_set.apply(args=[set_id])  # run the whole pipeline again, as a retry does

    detail = client.get(f"/api/study-sets/{set_id}").json()
    assert detail["status"] == "ready", detail["error"]
    with SessionLocal() as db:
        assert db.get(StudySet, set_id).source_text == first_text


def test_deleting_a_set_deletes_its_transcript(client):
    set_id = upload_recording(client)
    key = recording_key(set_id)
    assert client.delete(f"/api/study-sets/{set_id}").status_code == 204
    assert not storage.exists(key)
    assert not storage.exists(storage.transcript_key(key))
