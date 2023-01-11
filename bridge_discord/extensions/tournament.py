import logging

import interactions

from bridge_discord import datastore


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
    async def signup(self, ctx, bbo_user=None):
        # todo: abstract this out into guards
        with datastore.Session() as session:
            profile_model = session.get(datastore.ServerProfile, int(ctx.user.id))
            if not bbo_user:
                bbo_user = profile_model.bbo_main_account.bbo_user
            elif not profile_model.is_linked(bbo_user):
                await ctx.send(
                    f"You are not a representative of {bbo_user}. You cannot sign-up as them.",
                    ephemeral=True
                )
                return
            active_tournament = datastore.TeamRRTournament.get_active_tournament(session)
            if not active_tournament:
                await ctx.send(
                    "No tournament is currently running. Wait for one to start!",
                    ephemeral=True
                )
                return
            session.add(
                datastore.TeamRREntry(tournament_id=active_tournament.tournament_id, bbo_user=bbo_user)
            )
            session.commit()
        await ctx.send("Signed up for the upcoming tournament!", ephemeral=True)

    @interactions.extension_command(
        name="team_rr_drop",
        description="Drop registration from the currently active team round robin tournament.",
        options=[
            bbo_user_option_factory("BBO user if dropping for someone else."),
        ]
    )
    async def drop_tournament(self, ctx, bbo_user=None):
        with datastore.Session() as session:
            profile_model = session.get(datastore.ServerProfile, int(ctx.user.id))
            if not bbo_user:
                bbo_user = profile_model.bbo_main_account.bbo_user
            elif not profile_model.is_linked(bbo_user):
                await ctx.send(
                    f"You are not a representative of {bbo_user}. You cannot sign-up as them.",
                    ephemeral=True
                )
                return
            active_tournament = datastore.TeamRRTournament.get_active_tournament(session)
            if not active_tournament:
                await ctx.send(
                    "No tournament is currently running. Wait for one to start!",
                    ephemeral=True
                )
                return

            entry_model = session.get(datastore.TeamRREntry, (active_tournament.tournament_id, bbo_user))
            if not entry_model:
                await ctx.send(
                    f"{bbo_user} is not currently signed up for the upcoming tournament.",
                    ephemeral=True
                )
                return
            session.delete(entry_model)
            session.commit()
        await ctx.send("Successfully dropped out from the upcoming tournament!", ephemeral=True)

    @interactions.extension_command(
        name="team_rr_info",
        description="Displays information about the currently active team round robin tournament.",
    )
    async def team_rr_info(self, ctx):
        profile_embed = interactions.Embed()
        with datastore.Session() as session:
            tournament_model = datastore.TeamRRTournament.get_active_tournament(session)
            if not tournament_model:
                await ctx.send("No tournament is currently running. Wait for one to start!")
            profile_embed.title = f"Team RR Tournament: {tournament_model.tournament_name}"
            profile_embed.add_field(
                name="Tournament Details",
                value="\n".join(
                    f"{key}: {value}"
                    for key, value in {
                        "Challenge format": tournament_model.scoring_method,
                        "Boards per match": tournament_model.segment_boards,
                        "Created at": tournament_model.created_at
                    }.items()
                )
            )
            bbo_users = [p.bbo_user for p in tournament_model.participants]
            mention_strings = []
            for bbo_user in bbo_users:
                bbo_model = session.get(datastore.BBOProfile, bbo_user)
                if bbo_model.discord_main:
                    discord_user = await interactions.get(
                        self.client, interactions.User, object_id=bbo_model.discord_main.discord_user)
                    mention_strings.append(f" [{discord_user.mention}]")
                else:
                    mention_strings.append("")
            if tournament_model.state == "signup":
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
