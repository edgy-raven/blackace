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
            model = bot_datastore.BBOLink(bbo_user=bbo_user, discord_user=int(discord_user.id), proxy=proxy)
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
        success =  True
        with bot_datastore.Session() as session:
            model = session.get(bot_datastore.BBOLink, bbo_user)
            if model:
                session.delete(session.get(bot_datastore.BBOLink, bbo_user))
                session.commit()
            else:
                success = False
        await ctx.send(
            f"Successfully unlinked {bbo_user}!" if success else
            f"Did not find entry for {bbo_user}!", 
            ephemeral=True
        )

def setup(client):
    ProfileExtension(client)
