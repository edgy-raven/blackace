import logging
import random

from boltons.iterutils import chunked
import interactions
from sqlalchemy import and_
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
        name="create",
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
    async def create(self, ctx, tournament_name):
        with datastore.Session() as session:
            session.add(
                datastore.TeamRRTournament(state=datastore.TournamentState.SIGNUP, tournament_name=tournament_name)
            )
            session.commit()
        await ctx.send("Successfully created a new team round robin tournament!", ephemeral=True)

    @interactions.extension_command(
        name="signup",
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
        if guard.active_tournament.state is not datastore.TournamentState.SIGNUP:
            await utilities.failed_guard(ctx, "The active tournament is not currently accepting signups.")
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
        name="drop",
        description="Drop registration from the currently active team round robin tournament.",
        options=[
            bbo_user_option_factory("BBO user if dropping for someone else."),
        ]
    )
    @utilities.SessionedGuard(
        active_tournament=utilities.assert_tournament_exists,
        bbo_user=utilities.assert_bbo_rep
    )
    async def drop(self, ctx, *, bbo_user=None):
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
        name="info",
        description="Displays information about the currently active team round robin tournament.",
    )
    @utilities.SessionedGuard(active_tournament=utilities.assert_tournament_exists)
    async def info(self, ctx):
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
        if guard.active_tournament.state is datastore.TournamentState.SIGNUP:
            participant_strings = []
            for entry_model in guard.active_tournament.participants:
                if entry_model.bbo_profile.discord_main:
                    mention_string = await entry_model.bbo_profile.discord_main.server_profile.mention(self.client)
                    mention_string = f"[{mention_string}]"
                else:
                    mention_string = ""
                participant_strings.append(f"•{entry_model.bbo_user}\t{mention_string}")
            profile_embed.add_field(name="Currently Registered Players", value="\n".join(participant_strings))
        elif guard.active_tournament.state is datastore.TournamentState.STARTED:
            for team_number in range(guard.active_tournament.number_of_teams):
                team_members = guard.session.query(
                    datastore.TeamRREntry
                ).join(datastore.BBOProfile).filter(
                    and_(
                        datastore.TeamRREntry.tournament_id == guard.active_tournament.tournament_id,
                        datastore.TeamRREntry.team_number == team_number
                    )
                ).order_by(datastore.BBOProfile.conservative_mmr_estimate).all()
                profile_embed.add_field(
                    name=f"Team {team_number + 1}",
                    value="\n".join(f"•{member.bbo_user}" for member in team_members),
                    inline=team_number % 3 != 0 or team_number == 0
                )
        await ctx.send(embeds=profile_embed)

    @interactions.extension_command(
        name="start",
        description="Ends the signup phase, starts matches.",
        default_member_permissions=interactions.Permissions.MANAGE_MESSAGES
    )
    @utilities.SessionedGuard(active_tournament=utilities.assert_tournament_exists)
    async def start(self, ctx):
        guard = self.start_tournament.coro

        sorted_participants = sorted(
            guard.active_tournament.participants, key=lambda p: p.bbo_profile.conservative_mmr_estimate, reverse=True)
        for pot in chunked(sorted_participants, guard.active_tournament.number_of_teams):
            random.shuffle(pot)
            for ix, participant in enumerate(pot):
                participant.team_number = ix
        guard.active_tournament.state = datastore.TournamentState.STARTED
        guard.session.commit()
        await ctx.send("Tournament has been started and teams have been assigned.", ephemeral=True)


def setup(client):
    datastore.setup_connection()
    with datastore.Session() as session:
        active_tournament = session.query(
            datastore.TeamRRTournament
        ).where(datastore.TeamRRTournament.state != datastore.TournamentState.INACTIVE).all()
        if active_tournament and len(active_tournament) > 1:
            logging.critical("There can only be one active Team RR tournament.")
            raise ValueError("Failed setup assumptions.")

    TeamRRManagerExtension(client)
