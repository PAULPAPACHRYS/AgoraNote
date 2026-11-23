"""
Webhooks: messages another service sends to the API by itself (not requests from the frontend)

POST /api/webhooks/clerk: Clerk calls this when something happens to an account 
only "user.deleted" is acted on: the account was deleted (by the user in Clerk's "Manage account", or in the Clerk dashboard)
so everything AgoraNote keeps for it is deleted too:
- the user row, which takes the study sets, chapters, quiz progress and display settings with it (ON DELETE CASCADE in models.py)
- the uploaded files and saved transcripts in storage (R2 or the local folder)

there is no sign-in token here because Clerk itself is calling 
instead Clerk signs every message with a secret only Clerk and this API know (through Svix, the service that delivers Clerk's webhooks)

messages without a valid signature is refused, so nobody else can delete accounts by calling this URL
how the signature works: https://docs.svix.com/receiving/verifying-payloads/how-manual
"""
import base64
import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.models import StudySet, User
from app.routes.study_sets import delete_stored_files, stored_file_keys

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks")

# how far a message's timestamp may be from now: a copied message replayed later is refused
TIMESTAMP_TOLERANCE_SECONDS = 5 * 60


def signature_is_valid(
    secret: str, msg_id: str, timestamp: str, body: bytes, signature_header: str, now: float | None = None
) -> bool:
    # Svix signs "<message id>.<timestamp>.<raw body>" with HMAC-SHA256
    #key is the secret without its "whsec_" prefix, base64-decoded, `now` is only passed by tests
    try:
        key = base64.b64decode(secret.removeprefix("whsec_"))
        sent_at = int(timestamp)
    except ValueError:  # not base64 / not a number
        return False
    if abs((time.time() if now is None else now) - sent_at) > TIMESTAMP_TOLERANCE_SECONDS:
        return False
    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    # the header may hold several signatures, "v1,abc v1,def" (e.g. while the secret is being changed)
    for entry in signature_header.split():
        version, _, signature = entry.partition(",")
        # compare_digest takes as long for a near miss as for a total miss, so timing gives nothing away
        if version == "v1" and hmac.compare_digest(signature, expected):
            return True
    return False


async def raw_body(request: Request) -> bytes:
    # the exact bytes Clerk sent: the signature covers these, so they must be checked before any JSON parsing
    # a dependency because reading the body is async, the endpoint itself stays a normal def
    return await request.body()


@router.post("/clerk")
def clerk_webhook(
    body: bytes = Depends(raw_body),
    svix_id: str = Header(default=""),  #FastAPI reads the "svix-id" header into svix_id, etc
    svix_timestamp: str = Header(default=""),
    svix_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    # any 2xx answer tells Clerk the message arrived, on 4xx/5xx Clerk tries again later
    if not config.CLERK_WEBHOOK_SIGNING_SECRET:
        # 503: Clerk keeps retrying, so nothing is lost while the secret is still missing from .env
        raise HTTPException(status_code=503, detail="Webhooks are not set up (CLERK_WEBHOOK_SIGNING_SECRET is empty).")
    if not signature_is_valid(config.CLERK_WEBHOOK_SIGNING_SECRET, svix_id, svix_timestamp, body, svix_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    event = json.loads(body)
    if event.get("type") != "user.deleted":
        return {"status": "ignored"}  #some other event: nothing to do
    auth_id = (event.get("data") or {}).get("id")  # Clerk's user id, the same as the token's "sub"
    deleted = delete_user_data(db, auth_id) if auth_id else False
    return {"status": "deleted" if deleted else "unknown user"}


def delete_user_data(db: Session, auth_id: str) -> bool:
    # everything AgoraNote keeps for this Clerk account 
    # False when there is nothing: the account never used AgoraNote or this message came twice (webhooks can arrive more than once)
    user = db.scalar(select(User).where(User.auth_id == auth_id))
    if user is None:
        return False
    user_id = user.id  #for the log line: a deleted row can't be read any more after the commit
    study_sets = db.scalars(select(StudySet).where(StudySet.user_id == user_id)).all()
    keys = [key for study_set in study_sets for key in stored_file_keys(study_set)]
    db.delete(user)  # the database deletes all rows that belong to the user (ON DELETE CASCADE)
    db.commit()
    # files after the commit, like when deleting one study set:
    #leftover files are not a problem but a row pointing at a missing file can cause issues
    delete_stored_files(keys)
    log.info("Deleted user %s: %d study set(s), %d stored file(s)", user_id, len(study_sets), len(keys))
    return True
