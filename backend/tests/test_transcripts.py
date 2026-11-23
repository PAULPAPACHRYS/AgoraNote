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


def delete_like_the_api(set_id):
    """Delete a set from outside the worker, the way the Delete button (or account deletion) does."""
    from app.routes.study_sets import delete_stored_files, stored_file_keys

    with SessionLocal() as db:
        study_set = db.get(StudySet, set_id)
        keys = stored_file_keys(study_set)
        db.delete(study_set)
        db.commit()
    delete_stored_files(keys)


def delete_during_processing(set_keys):
    """Delete the set being processed, from outside the worker, and note its recording's storage key."""
    set_id = latest_set_id()
    set_keys.append(recording_key(set_id))
    delete_like_the_api(set_id)


def test_a_set_deleted_during_transcription_leaves_no_transcript(client, monkeypatch):
    # the set is deleted while the (slow) transcription runs; the worker must not leave the
    # transcript behind in storage, and must stop quietly
    keys = []

    def transcribe_then_get_deleted(path, filename, on_progress=None):
        delete_during_processing(keys)
        return "Mock transcript. " * 20

    monkeypatch.setattr(worker, "transcribe", transcribe_then_get_deleted)
    upload_recording(client)  # processes inline in tests; an error would fail the upload request
    with SessionLocal() as db:
        assert db.query(StudySet).count() == 0
    assert not storage.exists(keys[0])
    assert not storage.exists(storage.transcript_key(keys[0]))


def test_a_set_deleted_between_progress_updates_stops_quietly(client, monkeypatch):
    # the next status update would write to a row that no longer exists
    keys = []

    def transcribe_and_report_progress(path, filename, on_progress=None):
        delete_during_processing(keys)
        on_progress(1, 2)
        raise AssertionError("should have stopped at the progress update")

    monkeypatch.setattr(worker, "transcribe", transcribe_and_report_progress)
    upload_recording(client)
    assert not storage.exists(storage.transcript_key(keys[0]))


def latest_set_id():
    """The id of the newest study set: the one the worker is processing right now in these tests."""
    with SessionLocal() as db:
        return db.query(StudySet.id).order_by(StudySet.id.desc()).first()[0]
