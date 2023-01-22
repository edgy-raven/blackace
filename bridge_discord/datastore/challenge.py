import enum
from html.parser import HTMLParser
import re
from urllib.parse import urlparse

import requests
from sqlalchemy import Column, ForeignKey, Enum, Integer, String, Float
from sqlalchemy.orm import relationship

from .basic import Base, CreatedAtMixin


class ScoringMethod(enum.Enum):
    IMPS = 0
    MPS = 1


class FriendChallenge(Base, CreatedAtMixin):
    __tablename__ = "bbo_friend_challenge"

    match_id = Column(Integer, primary_key=True, autoincrement=True)
    scoring_method = Column(Enum(ScoringMethod))
    hero = Column(String)
    villain = Column(String)

    boards = relationship("FriendChallengeBoard", backref="bbo_friend_challenge")
    hero_profile = relationship(
        "BBOProfile",
        foreign_keys=hero,
        primaryjoin="FriendChallenge.hero == BBOProfile.bbo_user",
        backref="bbo_friend_challenge_hero",
        uselist=False
    )
    villain_profile = relationship(
        "BBOProfile",
        foreign_keys=villain,
        primaryjoin="FriendChallenge.villain == BBOProfile.bbo_user",
        backref="bbo_friend_challenge_villain",
        uselist=False
    )

    @classmethod
    def init_from_matchlink(cls, matchlink):
        parsed_url = urlparse(matchlink)
        if parsed_url.scheme != 'https' or parsed_url.netloc != 'webutil.bridgebase.com':
            raise ValueError('Matchlink is not from webutil.bridgebase.com. Refusing to parse.')

        parser = BBOChallengeParser()
        parser.feed(requests.get(matchlink).text)
        return parser.finalize()


class FriendChallengeBoard(Base):
    __tablename__ = "bbo_friend_challenge_board"

    match_id = Column(Integer, ForeignKey("bbo_friend_challenge.match_id"), primary_key=True)
    number = Column(Integer, primary_key=True)
    hero_result = Column(String)
    hero_score = Column(Integer)
    hero_matchscore = Column(Float)
    hero_lin = Column(String)
    villain_result = Column(String)
    villain_score = Column(Integer)
    villain_matchscore = Column(Float)
    villain_lin = Column(String)


class BBOChallengeParser(HTMLParser):
    match_details_order = ['hero', 'scoring_method', 'villain']
    board_details_order = [
        'number',
        'hero_lin', 'hero_result', 'hero_score', 'hero_matchscore',
        'villain_matchscore', 'villain_lin', 'villain_result', 'villain_score',
    ]

    def __init__(self):
        self.context_stack = []
        self.boards = [[]]
        self.match_details = []
        self.accumulator = None
        super().__init__()

    @property
    def current_state(self):
        return self.context_stack[-1] if self.context_stack else None

    def handle_starttag(self, tag, attrs):
        if tag == 'hr':
            return
        state = self.current_state
        if state is None and any(attr == ('class', 'handrecords') for attr in attrs):
            state = 'handrecords'
        elif state == 'handrecords':
            state = next(
                (
                    class_id
                    for class_id in ('odd', 'even', 'username', 'final_score')
                    if any(attr == ('class', class_id) for attr in attrs)
                ),
                state
            )
        elif state in ('odd', 'even') and tag == 'td':
            state = 'td'
        if state == 'td' and tag == 'a':
            self.boards[-1].append(next(
                (attr[1] for attr in attrs if attr[0] == 'href'), None))
        self.context_stack.append(state)

    def handle_endtag(self, tag):
        prev_state = self.context_stack.pop()
        if prev_state == 'odd' or prev_state == 'even':
            self.boards[-1] = FriendChallengeBoard(**{
                k: v
                for k, v in zip(self.board_details_order, self.boards[-1])
            })
            self.boards.append([])
        elif prev_state == 'td' and tag == 'td':
            if len(self.boards[-1]) in (0, 3, 4, 5, 8):
                self.boards[-1].append(int(self.accumulator or '0'))
            else:
                self.boards[-1].append(self.accumulator)
            self.accumulator = None

    def handle_data(self, data):
        if self.current_state == 'username':
            self.match_details.append(data)
        elif self.current_state == 'final_score':
            search = re.search(r"\((.+)\)", data)
            if search:
                self.match_details.append(ScoringMethod[search.group(1).upper()])
        elif self.current_state == 'td':
            self.accumulator = self.accumulator or data

    def finalize(self):
        match_details_kwargs = {
            k: v
            for k, v in zip(self.match_details_order, self.match_details)
        }
        match_details_kwargs['boards'] = self.boards[:-1]
        return FriendChallenge(**match_details_kwargs)
