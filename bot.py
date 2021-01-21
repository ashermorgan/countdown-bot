# Import dependencies
from discord.ext import commands
from dotenv import load_dotenv
import os
import re



# Load list of channels
channels = []
with open(os.path.join(os.path.dirname(__file__), "channels.txt"), "a+") as f:
    f.seek(0)
    lines = f.readlines()
    for line in lines:
        try:
            channels += [int(line)]
        except:
            pass



class Message:
    def __init__(self, obj):
        self.channel    = obj.channel.id
        self.number     = int(re.findall("^[0-9,]+", obj.content)[0].replace(",",""))
        self.author     = f"{obj.author.name}#{obj.author.discriminator}"



async def loadMessages(channel, depth=1000):
    # Read messages
    messages = await channel.history(limit=depth).flatten()
    messages.reverse()

    # Parse messages
    parsedMessages = []
    for message in messages:
        try:
            # Parse message
            parsedMessage = Message(message)

            # Process message
            if (len(parsedMessages) != 0 and parsedMessage.author == parsedMessages[-1].author):
                await message.add_reaction("⛔")
            elif (len(parsedMessages) != 0 and parsedMessage.number + 1 != parsedMessages[-1].number):
                await message.add_reaction("❌")
            else:
                parsedMessages += [parsedMessage]
        except:
            pass



# Create Discord bot
bot = commands.Bot(command_prefix = "!")



@bot.event
async def on_ready():
    for channel in channels:
        await loadMessages(bot.get_channel(channel))

@bot.event
async def on_message(obj):
    if (obj.channel.id in channels and obj.author.name != "countdown-bot"):
        await loadMessages(bot.get_channel(obj.channel.id), depth=15)



# Run bot
load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
