# Import dependencies
import copy
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import json
import math
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter
import os
import re
import tempfile



# Global variables
data = {}
loaded = 0  # percentage of countdowns fully loaded
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



# Static methods
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

async def getNickname(server, id):
    """
    Get a user's nickname in a server

    Parameters
    ----------
    server : int
        The server ID
    id : int
        The user ID

    Returns
    -------
    str
        The nickname
    """

    return (await (bot.get_guild(server)).fetch_member(id)).nick or await getUsername(id)

def saveData(data):
    """
    Save countdown data to the data.json file.

    Parameters
    ----------
    data : dict
        The countdown data
    """

    # Copy data
    obj = copy.deepcopy(data)

    # Remove countdown objects
    for countdown in obj["countdowns"]:
        del obj["countdowns"][countdown]["countdown"]

    # Save data
    with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
        return json.dump(obj, f)

def getCountdownChannel(ctx, resortToFirst=True):
    """
    Get the most relevant countdown channel to a certain context.

    Parameters
    ----------
    ctx
        The context
    resortToFirst : bool
        Whether to return the 1st countdown channel if no relevant countdown channels are found

    Returns
    -------
    dict
        The countdown channel
    str
        The channel ID
    """

    # Countdown channel
    global data
    if (str(ctx.channel.id) in data["countdowns"]):
        return data["countdowns"][str(ctx.channel.id)], str(ctx.channel.id)

    # Server with countdown channel
    if (isinstance(ctx.channel, discord.channel.TextChannel)):
        # Get first countdown in this server that use the current prefix
        serverChannels = [x for x in data["countdowns"] if data["countdowns"][x]["server"] == ctx.channel.guild.id and ctx.prefix in data["countdowns"][x]["prefixes"]]
        if (len(serverChannels) > 0):
            return data["countdowns"][serverChannels[0]], serverChannels[0]

    # No countdown channels
    if (len(data["countdowns"]) == 0):
        raise Exception("Countdown channel not found.")

    # Return default countdown channel
    if resortToFirst:
        return list(data["countdowns"].values())[0], list(data["countdowns"].keys())[0]
    else:
        raise Exception("Countdown channel not found.")

def getPrefix(bot, ctx):
    """
    Get the bot prefix for a certain context.

    Parameters
    ----------
    bot
        The bot
    ctx
        The context
    """

    # Countdown channel
    global data
    if (str(ctx.channel.id) in data["countdowns"] and len(data["countdowns"][str(ctx.channel.id)]["prefixes"]) > 0):
        return data["countdowns"][str(ctx.channel.id)]["prefixes"]

    # Server with countdown channels
    if (isinstance(ctx.channel, discord.channel.TextChannel)):
        serverChannels = [x for x in data["countdowns"] if data["countdowns"][x]["server"] == ctx.channel.guild.id]
        # Get list of prefixes
        prefixes = []
        for channel in serverChannels:
            prefixes += data["countdowns"][channel]["prefixes"]
        if (len(prefixes) > 0):
            return list(dict.fromkeys(prefixes))

    # Return default prefixes
    return data["prefixes"]



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

    def __init__(self, messages, reactions):
        self.messages = messages
        self.reactions = reactions

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
            if (str(message.number) in self.reactions):
                for reaction in self.reactions[str(message.number)]:
                    try:
                        await rawMessage.add_reaction(reaction)
                    except:
                        pass
            if (self.messages[0].number >= 500 and message.number % (self.messages[0].number // 50) == 0):
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

    def eta(self, period=timedelta(days=1), tz=timedelta(hours=0)):
        """
        Get countdown eta statistics.

        Parameters
        ----------
        period : timedelta
            The period size. The default is 1 day.
        tz : timedelta
            The timezone. The default is +0 (UTC)

        Returns
        -------
        list
            The countdown eta statistics.
        """

        # Make sure countdown has at least two messages
        if (len(self.messages) < 2):
            return [[], []]

        # Initialize period data
        periodEnd = self.messages[0].timestamp + tz + period
        lastMessage = 0

        # Initialize result and add first data point
        data = [[self.messages[0].timestamp + tz], [self.messages[0].timestamp + tz]]

        # Calculate timestamp for last data point
        if (self.messages[-1].number == 0):
            end = self.messages[-1].timestamp + tz
        else:
            end = datetime.utcnow() + tz

        # Add data points
        while (periodEnd < end):
            # Advance to last message in period
            while (lastMessage+1 < len(self.messages) and self.messages[lastMessage+1].timestamp + tz < periodEnd):
                lastMessage += 1

            # Calculate data
            rate = (self.messages[0].number - self.messages[lastMessage].number) / ((periodEnd - (self.messages[0].timestamp + tz)) / timedelta(days=1))
            eta = periodEnd + timedelta(days=self.messages[lastMessage].number/rate)
            data[0] += [periodEnd]
            data[1] += [eta]

            # Advance to next period
            periodEnd += period

        # Add last data point
        data[0] += [end]
        data[1] += [self.progress()["eta"]]

        # Return eta data
        return data

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
        if (len(self.messages) > 1 and self.messages[-1].number == 0):
            # The countdown has already finished
            rate = (total - current)/((self.messages[-1].timestamp - self.messages[0].timestamp) / timedelta(days=1))
            eta = self.messages[-1].timestamp
        elif (len(self.messages) > 1):
            # The countdown is still going
            rate = (total - current)/((datetime.utcnow() - self.messages[0].timestamp) / timedelta(days=1))
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



# Load countdown data
with open(os.path.join(os.path.dirname(__file__), "data.json"), "a+") as f:
    f.seek(0)
    data = json.load(f)



# Create Discord bot
bot = commands.Bot(command_prefix=getPrefix, case_insensitive=True)
bot.remove_command("help")



@bot.event
async def on_ready():
    # Print status
    print(f"Connected to Discord as {bot.user}")

    # Load messages
    global data
    global loaded
    for channel in data["countdowns"]:
        # Get messages
        rawMessages = await bot.get_channel(int(channel)).history(limit=10100).flatten()
        rawMessages.reverse()

        # Create countdown
        data["countdowns"][channel]["countdown"] = Countdown([], data["countdowns"][channel]["reactions"])

        # Load messages
        for rawMessage in rawMessages:
            await data["countdowns"][channel]["countdown"].parseMessage(rawMessage)

        # Print status
        print(f"Loaded messages from {bot.get_channel(int(channel))}")
        loaded += (1 / len(data["countdowns"]))
    loaded = 1



@bot.event
async def on_message(obj):
    if bot.user in obj.mentions:
        embed=discord.Embed(title="countdown-bot", description=f"Use `{(await bot.get_prefix(obj))[0]}help` to view help information", color=COLORS["embed"])
        await obj.channel.send(embed=embed)
    if (str(obj.channel.id) in data["countdowns"] and obj.author.name != "countdown-bot"):
        await data["countdowns"][str(obj.channel.id)]["countdown"].parseMessage(obj)
    try:
        await bot.process_commands(obj)
    except:
        pass



@bot.event
async def on_command_error(ctx, error):
    embed=discord.Embed(title="Error", description=str(error), color=COLORS["error"])
    if (isinstance(error, commands.CommandNotFound)):
        embed.description = f"Command not found: `{str(error)[9:-14]}`"
    else:
        embed.description = str(error)
    embed.description += f"\nUse `{(await bot.get_prefix(ctx))[0]}help` to view help information\n"
    await ctx.send(embed=embed)



@bot.command()
async def activate(ctx):
    """
    Turns a channel into a countdown
    """

    # Channel is already a coutndown
    if (str(ctx.channel.id) in data["countdowns"]):
        embed = discord.Embed(title="Error", description="This channel is already a countdown", color=COLORS["error"])
        await ctx.send(embed=embed)

    # Channel is a DM
    elif (not isinstance(ctx.channel, discord.channel.TextChannel)):
        embed = discord.Embed(title="Error", description="This command must be run inside a server", color=COLORS["error"])
        await ctx.send(embed=embed)

    # User isn't authorized
    elif (not ctx.message.author.guild_permissions.administrator):
        embed = discord.Embed(title="Error", description="You must be an administrator to turn a channel into a countdown", color=COLORS["error"])
        await ctx.send(embed=embed)

    # Channel is valid
    else:
        # Create countdown channel
        data["countdowns"][str(ctx.channel.id)] = {
            "server": ctx.channel.guild.id,
            "timezone": 0,
            "prefixes": data["prefixes"],
            "reactions": {},
            "countdown": Countdown([], {})
        }
        saveData(data)

        # Send initial responce
        print(f"Activated {bot.get_channel(ctx.channel.id)} as a countdown")
        embed = discord.Embed(title=":clock3: Loading Countdown", description="@here This channel is now a countdown\nPlease wait to start counting", color=COLORS["embed"])
        msg = await ctx.send(embed=embed)

        # Get messages
        rawMessages = await bot.get_channel(ctx.channel.id).history(limit=10100).flatten()
        rawMessages.reverse()

        # Create countdown
        data["countdowns"][str(ctx.channel.id)]["countdown"] = Countdown([], {})

        # Load messages
        for rawMessage in rawMessages:
            await data["countdowns"][str(ctx.channel.id)]["countdown"].parseMessage(rawMessage)

        # Send final responce
        print(f"Loaded messages from {bot.get_channel(ctx.channel.id)}")
        embed = discord.Embed(title=":white_check_mark: Countdown Activated", description="@here This channel is now a countdown\nYou may start counting!", color=COLORS["embed"])
        await msg.edit(embed=embed)



@bot.command()
async def config(ctx, key=None, *args):
    """
    Shows and modifies countdown settings
    """

    # Create embed
    embed = discord.Embed(title=":gear: Countdown Settings", color=COLORS["embed"])

    # Get countdown channel
    try:
        channel, id = getCountdownChannel(ctx, resortToFirst=False)
    except:
        embed.color = COLORS["error"]
        embed.description = "This command must be run in a countdown channel or a server with a countdown channel"
    else:
        # Get / set settings
        if (key is None):
            embed.description = f"**Countdown Channel:** <#{id}>\n"
            embed.description += f"**Command Prefixes:** `{'`, `'.join(channel['prefixes'])}`\n"
            if (channel["timezone"] < 0):
                embed.description += f"**Countdown Timezone:** UTC-{-1 * channel['timezone']}\n"
            else:
                embed.description += f"**Countdown Timezone:** UTC+{channel['timezone']}\n"
            if (len(channel["reactions"]) == 0):
                embed.description += f"**Reactions:** none\n"
            else:
                embed.description += f"**Reactions:**\n"
            for reaction in sorted(channel["reactions"].keys(), reverse=True):
                embed.description += f"**-** #{reaction}: {', '.join(channel['reactions'][reaction])}\n"
        elif (not ctx.message.author.guild_permissions.administrator):
            embed.color = COLORS["error"]
            embed.description = f"You must be an administrator to modify settings"
        elif (len(args) == 0):
            embed.color = COLORS["error"]
            embed.description = f"Please provide a value for the setting"
        elif (key in ["tz", "timezone"]):
            embed.description = f"Done"
            try:
                channel["timezone"] = int(args[0])
            except:
                try:
                    channel["timezone"] = float(args[0])
                except:
                    embed.color = COLORS["error"]
                    embed.description = f"Invalid timezone: {args[0]}"
        elif (key in ["prefix", "prefixes"]):
            channel["prefixes"] = args
            embed.description = f"Done"
        elif (key in ["react"]):
            try:
                number = int(args[0])
                if (number < 0):
                    embed.color = COLORS["error"]
                    embed.description = f"Number must be greater than zero"
                elif (len(args) == 1):
                    if (str(number) in channel["reactions"]):
                        del channel["reactions"][str(number)]
                    embed.description = f"Removed reactions for #{number}"
                else:
                    channel["reactions"][str(number)] = args[1:]
                    embed.description = f"Updated reactions for #{number}"
            except:
                embed.color = COLORS["error"]
                embed.description = f"Invalid number: {args[0]}"
        else:
            embed.color = COLORS["error"]
            embed.description = f"Setting not found: `{key}`\n"
            embed.description += f"Use `{(await bot.get_prefix(ctx))[0]}help config` to view the list of settings"

    # Save changes
    saveData(data)

    # Send embed
    await ctx.send(embed=embed)



@bot.command(aliases=["c"])
async def contributors(ctx, option=""):
    """
    Shows information about countdown contributors
    """

    # Get countdown channel
    channel, id = getCountdownChannel(ctx)

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Get stats
    stats = channel["countdown"].progress()
    contributors = channel["countdown"].contributors()

    # Create embed
    embed=discord.Embed(title=":busts_in_silhouette: Countdown Contributors", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(channel["countdown"].messages) == 0):
        embed.description = "The countdown is empty."
    elif (option.lower() in ["h", "history"]):
        # Create figure
        fig, ax = plt.subplots()
        ax.set_xlabel("Progress")
        ax.set_ylabel("Percentage of Contributions")
        ax.yaxis.set_major_formatter(PercentFormatter())

        # Get historical contributor data
        authors = {}
        for author in contributors:
            authors[author["author"]] = [{"progress":0, "percentage":0, "total":0}]
        for message in channel["countdown"].messages:
            for author in authors:
                if (author == message.author):
                    authors[author] += [{"progress":(stats["total"] - message.number), "percentage":(authors[author][-1]["total"] + 1)/(stats["total"] - message.number + 1) * 100, "total":authors[author][-1]["total"] + 1}]
                else:
                    authors[author] += [{"progress":(stats["total"] - message.number), "percentage":(authors[author][-1]["total"] + 0)/(stats["total"] - message.number + 1) * 100, "total":authors[author][-1]["total"] + 0}]

        # Plot data and add legend
        for author in list(authors.keys())[:min(len(authors), 15)]:
            # Top 15 contributors get included in the legend
            ax.plot([x["progress"] for x in authors[author]], [x["percentage"] for x in authors[author]], label=await getUsername(author))
        for author in list(authors.keys())[15:max(len(authors), 15)]:
            ax.plot([x["progress"] for x in authors[author]], [x["percentage"] for x in authors[author]])
        ax.legend(bbox_to_anchor=(1,1.025), loc="upper left")

        # Save graph
        fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
        file = discord.File(tmp.name, filename="image.png")

        # Add content to embed
        embed.description = f"**Countdown Channel:** <#{id}>"
        embed.set_image(url="attachment://image.png")
    elif (option == ""):
        # Create figure
        fig, ax = plt.subplots()

        # Add data to graph
        x = [x["author"] for x in contributors]
        y = [x["contributions"] for x in contributors]
        pieData = ax.pie(y, autopct="%1.1f%%", startangle=90)

        # Add legend
        ax.legend(pieData[0], [await getUsername(i) for i in x[:min(len(x), 15)]], bbox_to_anchor=(1,1.025), loc="upper left")

        # Save graph
        fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
        file = discord.File(tmp.name, filename="image.png")

        # Add content to embed
        embed.description = f"**Countdown Channel:** <#{id}>"
        ranks = ""
        users = ""
        contributions = ""
        for i in range(0, min(len(x), 20)):
            ranks += f"{i+1:,}\n"
            contributions += f"{y[i]:,} *({round(y[i] / len(channel['countdown'].messages) * 100, 1)}%)*\n"
            users += f"<@{x[i]}>\n"
        embed.add_field(name="Rank",value=ranks, inline=True)
        embed.add_field(name="User",value=users, inline=True)
        embed.add_field(name="Contributions",value=contributions, inline=True)
        embed.set_image(url="attachment://image.png")
    else:
        embed.color = COLORS["error"]
        embed.description = f"Unrecognized option: `{option}`\n"
        embed.description += f"Use `{(await bot.get_prefix(ctx))[0]}help contributors` to view help information"

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
async def deactivate(ctx):
    """
    Deactivates a countdown channel
    """

    # Channel isn't a countdown
    if (str(ctx.channel.id) not in data["countdowns"]):
        embed = discord.Embed(title="Error", description="This channel isn't a countdown", color=COLORS["error"])
        await ctx.send(embed=embed)

    # User isn't authorized
    elif (not ctx.message.author.guild_permissions.administrator):
        embed = discord.Embed(title="Error", description="You must be an administrator to deactivate a countdown channel", color=COLORS["error"])
        await ctx.send(embed=embed)

    # Channel is valid
    else:
        # Add channel data
        del data["countdowns"][str(ctx.channel.id)]
        saveData(data)

        # Send initial responce
        print(f"Deactivated {bot.get_channel(ctx.channel.id)} as a countdown")
        embed = discord.Embed(title=":octagonal_sign: Countdown Deactivated", description="@here This channel is no longer a countdown", color=COLORS["embed"])
        await ctx.send(embed=embed)



@bot.command(aliases=["e"])
async def eta(ctx, period="24.0"):
    """
    Shows information about the estimated completion date
    """

    # Get countdown channel
    channel, id = getCountdownChannel(ctx)

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":calendar: Countdown Estimated Completion Date", color=COLORS["embed"])

    # Parse period
    try:
        period = float(period)
    except:
        embed.color = COLORS["error"]
        embed.description = "The period must be a number"
    else:
        if (len(channel["countdown"].messages) < 2):
            embed.description = "The countdown must have at least two messages"
        elif (period < 0.01):
            embed.color = COLORS["error"]
            embed.description = "The period cannot be less than 0.01 hours"
        else:
            # Get stats
            eta = channel["countdown"].eta(timedelta(hours=period), tz=timedelta(hours=channel["timezone"]))

            # Create figure
            fig, ax = plt.subplots()
            ax.set_xlabel("Time")
            fig.autofmt_xdate()

            # Add ETA data to graph
            ax.plot(eta[0], eta[1], "C0", label="Estimated Completion Date")

            # Add reference line graph
            ax.plot([eta[0][0], eta[0][-1]], [eta[0][0], eta[0][-1]], "--C1", label="Current Date")

            # Add legend
            ax.legend()

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Calculate embed data
            maxEta = max(eta[1])
            maxDate = eta[0][eta[1].index(maxEta)]
            minEta = min(eta[1][1:])
            minDate = eta[0][eta[1].index(minEta)]
            end = eta[1][-1] + timedelta(hours=channel["timezone"])
            endDiff = eta[1][-1] - datetime.utcnow()

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{id}>\n\n"
            embed.description += f"**Maximum Estimate:** {maxEta.date()} (on {maxDate.date()})\n"
            embed.description += f"**Minimum Estimate:** {minEta.date()} (on {minDate.date()})\n"
            if endDiff < timedelta(seconds=0):
                embed.description += f"**Actual Completion Date:** {end.date()} ({(-1 * endDiff).days:,} days ago)\n"
            else:
                embed.description += f"**Current Estimate:** {end.date()} ({endDiff.days:,} days from now)\n"
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
        "utility-commands":
            "**-** `activate`: Turns a channel into a countdown\n" \
            "**-** `config`: Shows and modifies bot and countdown settings\n" \
            "**-** `deactivate`: Deactivates a countdown channel\n" \
            "**-** `help`, `h`: Shows help information\n" \
            "**-** `ping`: Pings the bot\n" \
            "**-** `reload`: Reloads the countdown cache\n",
        "analytics-commands":
            "**-** `contributors`, `c`: Shows information about countdown contributors\n" \
            "**-** `eta`, `e`: Shows information about the estimated completion date\n" \
            "**-** `leaderboard`, `l`: Shows the countdown leaderboard\n" \
            "**-** `progress`, `p`: Shows information about countdown progress\n" \
            "**-** `speed`, `s`: Shows information about countdown speed\n",
        "behavior":
            "**-** Reacts with :no_entry: when a user counts out of turn\n" \
            "**-** Reacts with :x: when a user counts incorrectly\n" \
            "**-** Pins numbers every 2% if the countdown started at 500 or higher\n",
        "activate":
            "**Name:** activate\n" \
            "**Description:** Turns a channel into a countdown\n" \
            f"**Usage:** `{prefixes[0]}activate`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n" \
            "**Notes:** Users must have admin permissions to turn a channel into a countdown\n",
        "config":
            "**Name:** config\n" \
            "**Description:** Shows and modifies countdown settings\n" \
            f"**Usage:** `{prefixes[0]}config [<key> <value>...]`\n" \
            "**Aliases:** none\n" \
            "**Arguments:**\n" \
            "**-** `<key>`: The name of the setting to modify (see below).\n" \
            "**-** `<value>`: The new value(s) for the setting. If no key-value pair is supplied, all settings will be shown.\n" \
            "**Available Settings:**\n" \
            "**-** `prefix`, `prefixes`: The prefix(es) for the bot.\n" \
            "**-** `tz`, `timezone`: The UTC offset, in hours.\n" \
            "**-** `react`: The reactions for a certain number. Ex: `react 0 :partying_face: :smile:`\n" \
            "**Notes:** Users must have admin permissions to modify settings\n",
        "contributors":
            "**Name:** contributors\n" \
            "**Description:** Shows information about countdown contributors\n" \
            f"**Usage:** `{prefixes[0]}contributors|c [history|h]`\n" \
            "**Aliases:** `c`\n" \
            "**Arguments:**\n" \
            "**-** `history`, `h`: Shows historical data about countdown contributors\n" \
            "**Notes:** The contributors embed will only show the top 20 contributors\n",
        "deactivate":
            "**Name:** deactivate\n" \
            "**Description:** Deactivates a countdown channel\n" \
            f"**Usage:** `{prefixes[0]}deactivate`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n" \
            "**Notes:** Users must have admin permissions to deactivate a countdown channel\n",
        "eta":
            "**Name:** eta\n" \
            "**Description:** Shows information about the estimated completion date\n" \
            f"**Usage:** `{prefixes[0]}eta|e [<period>]`\n" \
            "**Aliases:** `e`\n" \
            "**Arguments:**\n" \
            "**-** `<period>`: The size of the period in hours. The default is 24 hours.\n" \
            "**Notes:** none\n",
        "help":
            "**Name:** help\n" \
            "**Description:** Shows help information\n" \
            f"**Usage:** `{prefixes[0]}help|h [<command>]`\n" \
            "**Aliases:** `h`\n" \
            "**Arguments:**\n" \
            "**-** `<command>`: The command to view help information about. If no value is supplied, general help information will be shown.\n" \
            "**Notes:** none\n",
        "leaderboard":
            "**Name:** leaderboard\n" \
            "**Description:** Shows the countdown leaderboard\n" \
            f"**Usage:** `{prefixes[0]}leaderboard|l [<user>]`\n" \
            "**Aliases:** `l`\n" \
            "**Arguments:**\n" \
            "**-** `<user>`: The rank, username, or nickname of the user to viewleaderboard information about. If no value is supplied, the whole leaderboard will be shown.\n" \
            "**Notes:** The leaderboard embed will only show the top 20 contributors\n",
        "ping":
            "**Name:** ping\n" \
            "**Description:** Pings the bot\n" \
            f"**Usage:** `{prefixes[0]}ping`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n" \
            "**Notes:** none\n",
        "progress":
            "**Name:** progress\n" \
            "**Description:** Shows information about countdown progress\n" \
            f"**Usage:** `{prefixes[0]}progress|p`\n" \
            "**Aliases:** `p`\n" \
            "**Arguments:** none\n" \
            "**Notes:** none\n",
        "reload":
            "**Name:** reload\n" \
            "**Description:** Reloads the countdown cache\n" \
            f"**Usage:** `{prefixes[0]}reload`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n" \
            "**Notes:** none\n",
        "speed":
            "**Name:** speed\n" \
            "**Description:** Shows information about countdown speed\n" \
            f"**Usage:** `{prefixes[0]}speed|s [<period>]`\n" \
            "**Aliases:** `s`\n" \
            "**Arguments:**\n" \
            "**-** `<period>`: The size of the period in hours. The default is 24 hours.\n" \
            "**Notes:** none\n",
    }

    # Create embed
    embed=discord.Embed(title=":grey_question: countdown-bot Help", color=COLORS["embed"])
    if (command is None):
        embed.add_field(name="Command Prefixes :gear:", value=help_text["prefixes"], inline=False)
        embed.add_field(name="Utility Commands :wrench:", value=help_text["utility-commands"], inline=False)
        embed.add_field(name="Analytics Commands :bar_chart:", value=help_text["analytics-commands"], inline=False)
        embed.add_field(name="Behavior in Countdown Channels :robot:", value=help_text["behavior"], inline=False)
        embed.description = f"Use `{prefixes[0]}help command` to get more info on a command"
    elif (command.lower() in ["activate"]):
        embed.description = help_text["activate"]
    elif (command.lower() in ["config"]):
        embed.description = help_text["config"]
    elif (command.lower() in ["c", "contributors"]):
        embed.description = help_text["contributors"]
    elif (command.lower() in ["deactivate"]):
        embed.description = help_text["deactivate"]
    elif (command.lower() in ["e", "eta"]):
        embed.description = help_text["eta"]
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

    # Get countdown channel
    channel, id = getCountdownChannel(ctx)

    # Get leaderboard
    leaderboard = channel["countdown"].leaderboard()

    # Create embed
    embed=discord.Embed(title=":trophy: Countdown Leaderboard", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(channel["countdown"].messages) == 0):
        embed.description = "The countdown is empty."
    elif (user is None):
        # Add description
        embed.description = f"**Countdown Channel:** <#{id}>"

        # Add leaderboard
        ranks = ""
        points = ""
        users = ""
        for i in range(0, min(len(leaderboard), 20)):
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
        rank = None
        if (re.match("^\d+$", user) and int(user) > 0 and int(user) <= len(leaderboard)):
            # Get user from rank
            rank = int(user) - 1
        elif (re.match("^<@!\d+>$", user) and int(user[3:-1]) in [x["author"] for x in leaderboard]):
            # Get user from mention
            rank = [x["author"] for x in leaderboard].index(int(user[3:-1]))
        else:
            # Get user from username
            for contributor in leaderboard:
                username = await getUsername(contributor["author"])
                if (username.lower().startswith(user.lower())):
                    rank = leaderboard.index(contributor)

            if (rank == None):
                # Get user from nickname
                for contributor in leaderboard:
                    nickname = await getNickname(channel["server"], contributor["author"])
                    if (nickname.lower().startswith(user.lower())):
                        rank = leaderboard.index(contributor)

                if (rank == None):
                    # User not found
                    embed.color = COLORS["error"]
                    embed.description = f"User not found: `{user}`"
                    await ctx.send(embed=embed)
                    return

        # Add description
        embed.description = f"**Countdown Channel:** <#{id}>\n\n"
        embed.description += f"**User:** <@{leaderboard[rank]['author']}>\n"
        embed.description += f"**Rank:** #{rank + 1:,}\n"
        embed.description += f"**Total Points:** {leaderboard[rank]['points']:,}\n"
        embed.description += f"**Total Contributions:** {leaderboard[rank]['contributions']:,} *({round(leaderboard[rank]['contributions'] / len(channel['countdown'].messages) * 100, 1)}%)*\n"

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
    if (loaded == 1):
        embed.description += "**Status:** Ready :white_check_mark:"
    else:
        embed.description += f"**Status:** Loading ({round(loaded * 100)}%) :clock3:"
    await ctx.send(embed=embed)



@bot.command(aliases=["p"])
async def progress(ctx):
    """
    Shows information about countdown progress
    """

    # Get countdown channel
    channel, id = getCountdownChannel(ctx)

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":chart_with_downwards_trend: Countdown Progress", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(channel["countdown"].messages) == 0):
        embed.description = "The countdown is empty."
    else:
        # Get progress stats
        stats = channel["countdown"].progress()

        # Create figure
        fig, ax = plt.subplots()
        ax.set_xlabel("Time")
        ax.set_ylabel("Progress")
        fig.autofmt_xdate()

        # Add data to graph
        x = [stats["start"] + timedelta(hours=channel["timezone"])] + [x["time"] + timedelta(hours=channel["timezone"]) for x in stats["progress"]]
        y = [0] + [x["progress"] for x in stats["progress"]]
        ax.plot(x, y)

        # Save graph
        fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
        file = discord.File(tmp.name, filename="image.png")

        # Calculate embed data
        start = (stats["start"] + timedelta(hours=channel["timezone"])).date()
        startDiff = (datetime.utcnow() - stats["start"]).days
        end = (stats["eta"] + timedelta(hours=channel["timezone"])).date()
        endDiff = stats["eta"] - datetime.utcnow()

        # Add content to embed
        embed.description = f"**Countdown Channel:** <#{id}>\n\n"
        embed.description += f"**Progress:** {stats['total'] - stats['current']:,} / {stats['total']:,} ({round(stats['percentage'], 1)}%)\n"
        embed.description += f"**Average Progress per Day:** {round(stats['rate']):,}\n"
        embed.description += f"**Start Date:** {start} ({startDiff:,} days ago)\n"
        if endDiff < timedelta(seconds=0):
            embed.description += f"**End Date:** {end} ({(-1 * endDiff).days:,} days ago)\n"
        else:
            embed.description += f"**Estimated End Date:** {end} ({endDiff.days:,} days from now)\n"
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

    if (str(ctx.channel.id) in data["countdowns"]):
        # Send inital responce
        print(f"Reloading messages from {bot.get_channel(ctx.channel.id)}")
        embed = discord.Embed(title=":clock3: Reloading Countdown Cache", description="Please wait to continue counting.", color=COLORS["embed"])
        msg = await ctx.channel.send(embed=embed)

        # Get messages
        rawMessages = await bot.get_channel(ctx.channel.id).history(limit=10100).flatten()
        rawMessages.reverse()

        # Create countdown
        data["countdowns"][str(ctx.channel.id)]["countdown"] = Countdown([], data["countdowns"][str(ctx.channel.id)]["reactions"])

        # Load messages
        for rawMessage in rawMessages:
            await data["countdowns"][str(ctx.channel.id)]["countdown"].parseMessage(rawMessage)

        # Send final responce
        print(f"Reloaded messages from {bot.get_channel(ctx.channel.id)}")
        embed = discord.Embed(title=":white_check_mark: Countdown Cache Reloaded", description="Done! You may continue counting!", color=COLORS["embed"])
        await msg.edit(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="This command must be used in a countdown channel", color = COLORS["error"])
        await ctx.channel.send(embed=embed)



@bot.command(aliases=["s"])
async def speed(ctx, period="24.0"):
    """
    Shows information about countdown speed
    """

    # Get countdown channel
    channel, id = getCountdownChannel(ctx)

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":stopwatch: Countdown Speed", color=COLORS["embed"])

    # Parse period
    try:
        period = float(period)
    except:
        embed.color = COLORS["error"]
        embed.description = "The period must be a number"
    else:
        if (len(channel["countdown"].messages) == 0):
            embed.description = "The countdown is empty."
        elif (period < 0.01):
            embed.color = COLORS["error"]
            embed.description = "The period cannot be less than 0.01 hours"
        else:
            # Get stats
            stats = channel["countdown"].progress()
            period = timedelta(hours=period)
            speed = channel["countdown"].speed(period, tz=timedelta(hours=channel["timezone"]))

            # Create figure
            fig, ax = plt.subplots()
            ax.set_xlabel("Time")
            ax.set_ylabel("Progress per Period")
            fig.autofmt_xdate()

            # Add data to graph
            for i in range(0, len(speed[0])):
                ax.bar(speed[0][i], speed[1][i], width=period, align="edge", color="#1f77b4")

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{id}>\n\n"
            embed.description += f"**Period Size:** {period}\n"
            if (len(channel["countdown"].messages) > 1):
                rate = (stats['total'] - stats['current'])/((channel["countdown"].messages[-1].timestamp - channel["countdown"].messages[0].timestamp) / period)
            else:
                rate = 0
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
    bot.run(data["token"])
