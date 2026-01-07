from shared.db.base import get_db_engine, get_session_local
from .settings import settings

engine = get_db_engine(settings.DATABASE_URL)
SessionLocal = get_session_local(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
