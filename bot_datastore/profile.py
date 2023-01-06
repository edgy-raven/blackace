from sqlalchemy import Column, ForeignKey, Boolean, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .basic import Base


class ServerProfile(Base):
    __tablename__ = "server_profile"
    discord_user = Column(Integer, primary_key=True)

    bbo_main_account = relationship("BBOMain", uselist=False, backref='server_profile')
    bbo_representing = relationship("BBORepresentative", backref='server_profile')


class BBOProfile(Base):
    __tablename__ = "bbo_profile"
    bbo_user = Column(String, primary_key=True)
    

class BBOMain(Base):
    __tablename__ = 'bbo_main'
    bbo_user = Column(String, ForeignKey('bbo_profile.bbo_user'), primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'), unique=True, nullable=False)


class BBORepresentative(Base):
    __tablename__ = 'bbo_representative'
    bbo_user = Column(String, ForeignKey('bbo_profile.bbo_user'), primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'))
