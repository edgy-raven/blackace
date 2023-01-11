import json
import logging

import interactions


if __name__ == '__main__':
    keyring = json.load(open('keyring.json'))

    bot = interactions.Client(
        token=keyring['bot_token'],
        default_scope=keyring['served_guild'],
        intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_MEMBERS
    )
    bot.load('bridge_discord.extensions.challenge')
    bot.load('bridge_discord.extensions.tournament')
    bot.load('bridge_discord.extensions.profile')

    @bot.event(name='on_ready')
    async def verify_served_guilds():
        if not (len(bot.guilds) == 1 and bot.guilds[0].id == keyring['served_guild']):
            logging.critical("Present in unexpected guild. Shutting down.")
            await bot._stop()

    bot.start()
