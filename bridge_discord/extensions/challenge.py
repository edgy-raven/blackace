import interactions

from bridge_discord import datastore


class ChallengeExtension(interactions.Extension):
    @interactions.extension_command(
        name="parse_imp_challenge",
        description="Parses an IMP friend challenge from BBO.",
        options=[
            interactions.Option(
                name="matchlink",
                description="URL of BBO Friend Challenge Leaderboard Page",
                type=interactions.OptionType.STRING,
                required=True,
            ),
        ],
    )
    async def parse_imp_challenge(self, ctx: interactions.CommandContext, matchlink: str):
        with datastore.Session() as session:
            try:
                friend_challenge = datastore.FriendChallenge.init_from_matchlink(matchlink)
            except ValueError as e:
                await ctx.send(",".join(e.args), ephemeral=True)
                return
            session.add(friend_challenge)
            friend_challenge = session.merge(friend_challenge)

            line_sep = '\n+----+---------------+---------------+-----+\n'
            hero_str = (
                await friend_challenge.hero_profile.to_str_with_linked_mention(self.client)
                if friend_challenge.hero_profile
                else friend_challenge.hero
            )
            villain_str = (
                await friend_challenge.hero_profile.to_str_with_linked_mention(self.client)
                if friend_challenge.villain_profile
                else friend_challenge.villain
            )
            embed = interactions.Embed(
                title=f"{friend_challenge.scoring_method.name} Challenge",
                description=(
                    f"**{hero_str}** - ({sum(board.hero_matchscore for board in friend_challenge.boards)}) \n"
                    f"**{villain_str}** - ({sum(board.villain_matchscore for board in friend_challenge.boards)})"
                ),
                fields=[
                    interactions.EmbedField(
                        name='Board Details',
                        value=(
                            f'```     |{friend_challenge.hero:^15}|{friend_challenge.villain:^15}|{"imps":10}' +
                            line_sep +
                            line_sep.join(
                                (
                                    f'|{i+1:^4}|{board.hero_result:<8}|{board.hero_score:<6d}|'
                                    f'{board.villain_result:<8}|{board.villain_score:<6d}|'
                                    f'{board.hero_matchscore or "":<2}|{board.villain_matchscore or "":<2}|'
                                )
                                for i, board in enumerate(friend_challenge.boards)
                            ) +
                            line_sep + "```"
                        )
                    ),
                ]
            )
            await ctx.send(embeds=embed)


def setup(client):
    ChallengeExtension(client)
