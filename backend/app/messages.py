"""
Texts for the user that the backend sends: a code plus values instead of a finished English sentence,
e.g. {"code": "generating_chapter", "values": {"position": 2, "total": 5}}

The frontend turns them into English or Greek, whichever language the user chose (the "message."
texts in frontend/src/i18n.js), so a new code needs a text there in both languages
Used for a study set's progress (status_message) and failure reason (error), and for the API's
error answers (HTTPException's detail)
"""


def message(code: str, **values) -> dict:
    return {"code": code, "values": values}
