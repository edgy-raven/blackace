import functools

from bridge_discord import datastore


class SessionedGuard:
    def __init__(self, **guard_coroutines_dict):
        self.guard_coroutines_dict = guard_coroutines_dict

    def __call__(self, func):
        coroutines_dict = self.guard_coroutines_dict

        class StateHolder:
            async def __call__(self, *args, **kwargs):
                with datastore.Session() as session:
                    self.session = session
                    for key, coro in coroutines_dict.items():
                        result = await coro(self, args[1], **kwargs)
                        setattr(self, key, result)
                    return await func(*args, **kwargs)
        return functools.wraps(func)(StateHolder())


async def failed_guard(ctx, message):
    await ctx.send(message, ephemeral=True)
    raise ValueError("Failed guard.")


async def assert_tournament_exists(guard_obj, ctx, **kwargs):
    tournament = datastore.TeamRRTournament.get_active_tournament(guard_obj.session)
    if not tournament:
        await failed_guard(ctx, "No tournament is currently running. Wait for one to start!")
    return tournament


async def assert_bbo_rep(guard_obj, ctx, **kwargs):
    bbo_user = kwargs.get('bbo_user')
    profile = guard_obj.session.get(datastore.ServerProfile, int(ctx.user.id))
    if not bbo_user:
        if not profile.bbo_main_account:
            await failed_guard(ctx, "You are not linked to BBO. Contact a helper to link.")
        bbo_user = profile.bbo_main_account.bbo_user
    elif not profile.is_linked(bbo_user):
        await failed_guard(ctx, f"You are not a representative of {bbo_user}. You cannot sign-up as them.")
    return bbo_user
