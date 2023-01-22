from sqlalchemy import create_engine, Column, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker

_sessionmaker = None
Base = declarative_base()


def setup_connection():
    global _sessionmaker
    if _sessionmaker:
        return
    engine = create_engine("sqlite:///bridge_discord.db")
    _sessionmaker = sessionmaker(engine)
    Base.metadata.create_all(engine)


def Session():
    return _sessionmaker()


class CreatedAtMixin:
    created_at = Column(DateTime, server_default=func.now())
