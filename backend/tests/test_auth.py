"""Clerk sign-in: the API accepts only valid Clerk session tokens, and users only see their own data.

The tests play the role of Clerk: they create their own RSA key pair, sign tokens with the private
key, and make auth.py check signatures with the matching public key instead of downloading Clerk's.
"""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import auth, config

ISSUER = "https://agoranote-test.clerk.accounts.dev"
FRONTEND = "http://localhost:5173"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)  # "someone else's" key


@pytest.fixture(autouse=True)
def clerk_mode(monkeypatch):
    """Switch the app to Clerk mode for every test in this file."""
    monkeypatch.setattr(config, "AUTH_MODE", "clerk")
    monkeypatch.setattr(config, "AUTH_ISSUER", ISSUER)
    monkeypatch.setattr(config, "FRONTEND_URL", FRONTEND)
    monkeypatch.setattr(auth, "_signing_key", lambda token: PRIVATE_KEY.public_key())


def token(sub="user_alice", key=PRIVATE_KEY, **claims):
    """A Clerk-like session token; keyword arguments override or add claims."""
    now = int(time.time())
    payload = {"iss": ISSUER, "sub": sub, "azp": FRONTEND, "iat": now, "nbf": now, "exp": now + 60, **claims}
    return jwt.encode(payload, key, algorithm="RS256")


def headers(t):
    return {"Authorization": f"Bearer {t}"}


def test_valid_token_signs_the_user_in(client):
    response = client.get("/api/me", headers=headers(token(email="alice@example.com")))
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


@pytest.mark.parametrize("bad_headers", [
    {},  # not signed in at all
    {"Authorization": "Bearer not-a-jwt"},
    {"Authorization": "Basic dXNlcjpwYXNz"},  # wrong scheme
])
def test_missing_or_malformed_token_is_401(client, bad_headers):
    response = client.get("/api/me", headers=bad_headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("bad_token", [
    token(key=OTHER_KEY),  # forged: signed with a key that isn't Clerk's
    token(exp=int(time.time()) - 120),  # expired
    token(nbf=int(time.time()) + 120),  # not valid yet
    token(iss="https://someone-else.clerk.accounts.dev"),  # another Clerk instance
    token(azp="https://evil.example"),  # issued for another website
    token(sts="pending"),  # session not finished
])
def test_invalid_tokens_are_rejected(client, bad_token):
    assert client.get("/api/me", headers=headers(bad_token)).status_code == 401


def test_token_without_azp_is_accepted(client):
    t = jwt.encode({"iss": ISSUER, "sub": "user_x", "iat": int(time.time()), "exp": int(time.time()) + 60},
                   PRIVATE_KEY, algorithm="RS256")
    assert client.get("/api/me", headers=headers(t)).status_code == 200


def test_users_only_see_their_own_study_sets(client):
    alice, bob = headers(token("user_alice")), headers(token("user_bob"))
    created = client.post("/api/study-sets", data={"text": "Alice's notes. " * 60}, headers=alice)
    set_id = created.json()["id"]

    assert [s["id"] for s in client.get("/api/study-sets", headers=alice).json()] == [set_id]
    assert client.get("/api/study-sets", headers=bob).json() == []
    assert client.get(f"/api/study-sets/{set_id}", headers=bob).status_code == 404
    assert client.delete(f"/api/study-sets/{set_id}", headers=bob).status_code == 404
    assert client.get(f"/api/study-sets/{set_id}", headers=alice).status_code == 200


def test_health_needs_no_sign_in(client):
    assert client.get("/api/health").status_code == 200
