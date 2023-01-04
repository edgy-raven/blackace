from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_sessionmaker = None
Base = declarative_base()


def setup_connection():
    global _sessionmaker
    if _sessionmaker:
        return
    engine = create_engine("sqlite:///blackace.db")
    _sessionmaker = sessionmaker(engine)
    Base.metadata.create_all(engine)


def Session():
    return _sessionmaker()
