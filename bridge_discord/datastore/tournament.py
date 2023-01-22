import enum

from sqlalchemy import Column, ForeignKey, Enum, Integer, String
from sqlalchemy.orm import relationship

from .basic import Base, CreatedAtMixin
from .challenge import ScoringMethod


class TournamentState(enum.Enum):
    SIGNUP = 0
    STARTED = 1
    INACTIVE = 2


class TeamRRTournament(Base, CreatedAtMixin):
    __tablename__ = "teamrr_tournament"

    tournament_id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_name = Column(String)
    scoring_method = Column(Enum(ScoringMethod), default=ScoringMethod.IMPS)
    segment_boards = Column(Integer, default=7)
    number_of_teams = Column(Integer, default=4)
    state = Column(Enum(TournamentState))

    participants = relationship("TeamRREntry", backref="teamrr_tournament")

    @classmethod
    def get_active_tournament(cls, session):
        return session.query(cls).where(cls.state != "Inactive").first()


class TeamRREntry(Base):
    __tablename__ = "teamrr_entries"

    tournament_id = Column(Integer, ForeignKey("teamrr_tournament.tournament_id"), primary_key=True)
    bbo_user = Column(String, ForeignKey("bbo_profile.bbo_user"), primary_key=True, nullable=False)
    team_number = Column(Integer, nullable=True)

    bbo_profile = relationship("BBOProfile", uselist=False, backref="teamrr_entries")
