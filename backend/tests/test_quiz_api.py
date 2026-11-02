"""API tests for quizzes and scoring. Processing runs inline (Celery eager mode) with the mock AI."""
import pytest
from sqlalchemy import select

from app import config
from app.db import SessionLocal
from app.models import Question, StudySet, Topic, User

P = config.POINTS_PER_QUESTION

LECTURE = """Photosynthesis is the process by which green plants, algae and some bacteria turn light energy into chemical energy. It takes place mainly in the leaves, inside organelles called chloroplasts. The overall reaction uses carbon dioxide and water and produces glucose and oxygen.

Chloroplasts contain the pigment chlorophyll, which absorbs mostly red and blue light and reflects green light. That is why leaves look green. The chlorophyll molecules are arranged in structures called photosystems, embedded in the thylakoid membranes.

The light-dependent reactions happen in the thylakoid membranes. Light excites electrons in chlorophyll, and these electrons travel along an electron transport chain. Their energy is used to pump protons and to make ATP. Water molecules are split to replace the lost electrons, and oxygen is released as a by-product.

The second stage is the Calvin cycle, which takes place in the stroma of the chloroplast. The enzyme Rubisco fixes carbon dioxide by attaching it to a five-carbon sugar. Using ATP and NADPH, the cycle turns the fixed carbon into a three-carbon sugar that the plant can use to build glucose.

Rubisco is probably the most abundant protein on Earth, but it is slow and sometimes binds oxygen instead of carbon dioxide. This wasteful side reaction is called photorespiration. Photorespiration is more common when it is hot and dry, because plants close their stomata to save water and oxygen builds up in the leaf.

Some plants have evolved ways to reduce photorespiration. C4 plants such as maize first fix carbon dioxide into a four-carbon compound in mesophyll cells and then release it near Rubisco in bundle-sheath cells. CAM plants such as cacti open their stomata only at night and store carbon dioxide as an acid until daytime.

The rate of photosynthesis depends on light intensity, carbon dioxide concentration and temperature. When one of these factors is in short supply it limits the rate, no matter how plentiful the others are. This idea is known as the principle of limiting factors.

Photosynthesis matters far beyond the plant itself. It supplies almost all the oxygen in the atmosphere and the organic carbon that feeds food chains. Fossil fuels are the remains of organisms that stored the energy of ancient sunlight through photosynthesis."""


@pytest.fixture
def study_set(client):
    """A processed study set with at least two chapters."""
    response = client.post("/api/study-sets", data={"title": "Test set", "text": LECTURE})
    assert response.status_code == 201
    detail = client.get(f"/api/study-sets/{response.json()['id']}").json()
    assert detail["status"] == "ready", detail["error"]
    assert len(detail["chapters"]) >= 2
    return detail


def quiz(client, chapter_id):
    response = client.get(f"/api/chapters/{chapter_id}/quiz")
    assert response.status_code == 200, response.json()
    return response.json()


def correct_index(question_id):
    """The right answer, read straight from the database (the API never tells us beforehand)."""
    with SessionLocal() as db:
        return db.get(Question, question_id).correct_index


def answer(client, question_id, selected_index):
    return client.post(f"/api/questions/{question_id}/answer", json={"selected_index": selected_index})


def test_quiz_never_reveals_answers(client, study_set):
    state = quiz(client, study_set["chapters"][0]["id"])
    assert len(state["topics"]) == config.QUESTIONS_PER_CHAPTER
    for topic in state["topics"]:
        assert set(topic["question"]) == {"id", "prompt", "options"}
        assert len(topic["question"]["options"]) == 4


def test_correct_answer_scores_exactly_once(client, study_set):
    chapter_id = study_set["chapters"][0]["id"]
    topic = quiz(client, chapter_id)["topics"][0]
    question_id = topic["question"]["id"]
    right = correct_index(question_id)

    first = answer(client, question_id, right)
    assert first.status_code == 200
    body = first.json()
    assert body["correct"] is True
    assert body["points_awarded"] == P
    assert body["chapter"]["earned"] == P
    assert body["replacement_pending"] is False

    # Answering the same question again (a double-click) must not score twice.
    second = answer(client, question_id, right)
    assert second.status_code == 409

    state = quiz(client, chapter_id)
    assert state["earned"] == P
    mastered = next(t for t in state["topics"] if t["id"] == topic["id"])
    assert mastered["mastered"] is True and mastered["question"] is None


def test_wrong_answer_scores_zero_and_brings_a_new_question_on_the_same_topic(client, study_set):
    chapter_id = study_set["chapters"][0]["id"]
    topic = quiz(client, chapter_id)["topics"][0]
    question = topic["question"]
    wrong = (correct_index(question["id"]) + 1) % 4

    response = answer(client, question["id"], wrong)
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["points_awarded"] == 0
    assert body["chapter"]["earned"] == 0
    assert body["correct_index"] == correct_index(question["id"])
    assert body["explanation"]
    assert body["replacement_pending"] is True

    # Eager mode: the replacement task already ran.
    after = next(t for t in quiz(client, chapter_id)["topics"] if t["id"] == topic["id"])
    assert after["mastered"] is False and after["preparing"] is False
    assert after["question"]["id"] != question["id"]
    assert after["question"]["prompt"] != question["prompt"]

    with SessionLocal() as db:
        statuses = db.scalars(select(Question.status).where(Question.topic_id == topic["id"])).all()
    assert sorted(statuses) == ["active", "wrong"]


def test_replacement_questions_never_repeat_a_previous_prompt(client, study_set):
    chapter_id = study_set["chapters"][0]["id"]
    topic_id = quiz(client, chapter_id)["topics"][0]["id"]
    prompts = []
    for _ in range(3):
        question = next(t for t in quiz(client, chapter_id)["topics"] if t["id"] == topic_id)["question"]
        prompts.append(question["prompt"])
        answer(client, question["id"], (correct_index(question["id"]) + 1) % 4)
    assert len(set(prompts)) == len(prompts)


def test_locked_quiz_returns_403_until_the_previous_chapter_reaches_the_threshold(client, study_set):
    first, second = study_set["chapters"][0], study_set["chapters"][1]
    assert second["quiz_unlocked"] is False

    locked = client.get(f"/api/chapters/{second['id']}/quiz")
    assert locked.status_code == 403
    assert f"Chapter {first['position']}" in locked.json()["detail"]

    # Answering a question of a locked chapter is refused too.
    with SessionLocal() as db:
        locked_question = db.scalar(
            select(Question.id).join(Topic).where(Topic.chapter_id == second["id"], Question.status == "active")
        )
    assert answer(client, locked_question, 0).status_code == 403

    # Master topics of chapter 1 until it reaches its threshold; only the crossing answer reports the unlock.
    unlocked = None
    for topic in quiz(client, first["id"])["topics"]:
        body = answer(client, topic["question"]["id"], correct_index(topic["question"]["id"])).json()
        if body["chapter"]["earned"] < first["unlock_threshold"]:
            assert body["unlocked_chapter"] is None
        elif unlocked is None:
            unlocked = body["unlocked_chapter"]
            assert unlocked == {"id": second["id"], "title": second["title"]}
        else:
            assert body["unlocked_chapter"] is None
    assert unlocked is not None

    assert client.get(f"/api/chapters/{second['id']}/quiz").status_code == 200
    detail = client.get(f"/api/study-sets/{study_set['id']}").json()
    assert detail["chapters"][1]["quiz_unlocked"] is True
    assert detail["chapters"][0]["completed"] is True


def test_progress_total_never_changes(client, study_set):
    set_id = study_set["id"]
    total = study_set["progress"]["total"]
    assert total == sum(c["max"] for c in study_set["chapters"])
    assert total == len(study_set["chapters"]) * config.QUESTIONS_PER_CHAPTER * P

    chapter_id = study_set["chapters"][0]["id"]
    for _ in range(3):  # wrong answers create replacement questions...
        question = quiz(client, chapter_id)["topics"][0]["question"]
        body = answer(client, question["id"], (correct_index(question["id"]) + 1) % 4).json()
        assert body["progress"]["total"] == total
    question = quiz(client, chapter_id)["topics"][0]["question"]
    body = answer(client, question["id"], correct_index(question["id"])).json()  # ...and a right one
    assert body["progress"] == {"earned": P, "total": total, "percent": P * 100 // total}

    detail = client.get(f"/api/study-sets/{set_id}").json()
    assert detail["progress"]["total"] == total
    assert detail["progress"]["earned"] == sum(c["earned"] for c in detail["chapters"])


def test_other_users_questions_and_quizzes_are_hidden(client, study_set):
    chapter_id = study_set["chapters"][0]["id"]
    question_id = quiz(client, chapter_id)["topics"][0]["question"]["id"]
    with SessionLocal() as db:
        # Hand the whole set to someone else: for the dev user it must now look like it doesn't exist.
        other = User(auth_id="someone-else")
        db.add(other)
        db.flush()
        db.get(StudySet, study_set["id"]).user_id = other.id
        db.commit()
    assert client.get(f"/api/chapters/{chapter_id}/quiz").status_code == 404
    assert answer(client, question_id, 0).status_code == 404


def test_selected_index_must_be_between_0_and_3(client, study_set):
    question_id = quiz(client, study_set["chapters"][0]["id"])["topics"][0]["question"]["id"]
    assert answer(client, question_id, 4).status_code == 422
    assert answer(client, question_id, -1).status_code == 422
    with SessionLocal() as db:
        assert db.get(Question, question_id).status == "active"
