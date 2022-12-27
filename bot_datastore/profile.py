from sqlalchemy import Column, Boolean, Integer, String

from .basic import Base


class BBOLink(Base):
    __tablename__ = "bbolink"
    bbo_user = Column(String, primary_key=True)
    discord_user = Column(Integer)
    proxy = Column(Boolean)
