from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Chapter, StudySet, User
from app.schemas import SearchResult

router = APIRouter(prefix="/api")

MAX_RESULTS = 20

# The 'simple' configuration only lowercases words (no language-specific stemming), so it works the
# same for Greek and English. Written as a literal so the expression matches the GIN index exactly.
SIMPLE = literal_column("'simple'::regconfig")

# ts_headline marks matches with [[ ]]; the frontend turns those into <mark>, so no HTML comes from here.
HEADLINE_OPTIONS = "StartSel=[[, StopSel=]], MinWords=10, MaxWords=25, MaxFragments=2, FragmentDelimiter=\" … \""


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(max_length=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = q.strip()
    if not q:
        return []

    document = func.to_tsvector(SIMPLE, Chapter.search_text)
    query = func.websearch_to_tsquery(SIMPLE, q)  # accepts what people type: words, "phrases", -not
    rank = func.ts_rank(document, query)
    rows = db.execute(
        select(
            StudySet.id.label("study_set_id"),
            StudySet.title.label("study_set_title"),
            Chapter.id.label("chapter_id"),
            Chapter.position.label("chapter_position"),
            Chapter.title.label("chapter_title"),
            func.ts_headline(SIMPLE, Chapter.search_text, query, HEADLINE_OPTIONS).label("snippet"),
        )
        .join(StudySet, Chapter.study_set_id == StudySet.id)
        .where(StudySet.user_id == user.id, document.op("@@")(query))
        .order_by(rank.desc(), Chapter.id)
        .limit(MAX_RESULTS)
    ).all()
    return [row._asdict() for row in rows]
