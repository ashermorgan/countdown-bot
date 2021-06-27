# Import dependencies
import json
import os

# Import modules
from src import CountdownBot



# Load settings
settings = {}
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json"), "a+") as f:
    f.seek(0)
    settings = json.load(f)



# Run countdown-bot
CountdownBot(settings["database"], settings["prefixes"]).run(settings["token"])
