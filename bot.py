# Import dependencies
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
import math
from matplotlib import pyplot as plt
import os
import re
import tempfile



# Global variables
channels = []
countdowns = {}
TIMEZONE = timedelta(hours=-8)  # America/Los_Angeles
POINT_RULES = {
    "1000s": 1000,
    "1001s": 500,
    "200s": 200,
    "201s": 100,
    "100s": 100,
    "101s": 50,
    "Prime Numbers": 15,
    "Odd Numbers": 12,
    "Even Numbers": 10,
    "First Number": 0,
}
COLORS = {
    "error": 0xD52C42,
    "embed": 0x248AD1,
}



# Error classes
class MessageNotAllowedError(Exception):
    """Raised when someone posts twice in a row."""
    pass

class MessageIncorrectError(Exception):
    """Raised when someone posts an incorrect number."""
    pass



async def getUsername(id):
    """
    Get a username from a user ID.

    Parameters
    ----------
    id : int
        The user ID.

    Returns
    -------
    str
        The username (ex: "user#0000").
    """

    user = await bot.fetch_user(id)
    return f"{user.name}#{user.discriminator}"



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
    author : int
        The message author ID.
    number : int
        The message content.
    """

    def __init__(self, obj):
        self.channel    = obj.channel.id
        self.id         = obj.id
        self.timestamp  = obj.created_at
        self.author     = obj.author.id
        self.number     = int(re.findall("^[0-9,]+", obj.content)[0].replace(",",""))

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

    def contributors(self):
        """
        Get countdown contributor statistics.

        Returns
        -------
        list
            A list of contributor statistics.
        """

        # Get contributors
        authors = list(set([x.author for x in self.messages]))

        # Get contributions
        contributors = []
        for author in authors:
            contributors += [{
                "author":author,
                "contributions":len([x for x in self.messages if x.author == author]),
            }]

        # Sort contributors by contributions
        contributors = sorted(contributors, key=lambda x: x["contributions"], reverse=True)

        # Return contributors
        return contributors

    def leaderboard(self):
        """
        Get countdown leaderboard.

        Returns
        -------
        list
            The leaderboard.
        """

        if (len(self.messages) == 0):
            return []

        # Get list of prime numbers
        curTest = 5
        search = 1
        primes = [2, 3]
        while curTest < self.messages[0].number:
            if curTest%(primes[search]) == 0:
                curTest = curTest + 2
                search = 1
            else:
                if primes[search] > math.sqrt(curTest):
                    primes.append(curTest)
                    curTest = curTest + 2
                    search = 1
                else:
                    search = search + 1

        # Calculate contributor points
        points = {}
        for message in self.messages:
            if (message.author not in points):
                points[message.author] = {
                    "author": message.author,
                    "breakdown": {
                        "1000s": 0,
                        "1001s": 0,
                        "200s": 0,
                        "201s": 0,
                        "100s": 0,
                        "101s": 0,
                        "Prime Numbers": 0,
                        "Odd Numbers": 0,
                        "Even Numbers": 0,
                        "First Number": 0,
                    },
                }
            if (message.number == self.messages[0].number): points[message.author]["breakdown"]["First Number"] += 1
            elif (message.number % 1000 == 0):              points[message.author]["breakdown"]["1000s"] += 1
            elif (message.number % 1000 == 1):              points[message.author]["breakdown"]["1001s"] += 1
            elif (message.number % 200 == 0):               points[message.author]["breakdown"]["200s"] += 1
            elif (message.number % 200 == 1):               points[message.author]["breakdown"]["201s"] += 1
            elif (message.number % 100 == 0):               points[message.author]["breakdown"]["100s"] += 1
            elif (message.number % 100 == 1):               points[message.author]["breakdown"]["101s"] += 1
            elif (message.number in primes):                points[message.author]["breakdown"]["Prime Numbers"] += 1
            elif (message.number % 2 == 1):                 points[message.author]["breakdown"]["Odd Numbers"] += 1
            else:                                           points[message.author]["breakdown"]["Even Numbers"] += 1

        # Create ranked leaderboard
        leaderboard = []
        for contributor in points.values():
            contributor["contributions"] = sum(contributor["breakdown"].values())
            contributor["points"] = sum([contributor["breakdown"][x] * POINT_RULES[x] for x in contributor["breakdown"]])
            leaderboard += [contributor]
        leaderboard = sorted(leaderboard, key=lambda x: x["points"], reverse=True)
        return leaderboard

    def progress(self):
        """
        Get countdown progress statistics.

        Returns
        -------
        dict
            A dictionary containing countdown progress statistics.
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
        progress = [{"time":x.timestamp, "progress":x.number} for x in self.messages]

        # Return stats
        return {
            "total": total,
            "current": current,
            "percentage": percentage,
            "progress": progress,
            "start": start,
            "rate": rate,
            "eta": eta,
        }

    def speed(self, period=timedelta(days=1), tz=timedelta(hours=0)):
        """
        Get countdown speed statistics.

        Parameters
        ----------
        periodLength : timedelta
            The period size. The default is 1 day.
        tz : timedelta
            The timezone. The default is +0 (UTC)

        Returns
        -------
        list
            The countdown speed statistics.
        """

        # Calculate speed statistics
        data = [[], []]
        periodStart = datetime(2018, 1, 1) # Starts on Monday, Jan 1st
        for message in self.messages:
            # If data point isn't in the current period
            while (message.timestamp + tz - period >= periodStart):
                periodStart += period

            # Add new period if needed
            if (len(data[0]) == 0 or data[0][-1] != periodStart):
                data[0] += [periodStart]
                data[1] += [0]

            # Otherwise add the latest diff to the current period
            data[1][-1] += 1

        # Return speed statistics
        return data



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
bot = commands.Bot(command_prefix = ["c."], case_insensitive=True)
bot.remove_command("help")



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
        countdowns[channel] = Countdown([])

        # Load messages
        for rawMessage in rawMessages:
            await countdowns[channel].parseMessage(rawMessage)

        # Print status
        print(f"Loaded messages from {bot.get_channel(channel)}")



@bot.event
async def on_message(obj):
    if (obj.channel.id in channels and obj.author.name != "countdown-bot"):
        await countdowns[obj.channel.id].parseMessage(obj)
    try:
        await bot.process_commands(obj)
    except:
        pass



@bot.event
async def on_command_error(ctx, error):
    embed=discord.Embed(title="Error", description=str(error), color=COLORS["error"])
    embed.description = str(error)
    embed.description += f"\nUse `{(await bot.get_prefix(ctx))[0]}help` to view help information\n"
    await ctx.send(embed=embed)



@bot.command(aliases=["c"])
async def contributors(ctx):
    """
    Shows information about countdown contributors
    """

    # Get messages
    if (ctx.channel.id in channels):
        countdown = countdowns[ctx.channel.id]
    else:
        countdown = countdowns[channels[0]]

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":busts_in_silhouette: Countdown Contributors", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(countdown.messages) == 0):
        embed.description = "The countdown is empty."
    else:
        # Get stats
        contributors = countdown.contributors()

        # Create plot
        plt.close()
        plt.title("Countdown Contributors")

        # Add data to graph
        x = [await getUsername(x["author"]) for x in contributors]
        y = [x["contributions"] for x in contributors]
        plt.pie(y, labels=x, autopct="%1.1f%%", startangle = 90)

        # Save graph
        plt.savefig(tmp.name)
        file = discord.File(tmp.name, filename="image.png")

        # Add content to embed
        ranks = ""
        users = ""
        contributions = ""
        for i in range(0, len(x)):
            ranks += f"{i+1:,}\n"
            contributions += f"{y[i]:,}\n"
            users += f"{x[i]}\n"
        embed.add_field(name="Rank",value=ranks, inline=True)
        embed.add_field(name="User",value=users, inline=True)
        embed.add_field(name="Contributions",value=contributions, inline=True)
        embed.set_image(url="attachment://image.png")

    # Send embed
    try:
        await ctx.send(file=file, embed=embed)
    except:
        await ctx.send(embed=embed)

    # Remove temp file
    try:
        os.remove(tmp.name)
    except:
        print(f"Unable to delete temp file: {tmp.name}.")



@bot.command(aliases=["h", ""])
async def help(ctx, command=None):
    """
    Shows help information
    """

    # Initialize help information
    prefixes = await bot.get_prefix(ctx)
    help_text = {
        "prefixes":
            f"`{'`, `'.join(prefixes)}`",
        "commands":
            "**-** `contributors, c`: Shows information about countdown contributors\n" \
            "**-** `help, h`: Shows help information\n" \
            "**-** `leaderboard, l`: Shows the countdown leaderboard\n" \
            "**-** `ping`: Pings the bot\n" \
            "**-** `progress, p`: Shows information about countdown progress\n" \
            "**-** `reload`: Reloads the countdown cache\n" \
            "**-** `speed, s`: Shows information about countdown speed\n" \
            f"\nUse `{prefixes[0]}help command` to get more info on a command\n",
        "behavior":
            "**-** Reacts with :no_entry: when a user counts out of turn\n" \
            "**-** Reacts with :x: when a user counts incorrectly\n" \
            "**-** Pins numbers divisible by 200\n" \
            "**-** Reacts with :partying_face: to the number 0\n",
        "contributors":
            "**Name:** contributors\n" \
            "**Description:** Shows information about countdown contributors\n" \
            f"**Usage:** `{prefixes[0]}contributors|c`\n" \
            "**Aliases:** `c`\n" \
            "**Arguments:** none\n",
        "help":
            "**Name:** help\n" \
            "**Description:** Shows help information\n" \
            f"**Usage:** `{prefixes[0]}help|h [command]`\n" \
            "**Aliases:** `h`\n" \
            "**Arguments:**\n" \
            "**-** `command`: The command to view help information about. If no value is supplied, general help information will be shown.\n",
        "leaderboard":
            "**Name:** leaderboard\n" \
            "**Description:** Shows the countdown leaderboard\n" \
            f"**Usage:** `{prefixes[0]}leaderboard|l [user]`\n" \
            "**Aliases:** `l`\n" \
            "**Arguments:**\n" \
            "**-** `user`: The user to view leaderboard information about. If no value is supplied, the whole leaderboard will be shown.\n",
        "ping":
            "**Name:** ping\n" \
            "**Description:** Pings the bot\n" \
            f"**Usage:** `{prefixes[0]}ping`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n",
        "progress":
            "**Name:** progress\n" \
            "**Description:** Shows information about countdown progress\n" \
            f"**Usage:** `{prefixes[0]}progress|p`\n" \
            "**Aliases:** `p`\n" \
            "**Arguments:** none\n",
        "reload":
            "**Name:** reload\n" \
            "**Description:** Reloads the countdown cache\n" \
            f"**Usage:** `{prefixes[0]}reload`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n",
        "speed":
            "**Name:** speed\n" \
            "**Description:** Shows information about countdown speed\n" \
            f"**Usage:** `{prefixes[0]}speed|s [period]`\n" \
            "**Aliases:** `s`\n" \
            "**Arguments:**\n" \
            "**-** `period`: The size of the period in hours. The default is 24 hours.\n",
    }

    # Create embed
    embed=discord.Embed(title=":grey_question: countdown-bot Help", color=COLORS["embed"])
    if (command is None):
        embed.add_field(name="Command Prefixes :gear:", value=help_text["prefixes"], inline=False)
        embed.add_field(name="Commands :wrench:", value=help_text["commands"], inline=False)
        embed.add_field(name="Behavior in Countdown Channels :robot:", value=help_text["behavior"], inline=False)
    elif (command.lower() in ["c", "contributors"]):
        embed.description = help_text["contributors"]
    elif (command.lower() in ["h", "help"]):
        embed.description = help_text["help"]
    elif (command.lower() in ["l", "leaderboard"]):
        embed.description = help_text["leaderboard"]
    elif (command.lower() in ["ping"]):
        embed.description = help_text["ping"]
    elif (command.lower() in ["p", "progress"]):
        embed.description = help_text["progress"]
    elif (command.lower() in ["reload"]):
        embed.description = help_text["reload"]
    elif (command.lower() in ["s", "speed"]):
        embed.description = help_text["speed"]
    else:
        embed.color = COLORS["error"]
        embed.description = f"Command not found: `{command}`\n"
        embed.description += f"Use `{prefixes[0]}help` to view the list of commands"

    # Send embed
    await ctx.send(embed=embed)



@bot.command(aliases=["l"])
async def leaderboard(ctx, user=None):
    """
    Shows the countdown leaderboard
    """

    # Get countdown
    if (ctx.channel.id in channels):
        countdown = countdowns[ctx.channel.id]
    else:
        countdown = countdowns[channels[0]]

    # Get leaderboard
    leaderboard = countdown.leaderboard()

    # Create embed
    embed=discord.Embed(title=":trophy: Countdown Leaderboard", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(countdown.messages) == 0):
        embed.description = "The countdown is empty."
    elif (user is None):
        # Add leaderboard
        ranks = ""
        points = ""
        users = ""
        for i in range(0, len(leaderboard)):
            ranks += f"{i+1:,}\n"
            points += f"{leaderboard[i]['points']:,}\n"
            users += f"<@{leaderboard[i]['author']}>\n"
        embed.add_field(name="Rank",value=ranks, inline=True)
        embed.add_field(name="Points",value=points, inline=True)
        embed.add_field(name="User",value=users, inline=True)

        # Add leaderboard rules
        rules = ""
        values = ""
        for rule in POINT_RULES:
            rules += f"{rule}\n"
            values += f"{POINT_RULES[rule]} points\n"
        embed.add_field(name="Rules", value="Only 1 rule is applied towards each number", inline=False)
        embed.add_field(name="Numbers", value=rules, inline=True)
        embed.add_field(name="Points", value=values, inline=True)
    else:
        # Get usernames from IDs
        for contributor in leaderboard:
            contributor["name"] = await getUsername(contributor["author"])

        # Get user rank
        temp = [x["name"].lower().startswith(user.lower()) for x in leaderboard]
        if (True not in temp):
            embed.color = COLORS["error"]
            embed.description = f"User not found: `{user}`"
            await ctx.send(embed=embed)
            return
        rank = temp.index(True)

        # Add description
        embed.description = f"**User:** <@{leaderboard[rank]['author']}>\n"
        embed.description += f"**Rank:** #{rank + 1:,}\n"
        embed.description += f"**Total Points:** {leaderboard[rank]['points']:,}\n"
        embed.description += f"**Total Contributions:** {leaderboard[rank]['contributions']:,}\n"

        # Add points breakdown
        rules = ""
        points = ""
        percentage = ""
        for category in leaderboard[rank]["breakdown"]:
            rules += f"{category}\n"
            points += f"{leaderboard[rank]['breakdown'][category] * POINT_RULES[category]:,} *({leaderboard[rank]['breakdown'][category]:,})*\n"
            if (leaderboard[rank]['points'] > 0):
                percentage += f"{round(leaderboard[rank]['breakdown'][category] * POINT_RULES[category] / leaderboard[rank]['points'] * 100, 1)}%\n"
            else:
                percentage += "0%\n"
        embed.add_field(name="Category", value=rules, inline=True)
        embed.add_field(name="Points", value=points, inline=True)
        embed.add_field(name="Percentage", value=percentage, inline=True)

    # Send embed
    await ctx.send(embed=embed)



@bot.command()
async def ping(ctx):
    """
    Pings the bot
    """

    embed=discord.Embed(title=":ping_pong: Pong!", color=COLORS["embed"])
    embed.description = f"**Latency:** {round(bot.latency * 1000)} ms\n"
    embed.description += f"**Countdowns:** {len(countdowns)}"
    await ctx.send(embed=embed)



@bot.command(aliases=["p"])
async def progress(ctx):
    """
    Shows information about countdown progress
    """

    # Get messages
    if (ctx.channel.id in channels):
        countdown = countdowns[ctx.channel.id]
    else:
        countdown = countdowns[channels[0]]
    
    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":chart_with_downwards_trend: Countdown Progress", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(countdown.messages) == 0):
        embed.description = "The countdown is empty."
    else:
        # Get progress stats
        stats = countdown.progress()

        # Create plot
        plt.close()
        plt.title("Countdown Progress")
        plt.xlabel("Time")
        plt.ylabel("Progress")
        plt.gcf().autofmt_xdate()

        # Add data to graph
        x = [stats["start"] + TIMEZONE] + [x["time"] + TIMEZONE for x in stats["progress"]]
        y = [0] + [x["progress"] for x in stats["progress"]]
        plt.plot(x, y)

        # Save graph
        plt.savefig(tmp.name)
        file = discord.File(tmp.name, filename="image.png")

        # Calculate embed data
        start = (stats["start"] + TIMEZONE).date()
        startDiff = (datetime.utcnow() - stats["start"]).days
        end = (stats["eta"] + TIMEZONE).date()
        endDiff = (stats["eta"] - datetime.utcnow()).days
        if endDiff < 0: endDiff = 0

        # Add content to embed
        embed.description = f"**Progress:** {stats['total'] - stats['current']:,} / {stats['total']:,} ({round(stats['percentage'], 1)}%)\n"
        embed.description += f"**Average Progress per Day:** {round(stats['rate']):,}\n"
        embed.description += f"**Start Date:** {start} ({startDiff:,} days ago)\n"
        embed.description += f"**Estimated End Date:** {end} ({endDiff:,} days from now)\n"
        embed.set_image(url="attachment://image.png")

    # Send embed
    try:
        await ctx.send(file=file, embed=embed)
    except:
        await ctx.send(embed=embed)

    # Remove temp file
    try:
        os.remove(tmp.name)
    except:
        print(f"Unable to delete temp file: {tmp.name}.")



@bot.command()
async def reload(ctx):
    """
    Reloads the countdown cache
    """

    if (ctx.channel.id in channels):
        # Send inital responce
        print(f"Reloading messages from {bot.get_channel(ctx.channel.id)}")
        embed = discord.Embed(title=":clock3: Reloading Countdown Cache", description="Please wait to continue counting.", color=COLORS["embed"])
        msg = await ctx.channel.send(embed=embed)

        # Get messages
        rawMessages = await bot.get_channel(ctx.channel.id).history(limit=10100).flatten()
        rawMessages.reverse()

        # Create countdown
        countdowns[ctx.channel.id] = Countdown([])

        # Load messages
        for rawMessage in rawMessages:
            await countdowns[ctx.channel.id].parseMessage(rawMessage)

        # Send final responce
        print(f"Reloaded messages from {bot.get_channel(ctx.channel.id)}")
        embed = discord.Embed(title=":white_check_mark: Countdown Cache Reloaded", description="Done! You may continue counting!", color=COLORS["embed"])
        await msg.edit(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="This command must be used in a countdown channel", color = COLORS["error"])
        await ctx.channel.send(embed=embed)



@bot.command(aliases=["s"])
async def speed(ctx, period=24.0):
    """
    Shows information about countdown speed
    """

    # Get messages
    if (ctx.channel.id in channels):
        countdown = countdowns[ctx.channel.id]
    else:
        countdown = countdowns[channels[0]]

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":stopwatch: Countdown Speed", color=COLORS["embed"])

    if (len(countdown.messages) == 0):
        embed.description = "The countdown is empty."
    elif (period <= 0):
        embed.color = COLORS["error"]
        embed.description = "Hours must be greater than 0."
    else:
        # Get stats
        stats = countdown.progress()
        period = timedelta(hours=period)
        speed = countdown.speed(period, tz=TIMEZONE)

        # Create plot
        plt.close()
        plt.title("Countdown Speed")
        plt.xlabel("Time")
        plt.ylabel("Progress per Period")
        plt.gcf().autofmt_xdate()

        # Add data to graph
        for i in range(0, len(speed[0])):
            plt.bar(speed[0][i], speed[1][i], width=period, align="edge", color="#1f77b4")

        # Save graph
        plt.savefig(tmp.name)
        file = discord.File(tmp.name, filename="image.png")

        # Add content to embed
        embed.description = f"**Period Size:** {period}\n"
        rate = (stats['total'] - stats['current'])/((countdown.messages[-1].timestamp - countdown.messages[0].timestamp) / period)
        embed.description += f"**Average Progress per Period:** {round(rate):,}\n"
        embed.description += f"**Record Progress per Period:** {max(speed[1]):,}\n"
        embed.description += f"**Last Period Start:** {speed[0][-1]}\n"
        embed.description += f"**Progress during Last Period:** {speed[1][-1]:,}\n"
        embed.set_image(url="attachment://image.png")

    # Send embed
    try:
        await ctx.send(file=file, embed=embed)
    except:
        await ctx.send(embed=embed)

    # Remove temp file
    try:
        os.remove(tmp.name)
    except:
        print(f"Unable to delete temp file: {tmp.name}.")



# Run bot
if (__name__ == "__main__"):
    load_dotenv()
    bot.run(os.getenv("DISCORD_TOKEN"))
