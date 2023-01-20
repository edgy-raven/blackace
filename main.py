import argparse
import asyncio
import json
import logging
import time

import interactions

parser = argparse.ArgumentParser(description='start one or more bots.')
parser.add_argument('--keyring', default=open('keyring.json'), type=open, required=False)
parser.add_argument('--bot', default=None, type=str, required=False)


async def meta_main(args, keyring):
    awaitables = []
    for bot in keyring['bots']:
        process = await asyncio.create_subprocess_shell(
            f"python {__file__} --keyring {args.keyring.name} --bot {bot}")
        time.sleep(2.0)
        awaitables.append(process.wait())
    await asyncio.gather(*awaitables)


if __name__ == '__main__':
    args = parser.parse_args()
    keyring = json.load(args.keyring)

    if not args.bot:
        asyncio.run(meta_main(args, keyring))
    else:
        bot_keyring = keyring['bots'][args.bot]
        intents = interactions.Intents.DEFAULT
        for intent in bot_keyring.get('intents', []):
            intents = intents | getattr(interactions.Intents, intent)
        bot = interactions.Client(
            token=bot_keyring['bot_token'],
            default_scope=keyring['served_guild'],
            intents=intents,
        )
        for module in bot_keyring['modules']:
            bot.load(module)

        @bot.event(name='on_ready')
        async def verify_served_guilds():
            if not (len(bot.guilds) == 1 and bot.guilds[0].id == keyring['served_guild']):
                logging.critical("Present in unexpected guild. Shutting down.")
                await bot._stop()

        bot.start()
