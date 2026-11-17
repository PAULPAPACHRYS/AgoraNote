"""The study set's language code: worked out while structuring, stored, and sent with every response."""
import io

from app.ai import prompts

GREEK_TEXT = "Η φωτοσύνθεση είναι η διαδικασία με την οποία τα φυτά παράγουν ενέργεια από το φως. " * 20
ENGLISH_TEXT = "Photosynthesis is the process plants use to turn light into chemical energy. " * 20


def test_language_code():
    # the Greek check wins, also over the small model's "gr" mistake
    assert prompts.language_code(GREEK_TEXT, "gr") == "el"
    assert prompts.language_code(GREEK_TEXT, "") == "el"
    # otherwise the LLM's code is used when it looks like an ISO 639-1 code
    assert prompts.language_code("Le cours commence par la photosynthèse.", " FR ") == "fr"
    # names, longer codes or nothing at all mean "unknown"
    assert prompts.language_code(ENGLISH_TEXT, "English") is None
    assert prompts.language_code(ENGLISH_TEXT, "eng") is None
    assert prompts.language_code(ENGLISH_TEXT, "") is None


def test_every_response_carries_the_language(client):
    # with the mock LLM, English material is "en" and Greek material "el"
    english = client.post("/api/study-sets", data={"text": ENGLISH_TEXT}).json()["id"]
    greek = client.post(
        "/api/study-sets",
        files={"files": ("σημειώσεις.txt", io.BytesIO(GREEK_TEXT.encode("utf-8")), "text/plain")},
    ).json()["id"]

    detail = client.get(f"/api/study-sets/{greek}").json()
    assert detail["status"] == "ready" and detail["language"] == "el"
    assert client.get(f"/api/study-sets/{english}").json()["language"] == "en"

    languages = {s["id"]: s["language"] for s in client.get("/api/study-sets").json()}
    assert languages[greek] == "el" and languages[english] == "en"

    chapter_id = detail["chapters"][0]["id"]
    assert client.get(f"/api/chapters/{chapter_id}").json()["language"] == "el"

    results = client.get("/api/search", params={"q": "φωτοσύνθεση"}).json()
    assert results and all(r["language"] == "el" for r in results)
