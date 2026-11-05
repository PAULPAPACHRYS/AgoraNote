"""
Where uploaded files are saved, only the local-disk backend exists so far

Files are addressed by a *key*, a path-like string such as "users/1/sets/7/1-notes.pdf" (built in routes/study_sets.py)
Locally the "storage" is a folder (LOCAL_STORAGE_DIR, a Docker volume shared by the API, which saves uploads, and the workers, which read them)

Later will switch to Cloudflare R2
"""
import os
import shutil
from typing import BinaryIO

from app import config


def _local_path(key: str) -> str:
    #the file on disk for a key, e.g. /data/uploads/users/1/sets/7/1-notes.pdf
    return os.path.join(config.LOCAL_STORAGE_DIR, key)


def save(key: str, fileobj: BinaryIO) -> None:
    #Copy a file-like object to storage in chunks, so big uploads never sit in memory
    path = _local_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)  # create users/1/sets/7/ if needed
    with open(path, "wb") as out:
        shutil.copyfileobj(fileobj, out)  # reads and writes piece by piece


def download(key: str, dest_path: str) -> None:
    #copy a stored file to a local path (the worker processes files from a temp directory)
    shutil.copyfile(_local_path(key), dest_path)


def delete(key: str) -> None:
    #delete a stored file, a file that is already gone is not an error
    try:
        os.remove(_local_path(key))
    except FileNotFoundError:
        pass
