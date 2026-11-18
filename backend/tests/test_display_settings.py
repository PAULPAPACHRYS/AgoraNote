"""Display settings saved to the account: GET/PUT /api/display-settings."""
from app.db import SessionLocal
from app.models import User

SETTINGS = {
    "theme": "contrast",
    "text_size": "larger",
    "line_spacing": "wide",
    "text_spacing": "widest",
    "reading_width": "narrow",
    "reduce_motion": "on",
    "underline_links": "on",
}


def test_nothing_saved_yet_is_null(client):
    response = client.get("/api/display-settings")
    assert response.status_code == 200
    assert response.json() is None


def test_saved_settings_come_back(client):
    assert client.put("/api/display-settings", json=SETTINGS).json() == SETTINGS
    assert client.get("/api/display-settings").json() == SETTINGS


def test_unknown_values_are_refused(client):
    response = client.put("/api/display-settings", json={**SETTINGS, "theme": "purple"})
    assert response.status_code == 422
    assert client.get("/api/display-settings").json() is None  # nothing was saved


def test_missing_settings_get_their_defaults(client):
    # e.g. settings saved before a new setting was added to the panel
    saved = client.put("/api/display-settings", json={"theme": "dark"}).json()
    assert saved["theme"] == "dark" and saved["text_size"] == "normal" and saved["reduce_motion"] == "system"


def test_settings_belong_to_their_own_user(client):
    client.get("/api/display-settings")  # creates the dev user
    with SessionLocal() as db:
        db.add(User(auth_id="someone-else", display_settings=SETTINGS))
        db.commit()
    assert client.get("/api/display-settings").json() is None
