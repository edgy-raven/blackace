from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .basic import Base


class ServerProfile(Base):
    __tablename__ = "server_profile"
    discord_user = Column(Integer, primary_key=True)

    bbo_main_account = relationship("BBOMain", uselist=False, backref="server_profile")
    bbo_representing = relationship("BBORepresentative", backref="server_profile")

    def is_linked(self, bbo_user):
        return bbo_user == self.bbo_main_account.bbo_user or any(
            bbo_user == r.bbo_user for r in self.bbo_representing)


class BBOProfile(Base):
    __tablename__ = "bbo_profile"
    bbo_user = Column(String, primary_key=True)

    discord_main = relationship("BBOMain", uselist=False, backref="bbo_profile")
    discord_represented = relationship("BBORepresentative", backref="bbo_profile")


class BBOMain(Base):
    __tablename__ = 'bbo_main'
    bbo_user = Column(String, ForeignKey('bbo_profile.bbo_user'), primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'), unique=True, nullable=False)


class BBORepresentative(Base):
    __tablename__ = 'bbo_representative'
    bbo_user = Column(String, ForeignKey('bbo_profile.bbo_user'), primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'))
