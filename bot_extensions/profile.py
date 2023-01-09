import interactions
from sqlalchemy.exc import IntegrityError

import bot_datastore


class ProfileExtension(interactions.Extension):
    @interactions.extension_command(
        name="bbo_link",
        description="Links a discord user to a BBO user.",
        default_member_permissions=interactions.Permissions.MANAGE_MESSAGES,
        options=[
            interactions.Option(
                name="discord_user",
                description="Discord mention of user to be linked.",
                type=interactions.OptionType.USER,
                required=True
            ),
            interactions.Option(
                name="bbo_user",
                description="BBO name of user to be linked.",
                type=interactions.OptionType.STRING,
                required=True
            ),
            interactions.Option(
                name="proxy",
                description="Whether the Discord user is representing the BBO user.",
                type=interactions.OptionType.BOOLEAN,
            )
        ]
    )
    async def bbo_link(
        self,
        ctx: interactions.CommandContext,
        discord_user: interactions.api.models.member.Member,
        bbo_user: str,
        proxy: bool = False
    ):
        success = True
        with bot_datastore.Session() as session:
            model_cls = bot_datastore.BBORepresentative if proxy else bot_datastore.BBOMain
            model = model_cls(bbo_user=bbo_user, discord_user=int(discord_user.id))
            session.add(model)
            session.add(bot_datastore.BBOProfile(bbo_user=bbo_user))
            try:
                session.commit()
            except IntegrityError:
                success = False
        await ctx.send(
            f"Successfully linked {discord_user.mention} to {bbo_user}!" if success else
            f"Failed to link {discord_user.mention}! {bbo_user} is already linked.",
            ephemeral=True
        )

    @interactions.extension_command(
        name="bbo_unlink",
        description="Unlinks a BBO user.",
        default_member_permissions=interactions.Permissions.MANAGE_MESSAGES,
        options=[
            interactions.Option(
                name="bbo_user",
                description="BBO name to be unlinked.",
                type=interactions.OptionType.STRING,
                required=True
            )
        ]
    )
    async def bbo_unlink(self, ctx: interactions.CommandContext, bbo_user: str):
        success = True
        with bot_datastore.Session() as session:
            main_model = session.get(bot_datastore.BBOMain, bbo_user)
            if main_model:
                session.delete(main_model)
            representative_model = session.get(bot_datastore.BBORepresentative, bbo_user)
            if representative_model:
                session.delete(representative_model)
            if not (main_model or representative_model):
                success = False
            else:
                session.commit()
        await ctx.send(
            f"Successfully unlinked {bbo_user}!" if success else
            f"Did not find entry for {bbo_user}!",
            ephemeral=True
        )

    @interactions.extension_command(
        name="profile",
        description="Displays the profile of a user.",
        options=[
            interactions.Option(
                name="discord_user",
                description="Discord mention of user.",
                type=interactions.OptionType.USER,
                required=True
            )
        ]
    )
    async def profile(self, ctx: interactions.CommandContext, discord_user: interactions.api.models.member.Member):
        with bot_datastore.Session() as session:
            profile_model = session.get(bot_datastore.ServerProfile, int(discord_user.id))
            if not profile_model:
                await ctx.send("Failed to find profile for {discord_user.mention}!", ephemeral=True)
                return
            description = ""
            if profile_model.bbo_main_account:
                description += f"**BBO Username**: {profile_model.bbo_main_account.bbo_user}\n"
            if profile_model.bbo_representing:
                description += f"**Representing**: {', '.join(r.bbo_user for r in profile_model.bbo_representing)}\n"
            description = description or "No information to show."
        profile_embed = interactions.Embed(
            title=f"Card Games at 1430 Profile of User: `{discord_user.name}`",
            description=description
        )
        await ctx.send(embeds=profile_embed)

    @interactions.extension_listener(name="on_guild_member_add")
    async def add_guild_member_to_db(self, member):
        with bot_datastore.Session() as session:
            if not session.get(bot_datastore.ServerProfile, int(member.id)):
                model = bot_datastore.ServerProfile(discord_user=int(member.id))
                session.add(model)
                session.commit()

    @interactions.extension_listener(name="on_ready")
    async def sync_member_list(self):
        all_discord_users = [int(m.id) async for m in self.client.guilds[0].get_members()]
        with bot_datastore.Session() as session:
            for discord_user in all_discord_users:
                model = session.get(bot_datastore.ServerProfile, discord_user)
                if model:
                    continue
                session.add(bot_datastore.ServerProfile(discord_user=discord_user))
            session.commit()


def setup(client):
    bot_datastore.setup_connection()
    ProfileExtension(client)
