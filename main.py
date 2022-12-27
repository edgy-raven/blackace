import interactions
import json

import bot_datastore


if __name__ == "__main__":
    keyring = json.load(open("keyring.json"))

    bot = interactions.Client(keyring["bot_token"])
    bot.load('bot_extensions.challenge')
    bot.load('bot_extensions.profile')

    bot_datastore.setup_connection()
    bot.start()
