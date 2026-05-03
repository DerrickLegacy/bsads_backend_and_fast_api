from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from api.config import settings

# SQLAlchemy engine — one per application, reused across all requests
engine = create_engine(settings.database_url, pool_pre_ping=True)

# Session factory — each request gets its own session opened from this
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models inherit from this Base so SQLAlchemy knows about them
Base = declarative_base()


def get_db():
    """
    FastAPI dependency: yields a DB session for a request then closes it.
    Use with: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
