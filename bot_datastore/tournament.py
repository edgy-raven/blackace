from sqlalchemy import Column, ForeignKey, DateTime, Integer, String 
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .basic import Base


class TeamRRTournament(Base):
    __tablename__ = "teamrr_tournament"

    tournament_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now())
    scoring_method = Column(String, default="IMPs")
    segment_boards = Column(Integer, default=7)
    state = Column(String, default="Inactive")

    participants = relationship("TeamRREntry", backref="teamrr_tournament")

    @classmethod
    def get_active_tournament(cls, session):
        return session.query(cls).where(cls.state != "Inactive").first()


class TeamRREntry(Base):
    __tablename__ = "teamrr_entries"

    tournament_id = Column(Integer, ForeignKey("teamrr_tournament.tournament_id"), primary_key=True)
    bbo_user = Column(String, ForeignKey("bbo_profile.bbo_user"), primary_key=True)
