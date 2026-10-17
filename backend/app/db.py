from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config

# pool_pre_ping replaces connections that the database closed while they sat idle.
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
