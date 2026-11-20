"""
The get_current_user dependency answers "Who is making this request?" for every endpoint

Endpoints declare `user: User = Depends(get_current_user)` FastAPI then calls get_current_user first
and passes the result in, if it raises an HTTPException, the endpoint never runs

AUTH_MODE=dev: there is no login, every request is the same fixed "dev-user"

AUTH_MODE=clerk: the user signs in with Clerk in the browser. The frontend then sends Clerk's
*session token* (a JWT: a signed piece of JSON) with every request, in the header
`Authorization: Bearer <token>`. Clerk signs these tokens with a private key that only Clerk has; the
matching public keys are published at AUTH_JWKS_URL. If the signature checks out with those keys,
the token really comes from our Clerk instance and its contents can be trusted:
- `sub` is the Clerk user id (stored as users.auth_id), `exp`/`nbf` say when the token is valid
  (Clerk tokens live about a minute; the frontend asks for a fresh one before every request),
- `iss` must be our Clerk instance, `azp` (if present) must be our frontend's address.
No Clerk secret key is needed on the server: checking a signature only needs the public keys.
"""
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.messages import message
from app.models import User

# in dev mode every request is this one user, so the app works without an auth provider
DEV_AUTH_ID = "dev-user"

# Created on first use. PyJWKClient downloads the public keys once and keeps them (cache_keys), and
# fetches them again only when a token is signed with a key it doesn't know yet (Clerk rotated keys).
_jwks_client: jwt.PyJWKClient | None = None


def _signing_key(token: str):
    #the public key that the token says it was signed with (looked up by the token's "kid" header)
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(config.AUTH_JWKS_URL, cache_keys=True)
    return _jwks_client.get_signing_key_from_jwt(token).key


def verify_clerk_token(token: str) -> dict:
    #check a Clerk session token and return its claims; raises jwt.PyJWTError if anything is wrong
    claims = jwt.decode(
        token,
        _signing_key(token),
        algorithms=["RS256"],  # the algorithm Clerk signs with; never accept anything else
        issuer=config.AUTH_ISSUER,  # tokens from another Clerk instance are rejected
        leeway=5,  # seconds of tolerance for small clock differences between Clerk and this server
        options={"require": ["exp", "iat", "iss", "sub"]},  # exp and nbf are checked automatically
    )
    # azp ("authorized party") is the website the token was issued for. Clerk leaves it out when the
    # browser sent no Origin; when present it must be our frontend, so tokens for other sites fail.
    if claims.get("azp") and claims["azp"] != config.FRONTEND_URL:
        raise jwt.InvalidTokenError(f"token issued for {claims['azp']}, not for this app")
    # "pending" sessions (only used with Clerk Organizations) are not fully signed in yet.
    if claims.get("sts") == "pending":
        raise jwt.InvalidTokenError("session is pending")
    return claims


def get_or_create_user(db: Session, auth_id: str, email: str | None = None) -> User:
    #The user with this auth_id, creating the row on their very first request
    user = db.scalar(select(User).where(User.auth_id == auth_id))
    if user is None:
        # ON CONFLICT DO NOTHING: two first requests arriving at once must not both fail.
        # (The second insert simply does nothing; both then read the same row below.)
        db.execute(
            insert(User).values(auth_id=auth_id, email=email).on_conflict_do_nothing(index_elements=["auth_id"])
        )
        db.commit()
        user = db.scalar(select(User).where(User.auth_id == auth_id))
    elif email and user.email != email:
        # Keep the email up to date (only known when the Clerk token carries an "email" claim).
        user.email = email
        db.commit()
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    # FastAPI dependency: the user making the request or an HTTP error
    # (Header(default=None) makes FastAPI pass in the request's "Authorization" header, if any.)
    if config.AUTH_MODE == "dev":
        return get_or_create_user(db, DEV_AUTH_ID)
    if config.AUTH_MODE != "clerk":
        raise HTTPException(status_code=500, detail=f"Unknown AUTH_MODE={config.AUTH_MODE}.")

    # 401 = "not signed in"; the WWW-Authenticate header tells clients a Bearer token is expected.
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail=message("sign_in_required"), headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = verify_clerk_token(token)
    except jwt.PyJWKClientConnectionError:
        # Clerk's public keys couldn't be downloaded (network problem or wrong AUTH_JWKS_URL).
        raise HTTPException(status_code=503, detail=message("sign_in_unreachable"))
    except jwt.PyJWTError:
        # Bad signature, expired, wrong issuer or site, malformed...: all just mean "not signed in".
        raise HTTPException(
            status_code=401, detail=message("session_expired"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_or_create_user(db, claims["sub"], claims.get("email"))
