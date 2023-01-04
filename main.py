import json
import logging

import interactions

import bot_datastore


if __name__ == '__main__':
    keyring = json.load(open('keyring.json'))

    bot = interactions.Client(
        token=keyring['bot_token'], 
        default_scope=keyring['served_guild']
    )
    bot.load('bot_extensions.challenge')
    bot.load('bot_extensions.profile')
    
    @bot.event(name='on_ready')
    async def verify_served_guilds():
        if not (len(bot.guilds) == 1 and bot.guilds[0].id == keyring['served_guild']):
            logging.critical("Present in unexpected guild. Shutting down.")
            await bot._stop()

    bot.start()
