"""API tests for full-text search."""
from app.db import SessionLocal
from app.models import StudySet, User
from tests.test_quiz_api import LECTURE

GREEK = """Η φωτοσύνθεση είναι η διαδικασία με την οποία τα φυτά μετατρέπουν την ενέργεια του φωτός σε χημική ενέργεια. Πραγματοποιείται κυρίως στα φύλλα, μέσα στους χλωροπλάστες.

Οι χλωροπλάστες περιέχουν τη χρωστική χλωροφύλλη, η οποία απορροφά κυρίως το κόκκινο και το μπλε φως. Γι' αυτό τα φύλλα φαίνονται πράσινα.

Οι φωτεινές αντιδράσεις γίνονται στις μεμβράνες των θυλακοειδών. Το φως διεγείρει ηλεκτρόνια της χλωροφύλλης, τα οποία κινούνται σε μια αλυσίδα μεταφοράς ηλεκτρονίων.

Ο κύκλος του Calvin γίνεται στο στρώμα του χλωροπλάστη. Το ένζυμο Rubisco δεσμεύει το διοξείδιο του άνθρακα."""


def create_set(client, title, text):
    """Upload text as a study set (processed inline with the mock AI) and return its detail."""
    response = client.post("/api/study-sets", data={"title": title, "text": text})
    assert response.status_code == 201
    return client.get(f"/api/study-sets/{response.json()['id']}").json()


def search(client, q):
    """GET /api/search and return the list of results."""
    response = client.get("/api/search", params={"q": q})
    assert response.status_code == 200
    return response.json()


def test_search_finds_a_term_and_links_to_its_chapter(client):
    study_set = create_set(client, "Plants", LECTURE)
    results = search(client, "Rubisco")
    assert results, "expected at least one match"
    chapter_ids = {c["id"] for c in study_set["chapters"]}
    for r in results:
        assert r["study_set_id"] == study_set["id"]
        assert r["study_set_title"] == "Plants"
        assert r["chapter_id"] in chapter_ids
        assert "[[Rubisco]]" in r["snippet"]  # match markers, never HTML
        assert "<" not in r["snippet"]


def test_search_is_case_insensitive_and_works_for_greek(client):
    create_set(client, "Φυτά", GREEK + "\n\n" + GREEK)
    assert search(client, "rubisco")
    results = search(client, "χλωροφύλλη")
    assert results and "[[χλωροφύλλη]]" in results[0]["snippet"]


def test_search_supports_phrases_and_returns_nothing_for_unknown_words(client):
    create_set(client, "Plants", LECTURE)
    assert search(client, '"Calvin cycle"')
    assert search(client, "zzzunknownword") == []
    assert search(client, "   ") == []


def test_search_only_returns_the_users_own_chapters(client):
    study_set = create_set(client, "Plants", LECTURE)
    with SessionLocal() as db:
        other = User(auth_id="someone-else")
        db.add(other)
        db.flush()
        db.get(StudySet, study_set["id"]).user_id = other.id
        db.commit()
    assert search(client, "Rubisco") == []
