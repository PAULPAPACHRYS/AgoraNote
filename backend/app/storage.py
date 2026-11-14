"""
Where uploaded files are saved: a local folder (development) or Cloudflare R2 (STORAGE_BACKEND=r2)

Files are addressed by a *key*, a path-like string such as "users/1/sets/7/1-notes.pdf" (built in routes/study_sets.py)
The rest of the code only uses the functions below, so it doesn't know or care which backend is used

- local: the "storage" is a folder (LOCAL_STORAGE_DIR, a Docker volume shared by the API, which saves uploads,
  and the workers, which read them)
- r2: Cloudflare R2 object storage, a "bucket" of files in the cloud, spoken to with boto3 (Amazon's S3 library;
  R2 speaks the same S3 API). The key is the object's name in the bucket. The bucket stays private: there are no
  public links, only the API (uploading, deleting) and the workers (reading) access it, with an R2 API token
"""
import os
import shutil
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app import config


def check_settings() -> None:
    #refuse to start with storage settings that can't work (called by main.py and worker.py on startup)
    if config.STORAGE_BACKEND not in ("local", "r2"):
        raise RuntimeError(f"Unknown STORAGE_BACKEND={config.STORAGE_BACKEND} (use local or r2).")
    needed = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
    missing = [name for name in needed if not getattr(config, name)]
    if config.STORAGE_BACKEND == "r2" and missing:
        raise RuntimeError(f"STORAGE_BACKEND=r2 needs these settings: {', '.join(missing)}.")


# --- local folder -----------------------------------------------------------------------------------

def _local_path(key: str) -> str:
    #the file on disk for a key, e.g. /data/uploads/users/1/sets/7/1-notes.pdf
    return os.path.join(config.LOCAL_STORAGE_DIR, key)


# --- Cloudflare R2 ----------------------------------------------------------------------------------

# created on first use, in each process (a boto3 client must not be shared between the worker's processes)
_r2_client = None


def _r2():
    #the boto3 client for our R2 account: R2's S3 address for the account, region "auto" (R2 has no regions)
    global _r2_client
    if _r2_client is None:
        _r2_client = boto3.client(
            "s3",
            endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    return _r2_client


def _use_r2() -> bool:
    return config.STORAGE_BACKEND == "r2"


# --- the functions the rest of the app uses ------------------------------------------------------------

def save(key: str, fileobj: BinaryIO) -> None:
    #Copy a file-like object to storage in chunks, so big uploads never sit in memory
    if _use_r2():
        # upload_fileobj sends big files in parts (multipart upload), reading the file piece by piece
        _r2().upload_fileobj(fileobj, config.R2_BUCKET, key)
        return
    path = _local_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)  # create users/1/sets/7/ if needed
    with open(path, "wb") as out:
        shutil.copyfileobj(fileobj, out)  # reads and writes piece by piece


def download(key: str, dest_path: str) -> None:
    #copy a stored file to a local path (the worker processes files from a temp directory)
    if _use_r2():
        _r2().download_file(config.R2_BUCKET, key, dest_path)  # also in parts, straight to the file
        return
    shutil.copyfile(_local_path(key), dest_path)


def exists(key: str) -> bool:
    #is something stored under this key?
    if _use_r2():
        try:
            _r2().head_object(Bucket=config.R2_BUCKET, Key=key)  # asks for the object's details, not its bytes
            return True
        except ClientError as error:
            if error.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise  # anything else (wrong credentials, network...) is a real error
    return os.path.isfile(_local_path(key))


def read_text(key: str) -> str:
    #a stored text file's contents (used for saved transcripts)
    if _use_r2():
        return _r2().get_object(Bucket=config.R2_BUCKET, Key=key)["Body"].read().decode("utf-8")
    with open(_local_path(key), encoding="utf-8") as f:
        return f.read()


def transcript_key(key: str) -> str:
    #where a recording's transcript is saved: next to the upload, e.g. ".../1-lecture.mp4.transcript.txt"
    return key + ".transcript.txt"


def delete(key: str) -> None:
    #delete a stored file, a file that is already gone is not an error
    if _use_r2():
        _r2().delete_object(Bucket=config.R2_BUCKET, Key=key)  # R2/S3 don't complain about missing objects
        return
    try:
        os.remove(_local_path(key))
    except FileNotFoundError:
        pass
