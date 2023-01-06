import logging

import interactions
from sqlalchemy import and_

import bot_datastore

class TeamRRManagerExtension(interactions.Extension):
    @interactions.extension_command(
        name="team_rr_create",
        description="Creates a team round robin tournament",
        default_member_permissions = interactions.Permissions.MANAGE_MESSAGES,
        # Todo: adjustable parameters
    )
    async def create_tournament(self, ctx):
        with bot_datastore.Session() as session:
            tournament_model = bot_datastore.TeamRRTournament(state="signup")
            session.add(tournament_model)
            session.commit()
        await ctx.send("Successfully created a new team round robin tournament!")

    @interactions.extension_command(
        name="team_rr_signup",
        description="Sign up for the currently active team round robin tournament.",
        options=[
            interactions.Option(
                name="bbo_user", 
                description="BBO user if signing up for someone else.",
                type=interactions.OptionType.STRING
            )
        ]
    )
    async def signup(self, ctx, bbo_user=None):
        def process(bbo_user):
            with bot_datastore.Session() as session:
                if not bbo_user:
                    bbo_user = session.get(bot_datastore.ServerProfile, int(ctx.user.id)).bbo_main_account.bbo_user
                elif not session.query(bot_datastore.BBORepresentative).where(
                    and_(
                        bot_datastore.BBORepresentative.bbo_user == bbo_user,
                        bot_datastore.BBORepresentative.discord_user == int(ctx.user.id)
                    )
                ).first():
                    return f"You are not a representative of {bbo_user}. You cannot sign-up as them."
                active_tournament = bot_datastore.TeamRRTournament.get_active_tournament(session)
                if not active_tournament:
                    return "No tournament is currently running. Wait for one to start!"
                entry_model = bot_datastore.TeamRREntry(
                    tournament_id=active_tournament.tournament_id, bbo_user=bbo_user)
                session.add(entry_model)
                session.commit()
                return "Signed up for the upcoming tournament!"
        await ctx.send(process(bbo_user), ephemeral=True)


def setup(client):
    bot_datastore.setup_connection()
    with bot_datastore.Session() as session:
        active_tournament = session.query(
            bot_datastore.TeamRRTournament).where(bot_datastore.TeamRRTournament.state != "Inactive").all()
        if active_tournament and len(active_tournament) > 1:
            logger.critical("There can only be one active Team RR tournament.")
            raise ValueError("Failed setup assumptions.")

    TeamRRManagerExtension(client)
