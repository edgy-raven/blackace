from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import urlparse

from typing import List

import interactions
import requests


@dataclass
class BoardDetails:
    number: int
    hero_result: str
    hero_lin: str
    hero_score : int
    hero_imps : int 
    villain_result: str
    villain_lin: str
    villain_score : int
    villain_imps : int

    
@dataclass
class MatchDetails:
    match_format : str
    hero : str
    villain : str
    boards : List[BoardDetails]
    
    def total_score(self, prop):
        return sum(getattr(board, prop) for board in self.boards)
    
    def to_discord_embed(self):
        line_sep = '\n+----+---------------+---------------+-----+\n'
        embed = interactions.Embed(
            title=f"{self.match_format} Challenge",
            description=(
                f"**{self.hero}** - ({sum(board.hero_imps for board in self.boards)}) \n"\
                f"**{self.villain}** - ({sum(board.villain_imps for board in self.boards)})"
            ),
            fields=[
                interactions.EmbedField(
                    name='Board Details',
                    value= (
                        f'```     |{self.hero:^15}|{self.villain:^15}|{"imps":10}' +
                        line_sep +
                        line_sep.join(
                            f'|{i:^4}|{board.hero_result:<8}|{board.hero_score:<6d}|{board.villain_result:<8}|{board.villain_score:<6d}|{board.hero_imps:<2}|{board.villain_imps:<2}|'
                            for i, board in enumerate(self.boards)
                        ) + 
                        line_sep + "```"
                    )
                ),
            ]
        )
        return embed

    
class BBOChallengeParser(HTMLParser):
    match_details_order = ['hero', 'match_format', 'villain']
    board_details_order = [
        'number', 
        'hero_lin', 'hero_result', 'hero_score', 'hero_imps',
        'villain_imps', 'villain_lin', 'villain_result', 'villain_score',
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
            self.boards[-1] = BoardDetails(**{
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
            search = re.search("\((.+)\)", data)
            if search:
                self.match_details.append(search.group(1))
        elif self.current_state == 'td':
            self.accumulator = self.accumulator or data

    def finalize(self):
        match_details_kwargs = {
            k: v 
            for k, v in zip(self.match_details_order, self.match_details)
        }
        match_details_kwargs['boards'] = self.boards[:-1]
        return MatchDetails(**match_details_kwargs)


class ChallengeExtension(interactions.Extension):
    def __init__(self, client):
        self.client = client

    @interactions.extension_command(
        name="parse_imp_challenge",
        description="Parses an IMP friend challenge from BBO.",
        options = [
            interactions.Option(
                name="matchlink",
                description="URL of BBO Friend Challenge Leaderboard Page",
                type=interactions.OptionType.STRING,
                required=True,
            ),
        ],
    )
    async def parse_imp_challenge(self, ctx: interactions.CommandContext, matchlink: str):
        parser = BBOChallengeParser()
    
        parsed_url = urlparse(matchlink)
        if parsed_url.scheme != 'https' or parsed_url.netloc != 'webutil.bridgebase.com':
            return
            # should throw an error back at the user
        
        parser.feed(requests.get(matchlink).text)
        match_details = parser.finalize()
        await ctx.send(embeds=match_details.to_discord_embed())


def setup(client):
    ChallengeExtension(client)
