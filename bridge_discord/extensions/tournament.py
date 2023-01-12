import logging

import interactions
from sqlalchemy.exc import IntegrityError

from bridge_discord import datastore
from bridge_discord.extensions import utilities


def bbo_user_option_factory(description):
    return interactions.Option(
        name="bbo_user",
        description=description,
        type=interactions.OptionType.STRING
    )


class TeamRRManagerExtension(interactions.Extension):
    @interactions.extension_command(
        name="team_rr_create",
        description="Creates a team round robin tournament",
        default_member_permissions=interactions.Permissions.MANAGE_MESSAGES,
        options=[
            interactions.Option(
                name="tournament_name",
                description="The name of the new tournament.",
                type=interactions.OptionType.STRING,
                required=True
            )
        ]
    )
    async def create_tournament(self, ctx, tournament_name):
        with datastore.Session() as session:
            session.add(
                datastore.TeamRRTournament(state="signup", tournament_name=tournament_name))
            session.commit()
        await ctx.send("Successfully created a new team round robin tournament!")

    @interactions.extension_command(
        name="team_rr_signup",
        description="Sign up for the currently active team round robin tournament.",
        options=[
            bbo_user_option_factory("BBO user if signing up for someone else."),
        ]
    )
    @utilities.SessionedGuard(
        active_tournament=utilities.assert_tournament_exists,
        bbo_user=utilities.assert_bbo_rep
    )
    async def signup(self, ctx, *, bbo_user=None):
        guard = self.signup.coro
        guard.session.add(
            datastore.TeamRREntry(
                tournament_id=guard.active_tournament.tournament_id,
                bbo_user=guard.bbo_user
            )
        )
        try:
            guard.session.commit()
            await ctx.send("Signed up for the upcoming tournament!", ephemeral=True)
        except IntegrityError:
            await ctx.send("You are already signed up for the upcoming tournament.", ephemeral=True)

    @interactions.extension_command(
        name="team_rr_drop",
        description="Drop registration from the currently active team round robin tournament.",
        options=[
            bbo_user_option_factory("BBO user if dropping for someone else."),
        ]
    )
    @utilities.SessionedGuard(
        active_tournament=utilities.assert_tournament_exists,
        bbo_user=utilities.assert_bbo_rep
    )
    async def drop_tournament(self, ctx, *, bbo_user=None):
        guard = self.drop_tournament.coro
        entry_model = guard.session.get(datastore.TeamRREntry, (guard.active_tournament.tournament_id, guard.bbo_user))
        if not entry_model:
            await ctx.send(
                f"{guard.bbo_user} is not currently signed up for the upcoming tournament.",
                ephemeral=True
            )
        guard.session.delete(entry_model)
        guard.session.commit()
        await ctx.send("Successfully dropped out from the upcoming tournament!", ephemeral=True)

    @interactions.extension_command(
        name="team_rr_info",
        description="Displays information about the currently active team round robin tournament.",
    )
    @utilities.SessionedGuard(active_tournament=utilities.assert_tournament_exists)
    async def tournament_info(self, ctx):
        guard = self.tournament_info.coro

        profile_embed = interactions.Embed(title=f"Team RR Tournament: {guard.active_tournament.tournament_name}")
        profile_embed.add_field(
            name="Tournament Details",
            value="\n".join(
                f"{key}: {value}"
                for key, value in {
                    "Challenge format": guard.active_tournament.scoring_method,
                    "Boards per match": guard.active_tournament.segment_boards,
                    "Created at": guard.active_tournament.created_at
                }.items()
            )
        )
        bbo_users = [p.bbo_user for p in guard.active_tournament.participants]
        mention_strings = []
        # TODO: abstract this out to a utility function
        for bbo_user in bbo_users:
            bbo_model = guard.session.get(datastore.BBOProfile, bbo_user)
            if bbo_model.discord_main:
                discord_user = await interactions.get(
                    self.client, interactions.User, object_id=bbo_model.discord_main.discord_user)
                mention_strings.append(f" [{discord_user.mention}]")
            else:
                mention_strings.append("")
        if guard.active_tournament.state == "signup":
            profile_embed.add_field(
                name="Currently Registered Players",
                value="\n".join(
                    f"\t    • {bbo_user}{mention}"
                    for bbo_user, mention in zip(bbo_users, mention_strings)
                )
            )
        await ctx.send(embeds=profile_embed)


def setup(client):
    datastore.setup_connection()
    with datastore.Session() as session:
        active_tournament = session.query(
            datastore.TeamRRTournament).where(datastore.TeamRRTournament.state != "Inactive").all()
        if active_tournament and len(active_tournament) > 1:
            logging.critical("There can only be one active Team RR tournament.")
            raise ValueError("Failed setup assumptions.")

    TeamRRManagerExtension(client)
