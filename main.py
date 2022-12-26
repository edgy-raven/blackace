import interactions
import json


if __name__ == "__main__":
    keyring = json.load(open("keyring.json"))
    
    bot = interactions.Client(keyring["bot_token"])
    bot.load('bot_extensions.challenge')

    bot.start()
