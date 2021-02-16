# Import dependencies
import copy
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import math
from matplotlib import pyplot as plt
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
        serverChannels = [x for x in data["countdowns"] if data["countdowns"][x]["server"] == ctx.channel.guild.id]
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

    try:
        channel, id = getCountdownChannel(ctx, resortToFirst=False)
        return channel["prefixes"]
    except:
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
        data["countdowns"][channel]["countdown"] = Countdown([])

        # Load messages
        for rawMessage in rawMessages:
            await data["countdowns"][channel]["countdown"].parseMessage(rawMessage)

        # Print status
        print(f"Loaded messages from {bot.get_channel(int(channel))}")
        loaded += (1 / len(data["countdowns"]))
    loaded = 1



@bot.event
async def on_message(obj):
    if (str(obj.channel.id) in data["countdowns"] and obj.author.name != "countdown-bot"):
        await data["countdowns"][str(obj.channel.id)]["countdown"].parseMessage(obj)
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



@bot.command()
async def activate(ctx):
    """
    Turns a channel into a countdown
    """

    # Channel is already a coutndown
    if (str(ctx.channel.id) in data["countdowns"]):
        embed = discord.Embed(title="Error", description="This channel is already a countdown.", color=COLORS["error"])
        await ctx.send(embed=embed)

    # Channel is a DM
    elif (not isinstance(ctx.channel, discord.channel.TextChannel)):
        embed = discord.Embed(title="Error", description="This command must be run inside a server.", color=COLORS["error"])
        await ctx.send(embed=embed)

    # Channel is valid
    else:
        # Create countdown channel
        data["countdowns"][str(ctx.channel.id)] = {
            "server": ctx.channel.guild.id,
            "timezone": 0,
            "prefixes": data["prefixes"],
            "countdown": Countdown([])
        }
        saveData(data)

        # Send initial responce
        print(f"Activated {bot.get_channel(ctx.channel.id)} as a countdown")
        embed = discord.Embed(title=":clock3: Loading Countdown", description="@here This channel is now a countdown.\nPlease wait to start counting.", color=COLORS["embed"])
        msg = await ctx.send(embed=embed)

        # Get messages
        rawMessages = await bot.get_channel(ctx.channel.id).history(limit=10100).flatten()
        rawMessages.reverse()

        # Create countdown
        data["countdowns"][str(ctx.channel.id)]["countdown"] = Countdown([])

        # Load messages
        for rawMessage in rawMessages:
            await data["countdowns"][str(ctx.channel.id)]["countdown"].parseMessage(rawMessage)

        # Send final responce
        print(f"Loaded messages from {bot.get_channel(ctx.channel.id)}")
        embed = discord.Embed(title=":white_check_mark: Countdown Activated", description="@here This channel is now a countdown.\nYou may start counting!", color=COLORS["embed"])
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
        elif (not ctx.message.author.guild_permissions.administrator):
            embed.color = COLORS["error"]
            embed.description = f"You must be an administrator to modify settings"
        elif (len(args) == 0):
            embed.color = COLORS["error"]
            embed.description = f"Please provide a value for the setting"
        elif (key in ["tz", "timezone"]):
            try:
                channel["timezone"] = int(args[0])
            except:
                channel["timezone"] = float(args[0])
            embed.description = f"Done"
        elif (key in ["prefix", "prefixes"]):
            channel["prefixes"] = args
            embed.description = f"Done"
        else:
            embed.color = COLORS["error"]
            embed.description = f"Setting not found: `{key}`\n"
            embed.description += f"Use `{(await bot.get_prefix(ctx))[0]}help config` to view the list of settings"

    # Save changes
    saveData(data)

    # Send embed
    await ctx.send(embed=embed)



@bot.command(aliases=["c"])
async def contributors(ctx):
    """
    Shows information about countdown contributors
    """

    # Get countdown channel
    channel, id = getCountdownChannel(ctx)

    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()

    # Create embed
    embed=discord.Embed(title=":busts_in_silhouette: Countdown Contributors", color=COLORS["embed"])

    # Make sure the countdown has started
    if (len(channel["countdown"].messages) == 0):
        embed.description = "The countdown is empty."
    else:
        # Get stats
        contributors = channel["countdown"].contributors()

        # Create plot
        plt.close()
        plt.title("Countdown Contributors")

        # Add data to graph
        x = [x["author"] for x in contributors]
        y = [x["contributions"] for x in contributors]
        plt.pie(y, labels=[await getUsername(i) for i in x], autopct="%1.1f%%", startangle = 90)

        # Save graph
        plt.savefig(tmp.name)
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
        embed = discord.Embed(title="Error", description="This channel isn't a countdown.", color=COLORS["error"])
        await ctx.send(embed=embed)

    # Channel is valid
    else:
        # Add channel data
        del data["countdowns"][str(ctx.channel.id)]
        saveData(data)

        # Send initial responce
        print(f"Deactivated {bot.get_channel(ctx.channel.id)} as a countdown")
        embed = discord.Embed(title=":octagonal_sign: Countdown Deactivated", description="@here This channel is no longer a countdown.", color=COLORS["embed"])
        await ctx.send(embed=embed)



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
            "**-** `leaderboard`, `l`: Shows the countdown leaderboard\n" \
            "**-** `progress`, `p`: Shows information about countdown progress\n" \
            "**-** `speed`, `s`: Shows information about countdown speed\n",
        "behavior":
            "**-** Reacts with :no_entry: when a user counts out of turn\n" \
            "**-** Reacts with :x: when a user counts incorrectly\n" \
            "**-** Pins numbers every 2% if the countdown started at 500 or higher\n" \
            "**-** Reacts with :partying_face: to the number 0\n",
        "activate":
            "**Name:** activate\n" \
            "**Description:** Turns a channel into a countdown\n" \
            f"**Usage:** `{prefixes[0]}activate`\n" \
            "**Aliases:** none\n" \
            "**Arguments:** none\n",
        "config":
            "**Name:** config\n" \
            "**Description:** Shows and modifies countdown settings\n" \
            f"**Usage:** `{prefixes[0]}config [key value...]`\n" \
            "**Aliases:** none\n" \
            "**Arguments:**\n" \
            "**-** `key`: The name of the setting to modify (see below).\n" \
            "**-** `value`: The new value(s) for the setting. If no key-value pair is supplied, all settings will be shown.\n" \
            "**Available Settings:**\n" \
            "**-** `prefix`, `prefixes`: The prefix(es) for the bot. If there are multiple sets of prefixes in a server, only the first set will be enabled throughout the server.\n" \
            "**-** `tz`, `timezone`: The UTC offset, in hours.\n",
        "contributors":
            "**Name:** contributors\n" \
            "**Description:** Shows information about countdown contributors\n" \
            f"**Usage:** `{prefixes[0]}contributors|c`\n" \
            "**Aliases:** `c`\n" \
            "**Arguments:** none\n",
        "deactivate":
            "**Name:** deactivate\n" \
            "**Description:** Deactivates a countdown channel\n" \
            f"**Usage:** `{prefixes[0]}deactivate`\n" \
            "**Aliases:** none\n" \
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
            "**-** `user`: The username of the user to view leaderboard information about. Nicknames are not currently supported. If no value is supplied, the leaderboard will be shown.\n",
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

        # Create plot
        plt.close()
        plt.title("Countdown Progress")
        plt.xlabel("Time")
        plt.ylabel("Progress")
        plt.gcf().autofmt_xdate()

        # Add data to graph
        x = [stats["start"] + timedelta(hours=channel["timezone"])] + [x["time"] + timedelta(hours=channel["timezone"]) for x in stats["progress"]]
        y = [0] + [x["progress"] for x in stats["progress"]]
        plt.plot(x, y)

        # Save graph
        plt.savefig(tmp.name)
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
        data["countdowns"][str(ctx.channel.id)]["countdown"] = Countdown([])

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
async def speed(ctx, period=24.0):
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

    if (len(channel["countdown"].messages) == 0):
        embed.description = "The countdown is empty."
    elif (period <= 0):
        embed.color = COLORS["error"]
        embed.description = "Hours must be greater than 0."
    else:
        # Get stats
        stats = channel["countdown"].progress()
        period = timedelta(hours=period)
        speed = channel["countdown"].speed(period, tz=timedelta(hours=channel["timezone"]))

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
    load_dotenv()
    bot.run(data["token"])
