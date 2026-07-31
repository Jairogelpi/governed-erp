from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from erpguard.db.base import Base
from erpguard.config import settings

_url = settings.database_url
_is_sqlite = _url.startswith("sqlite")
_is_sqlite_memory = _is_sqlite and ":memory:" in _url

if _is_sqlite_memory:
    # In-memory SQLite: StaticPool keeps the single connection alive across uses.
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
elif _is_sqlite:
    # File SQLite: NullPool closes the physical connection after every session.close()
    # so the OS-level write lock is released immediately. QueuePool (the default)
    # would keep connections alive in the pool, causing "database is locked" when
    # the next test tries to write before the pooled connection fully releases.
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
else:
    engine = create_engine(_url)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # WAL mode: readers never block writers; writers never block readers.
        cursor.execute("PRAGMA journal_mode=WAL")
        # Retry for up to 30 s before raising "database is locked".
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    import erpguard.db.models  # noqa: F401
    import erpguard.db.model_packages  # noqa: F401
    import erpguard.db.model_packages.identity  # noqa: F401
    import erpguard.db.model_packages.connections  # noqa: F401
    import erpguard.db.model_packages.events  # noqa: F401
    import erpguard.db.model_packages.candidate  # noqa: F401
    import erpguard.db.model_packages.event_links  # noqa: F401
    import erpguard.db.model_packages.shadow  # noqa: F401
    import erpguard.db.model_packages.decision_intelligence  # noqa: F401

    Base.metadata.create_all(bind=engine)
