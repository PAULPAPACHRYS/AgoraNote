"""
The database connection
- `engine` knows how to connect to Postgres and keeps a small pool of open connections to reuse
- `SessionLocal()` creates a *session*: a unit of work in which you query and change ORM objects
  `db.commit()` writes the changes to the database, `db.rollback()` throws them away
- `get_db` gives each API request its own session (the worker creates its own with SessionLocal())
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config

#pool_pre_ping replaces connections that the database closed while they sat idle
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency: one session per request, always closed afterwards

    Used as `db: Session = Depends(get_db)`, FastAPI runs the code up to `yield`, hands the session to
    the endpoint, and runs the `finally` part once the response is done, even if the endpoint failed
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
