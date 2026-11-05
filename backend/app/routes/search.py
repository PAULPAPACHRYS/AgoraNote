"""
Full-text search across all of the user's chapters: GET /api/search?q=...

Uses PostgreSQL's built-in full-text search, no extra search engine:
- to_tsvector(text) turns a chapter's search_text into a list of normalised words ("lexemes")
- websearch_to_tsquery(q) turns what the user typed into a query (words, "a phrase", -excluded)
- `document @@ query` is true when the chapter matches, the GIN index on chapters makes this fast
- ts_rank scores how well it matches (best first), ts_headline cuts out a snippet around the matches
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Chapter, StudySet, User
from app.schemas import SearchResult

router = APIRouter(prefix="/api")

MAX_RESULTS = 20  # the results page shows at most this many chapters

# 'simple' configuration only lowercases words (no language-specific stemming), so it works the
#same for Greek and English. Written as a literal so the expression matches the GIN index exactly
SIMPLE = literal_column("'simple'::regconfig")

# ts_headline marks matches with [[ ]]; the frontend turns those into <mark>, so no HTML comes from here
HEADLINE_OPTIONS = "StartSel=[[, StopSel=]], MinWords=10, MaxWords=25, MaxFragments=2, FragmentDelimiter=\" … \""


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(max_length=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # best-matching chapters (max 20), each with its study set and a highlighted snippet
    q = q.strip()
    if not q:
        return []

    document = func.to_tsvector(SIMPLE, Chapter.search_text)
    query = func.websearch_to_tsquery(SIMPLE, q)  # accepts what people type: words, "phrases", -not
    rank = func.ts_rank(document, query)
    # one SQL query: join each chapter to its study set, keep only the user's matching chapters, 
    #best match first (Chapter.id breaks ties so the order is stable)
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
    return [row._asdict() for row in rows]  # each row becomes a dict with the labels above as keys
