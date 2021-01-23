# Import dependencies
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
from matplotlib import pyplot as plt
import os
import re
import tempfile



# Global variables
channels = []
countdowns = {}
TIMEZONE = -8  # America/Los_Angeles



# Error classes
class MessageNotAllowedError(Exception):
    """Raised when someone posts twice in a row."""
    pass

class MessageIncorrectError(Exception):
    """Raised when someone posts an incorrect number."""
    pass



# Message class
class Message:
    """
    Represents a single, valid, countdown message.

    Attributes
    ----------
    id : int
        The message ID.
    channel : int
        The channel ID.
    author : str
        The message author (ex: "user#0000").
    number : int
        The message content.
    """

    def __init__(self, obj):
        self.channel    = obj.channel.id
        self.id         = obj.id
        self.timestamp  = obj.created_at
        self.author     = f"{obj.author.name}#{obj.author.discriminator}"
        self.number     = int(re.findall("^[0-9,]+", obj.content)[0].replace(",",""))

    def __str__(self) -> str:
        return f"{self.author}: {self.number}"

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Message): return False
        else: return self.id == o.id



# Countdown class
class Countdown:
    """
    Represents a countdown.

    Attributes
    ----------
    messages : list
        The (valid) messages belonging to the countdown.

    Methods
    -------
    addMessage
        Add a message to the list of messages.
    parseMessage
        Parse a message and adds it to the list of messages.
    """

    def __init__(self, messages):
        self.messages = messages

    def addMessage(self, message):
        """
        Add a message to the list of messages.

        Parameters
        ----------
        message : Message
            The message object.

        Raises
        ------
        MessageNotAllowedError
            If the author posted the last message.
        MessageIncorrectError
            If the message content is incorrect.
        """

        if (len(self.messages) != 0 and message.author == self.messages[-1].author):
            raise MessageNotAllowedError()
        elif (len(self.messages) != 0 and message.number + 1 != self.messages[-1].number):
            raise MessageIncorrectError()
        else:
            self.messages += [message]

    async def parseMessage(self, rawMessage):
        """
        Parse a message and add it to the list of messages.

        Notes
        -----
        If the message is invalid or incorrect, a reacted will be added accordingly.

        Parameters
        ----------
        rawMessage : obj
            The raw Discord message object.
        """

        try:
            # Parse message
            message = Message(rawMessage)

            # Add message
            self.addMessage(message)

            # Mark important messages
            if (message.number == 0):
                await rawMessage.add_reaction("🥳")
            if (message.number % 200 == 0):
                await rawMessage.pin()
        except MessageNotAllowedError:
            await rawMessage.add_reaction("⛔")
        except MessageIncorrectError:
            await rawMessage.add_reaction("❌")
        except:
            pass

    def stats(self):
        """
        Get countdown statistics.

        Returns
        -------
        dict
            A dictionary containing countdown statistics.
        """

        # Get basic statistics
        if (len(self.messages) > 0):
            total = self.messages[0].number
            current = self.messages[-1].number
            percentage = (total - current) / total * 100
            start = self.messages[0].timestamp
        else:
            total = 0
            current = 0
            percentage = 0
            start = datetime.utcnow()

        # Get rate statistics
        if (len(self.messages) > 1):
            rate = (total - current)/((self.messages[-1].timestamp - self.messages[0].timestamp) / timedelta(days=1))
            eta = datetime.utcnow() + timedelta(days=current/rate)
        else:
            rate = 0
            eta = datetime.utcnow()

        # Get list of progress
        progress = []
        for message in self.messages:
            progress += [{
                "time":message.timestamp,
                "progress":message.number
            }]

        # Get author contributors
        contributors = []
        authors = list(set([x.author for x in self.messages]))
        for author in authors:
            contributors += [{
                "author":author,
                "contributors":len([x for x in self.messages if x.author == author]),
            }]
        contributors = sorted(contributors, key=lambda x: x["contributors"], reverse=True)

        # Return stats
        return {
            "total": total,
            "current": current,
            "percentage": percentage,
            "progress": progress,
            "contributors": contributors,
            "start": start,
            "rate": rate,
            "eta": eta,
        }



# Load list of channels
with open(os.path.join(os.path.dirname(__file__), "channels.txt"), "a+") as f:
    f.seek(0)
    lines = f.readlines()
    for line in lines:
        try:
            channels += [int(line)]
        except:
            pass



# Create Discord bot
bot = commands.Bot(command_prefix = "!count ")



@bot.event
async def on_ready():
    # Print status
    print(f"Connected to Discord as {bot.user}")

    # Load messages
    for channel in channels:
        # Get messages
        rawMessages = await bot.get_channel(channel).history(limit=10100).flatten()
        rawMessages.reverse()

        # Create countdown
        countdowns[str(channel)] = Countdown([])

        # Load messages
        for rawMessage in rawMessages:
            await countdowns[str(channel)].parseMessage(rawMessage)

        # Print status
        print(f"Loaded messages from {bot.get_channel(channel)}")

@bot.event
async def on_message(obj):
    if (obj.channel.id in channels and obj.author.name != "countdown-bot"):
        await countdowns[str(obj.channel.id)].parseMessage(obj)
    try:
        await bot.process_commands(obj)
    except:
        pass



@bot.command()
async def contributors(ctx):
    """
    Get information about countdown contributors
    """

    # Get messages
    if (ctx.channel.id in channels):
        countdown = countdowns[str(ctx.channel.id)]
    else:
        countdown = countdowns[str(channels[0])]

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Get stats
    stats = countdown.stats()

    # Create plot
    plt.close()
    plt.title("Countdown Contributors")

    # Add data to graph
    x = [x["author"] for x in stats["contributors"]]
    y = [x["contributors"] for x in stats["contributors"]]
    plt.pie(y, labels=x, autopct="%1.1f%%", startangle = 90)

    # Save graph
    plt.savefig(tmp.name)
    file = discord.File(tmp.name, filename="image.png")

    # Create embed
    embed=discord.Embed(title="Countdown Contributors")
    embed.description = ""
    for i in range(0, len(x)):
        embed.description += f"**{i + 1}.** `{x[i]}` ({y[i]} contributions)\n"
    embed.set_image(url="attachment://image.png")

    # Send embed
    await ctx.send(file=file, embed=embed)

    # Remove temp file
    try:
        os.remove(tmp.name)
    except:
        print(f"Unable to delete temp file: {tmp.name}.")



@bot.command()
async def progress(ctx):
    """
    Get information about countdown progress
    """

    # Get messages
    if (ctx.channel.id in channels):
        countdown = countdowns[str(ctx.channel.id)]
    else:
        countdown = countdowns[str(channels[0])]

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Get stats
    stats = countdown.stats()

    # Create plot
    plt.close()
    plt.title("Countdown Progress")
    plt.xlabel("Time")
    plt.ylabel("Progress")
    plt.gcf().autofmt_xdate()

    # Add data to graph
    x = [stats["start"] + timedelta(hours=TIMEZONE)] + [x["time"] + timedelta(hours=TIMEZONE) for x in stats["progress"]]
    y = [0] + [x["progress"] for x in stats["progress"]]
    plt.plot(x, y)

    # Save graph
    plt.savefig(tmp.name)
    file = discord.File(tmp.name, filename="image.png")

    # Calculate embed data
    start = (stats["start"] + timedelta(hours=TIMEZONE)).date()
    startDiff = (datetime.utcnow() - stats["start"]).days
    end = (stats["eta"] + timedelta(hours=TIMEZONE)).date()
    endDiff = (stats["eta"] - datetime.utcnow()).days
    if endDiff < 0: endDiff = 0

    # Create embed
    embed=discord.Embed(title="Countdown Progress")
    embed.description = f"**Progress:** {stats['total'] - stats['current']} / {stats['total']} ({round(stats['percentage'], 2)}%)\n"
    embed.description += f"**Average Progress per Day:** {round(stats['rate'], 2)}\n"
    embed.description += f"**Start Date:** {start} ({startDiff} days ago)\n"
    embed.description += f"**Estimated End Date:** {end} ({endDiff} days from now)\n"
    embed.set_image(url="attachment://image.png")

    # Send embed
    await ctx.send(file=file, embed=embed)

    # Remove temp file
    try:
        os.remove(tmp.name)
    except:
        print(f"Unable to delete temp file: {tmp.name}.")



# Command aliases
@bot.command()
async def c(ctx):
    """
    Alias for !count contributors
    """

    await contributors(ctx)

@bot.command()
async def p(ctx):
    """
    Alias for !count progress
    """

    await progress(ctx)



# Run bot
load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
