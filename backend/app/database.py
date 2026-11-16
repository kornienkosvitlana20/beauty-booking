from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str, **kwargs):
    """Створює engine; для SQLite вмикає перевірку зовнішніх ключів."""
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        kwargs.setdefault("connect_args", {"check_same_thread": False})
    eng = create_engine(url, **kwargs)
    if is_sqlite:

        @event.listens_for(eng, "connect")
        def _enable_fk(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
            # Вбудований lower() у SQLite не розуміє кирилицю — підключаємо Unicode-версію.
            dbapi_conn.create_function(
                "lower", 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True)

    return eng


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)  # pylint: disable=invalid-name
