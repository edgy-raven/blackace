from sqlalchemy import Column, ForeignKey, Boolean, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .basic import Base


class ServerProfile(Base):
    __tablename__ = "server_profile"
    discord_user = Column(Integer, primary_key=True)
    join_datetime = Column(DateTime, server_default=func.now())

    bbo_main_account = relationship("BBOMain", uselist=False, back_populates='server_profile')
    bbo_representing = relationship("BBORepresentative", back_populates='server_profile')


class BBOMain(Base):
    __tablename__ = 'bbo_main'
    bbo_user = Column(String, primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'), unique=True, nullable=False)

    server_profile = relationship("ServerProfile", back_populates='bbo_main_account')


class BBORepresentative(Base):
    __tablename__ = 'bbo_representative'
    bbo_user = Column(String, primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'))

    server_profile = relationship("ServerProfile", back_populates='bbo_representing')
