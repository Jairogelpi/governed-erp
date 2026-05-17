from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    import erpguard.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
