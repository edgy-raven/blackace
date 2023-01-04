import interactions
from sqlalchemy.exc import IntegrityError

import bot_datastore 


class ProfileExtension(interactions.Extension):
    @interactions.extension_command(
        name="bbo_link",
        description="Links a discord user to a BBO user.",
        default_member_permissions = interactions.Permissions.MANAGE_MESSAGES,
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
            model_cls = bot_datastore.BBOProxy if proxy else bot_datastore.BBOMain
            model = model_cls(bbo_user=bbo_user, discord_user=int(discord_user.id))
            session.add(model)
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
        default_member_permissions = interactions.Permissions.MANAGE_MESSAGES,
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
            main_model = session.get(bbo_datastore.BBOMain, bbo_user)
            if main_model:
                session.delete(main_model)
            representative_model = session.get(bbo_datastore.BBORepresentative, bbo_user)
            if representative_model:
                session.delete(representative_model)
            if not (main_model or representative_model):
                success = False
        await ctx.send(
            f"Successfully unlinked {bbo_user}!" if success else
            f"Did not find entry for {bbo_user}!", 
            ephemeral=True
        )

    @interactions.extension_listener(name="on_guild_member_add")
    async def add_guild_member_to_db(self, member):
        with bot_datastore.Session() as session:
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
