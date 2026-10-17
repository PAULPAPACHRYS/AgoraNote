"""Where uploaded files live. Only the local-disk backend exists so far; R2 comes in Phase 9."""
import os
import shutil
from typing import BinaryIO

from app import config


def _local_path(key: str) -> str:
    return os.path.join(config.LOCAL_STORAGE_DIR, key)


def save(key: str, fileobj: BinaryIO) -> None:
    """Copy a file-like object to storage in chunks, so big uploads never sit in memory."""
    path = _local_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as out:
        shutil.copyfileobj(fileobj, out)


def download(key: str, dest_path: str) -> None:
    """Copy a stored file to a local path (the worker processes files from a temp directory)."""
    shutil.copyfile(_local_path(key), dest_path)


def delete(key: str) -> None:
    """Delete a stored file. A file that is already gone is not an error."""
    try:
        os.remove(_local_path(key))
    except FileNotFoundError:
        pass
