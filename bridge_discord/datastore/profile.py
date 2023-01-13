import functools

import numpy as np
import scipy
from sqlalchemy import Column, ForeignKey, Float, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext import hybrid_property

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
    mmr_m = Column(Float, server_default=1200.0)
    mmr_s = Column(Float, server_default=400.0)

    discord_main = relationship("BBOMain", uselist=False, backref="bbo_profile")
    discord_represented = relationship("BBORepresentative", backref="bbo_profile")

    def update_mmr(self, other, win):
        # Message passing with approximate moment matching, aka TrueSkill
        def integrand(r, moment):
            other_cdf = scipy.stats.norm.cdf(r, other.mmr_m, other.mmr_s)
            return r ** moment * (
                scipy.stats.norm.pdf(r, self.mmr_m, self.mmr_s) *
                other_cdf if win else (1.0 - other_cdf) /
                scipy.stats.norm.cdf(
                    0,
                    other.mmr_m - self.mmr_m if win else self.mmr_m - other.mmr_m,
                    (self.mmr_s * self.mmr_s + other.mmr_s) ** 0.5
                )
            )
        self.mmr_m = scipy.integrate.quad(functools.partial(integrand, moment=1), -np.inf, np.inf)[0]
        m2 = scipy.integrate.quad(functools.partial(integrand, moment=2), -np.inf, np.inf)[0]
        self.mmr_s = (m2 - self.mmr_m*self.mmr_m)**0.5

    @hybrid_property
    def conservative_estimate(self):
        return self.mmr_m - 3.0 * self.mmr_s


class BBOMain(Base):
    __tablename__ = 'bbo_main'
    bbo_user = Column(String, ForeignKey('bbo_profile.bbo_user'), primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'), unique=True, nullable=False)


class BBORepresentative(Base):
    __tablename__ = 'bbo_representative'
    bbo_user = Column(String, ForeignKey('bbo_profile.bbo_user'), primary_key=True)
    discord_user = Column(Integer, ForeignKey('server_profile.discord_user'))
