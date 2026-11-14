"""Storage backends: the R2 code path (with an in-memory stand-in for R2) and the startup settings check."""
import io

import pytest
from botocore.exceptions import ClientError

from app import config, storage

BUCKET = "agoranote-test"


class FakeR2:
    """Behaves like the few boto3 S3 client calls storage.py uses, keeping objects in a dict."""

    def __init__(self):
        self.objects = {}  # (bucket, key) -> bytes

    def upload_fileobj(self, fileobj, bucket, key):
        self.objects[(bucket, key)] = fileobj.read()

    def download_file(self, bucket, key, path):
        with open(path, "wb") as f:
            f.write(self.objects[(bucket, key)])

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return {"ContentLength": len(self.objects[(Bucket, Key)])}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)  # like S3: deleting a missing object is fine


@pytest.fixture
def r2(monkeypatch):
    """Switch storage to R2 mode, with the fake standing in for the real client."""
    fake = FakeR2()
    monkeypatch.setattr(config, "STORAGE_BACKEND", "r2")
    monkeypatch.setattr(config, "R2_BUCKET", BUCKET)
    monkeypatch.setattr(storage, "_r2_client", fake)
    return fake


def test_r2_save_read_download_delete(r2, tmp_path):
    storage.save("users/1/sets/1/1-notes.txt", io.BytesIO("Γεια σου".encode("utf-8")))
    assert storage.exists("users/1/sets/1/1-notes.txt")
    assert not storage.exists("users/1/sets/1/missing.txt")
    assert storage.read_text("users/1/sets/1/1-notes.txt") == "Γεια σου"

    local_copy = tmp_path / "copy.txt"
    storage.download("users/1/sets/1/1-notes.txt", str(local_copy))
    assert local_copy.read_text(encoding="utf-8") == "Γεια σου"

    storage.delete("users/1/sets/1/1-notes.txt")
    storage.delete("users/1/sets/1/1-notes.txt")  # twice: no error
    assert not storage.exists("users/1/sets/1/1-notes.txt")


def test_a_whole_study_set_lives_in_r2_and_is_deleted_with_the_set(client, r2):
    response = client.post(
        "/api/study-sets",
        files={"files": ("lecture.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
        data={"text": "Pasted notes. " * 60},
    )
    set_id = response.json()["id"]
    detail = client.get(f"/api/study-sets/{set_id}").json()
    assert detail["status"] == "ready", detail["error"]

    keys = sorted(key for _, key in r2.objects)
    assert keys == [
        f"users/1/sets/{set_id}/1-lecture.mp3",
        f"users/1/sets/{set_id}/1-lecture.mp3.transcript.txt",  # the saved transcript, also in R2
        f"users/1/sets/{set_id}/2-pasted-text.txt",
    ]
    assert all(bucket == BUCKET for bucket, _ in r2.objects)

    assert client.delete(f"/api/study-sets/{set_id}").status_code == 204
    assert r2.objects == {}


def test_settings_check(monkeypatch):
    monkeypatch.setattr(config, "STORAGE_BACKEND", "r2")
    for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.setattr(config, name, "")
    with pytest.raises(RuntimeError, match="R2_ACCOUNT_ID"):
        storage.check_settings()

    monkeypatch.setattr(config, "STORAGE_BACKEND", "s3")
    with pytest.raises(RuntimeError, match="Unknown STORAGE_BACKEND"):
        storage.check_settings()

    monkeypatch.setattr(config, "STORAGE_BACKEND", "local")
    storage.check_settings()  # local needs nothing
