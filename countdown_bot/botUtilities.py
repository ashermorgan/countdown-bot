# Import dependencies
import discord
import re


COLORS = {
    "error": 0xD52C42,
    "embed": 0x248AD1,
}



# Error classes
class CommandError(Exception):
    """Raised when a command encounters an anticipated error"""
    pass
class ContributorNotFound(Exception):
    """Raised when a matching countdown contributor cannot be found"""
    pass
class CountdownNotFound(Exception):
    """Raised when a matching countdown cannot be found"""
    pass



# The rules for awarding leaderboard points
POINT_RULES = {
    "r1": ("First Number", 0),
    "r2": ("1000s", 1000),
    "r3": ("1001s", 500),
    "r4": ("200s", 200),
    "r5": ("201s", 100),
    "r6": ("100s", 100),
    "r7": ("101s", 50),
    # "r8": ("Prime Numbers", 15),
    "r8": ("Odd Numbers", 12),
    "r9": ("Even Numbers", 10),
}



async def getUsername(bot, id):
    """
    Get a username from a user ID

    Parameters
    ----------
    bot : commands.Bot
        The bot
    id : int
        The user ID

    Returns
    -------
    str
        The username
    """

    user = await bot.fetch_user(id)
    return user.name



async def getContributor(bot, countdown, text):
    """
    Get the ID of the countdown contributor refered to by a string

    Parameters
    ----------
    bot : commands.Bot
        The bot
    countdown : Countdown
        The countdown
    text : str
        The string

    Returns
    -------
    int
        The ID of the contributor

    Raises
    ------
    ContributorNotFound
        If a matching contributor cannot be found
    """

    if (re.match("^<@\d+>$", text)):
        return int(text[2:-1])

    raise ContributorNotFound(text)



def isCountdown(cur, id):
    """
    Determine whether a channel is a countdown

    Parameters
    ----------
    cur : psycopg.cursor
        The database cursor
    id : int
        The countdown ID

    Returns
    -------
    bool
        A boolean indicating whether the channel is a countdown
    """

    cur.execute("CALL isCountdown(%s, null);",
        (id,))
    return cur.fetchone()["result"]



def getContextCountdown(cur, ctx):
    """
    Get the most relevant countdown to a certain context

    Parameters
    ----------
    cur : psycopg.cursor
        The database cursor
    ctx : discord.ext.commands.Context
        The context

    Returns
    -------
    countdownID
        The countdown ID
    """

    if (isinstance(ctx.channel, discord.channel.TextChannel)):
        # Channel inside a server
        cur.execute("CALL getServerContextCountdown(%s, %s, %s, null);",
            (ctx.channel.guild.id, ctx.channel.id, ctx.prefix))
        return cur.fetchone()["countdownid"]

    if (isinstance(ctx.channel, discord.channel.DMChannel)):
        # DM with a user
        cur.execute("CALL getUserContextCountdown(%s, null);",
            (ctx.author.id,))
        return cur.fetchone()["countdownid"]

    return None



def getPrefix(conn, ctx, default):
    """
    Get the bot prefix for a certain context

    Parameters
    ----------
    conn : psycopg.Connection
        The database connection
    ctx : discord.ext.commands.Context
        The context
    default : list
        The default prefixes
    """

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM getServerPrefixes(%s, %s);",
            (ctx.channel.guild.id if ctx.channel.guild else None, ctx.channel.id))
        prefixes = cur.fetchall()
        return [x["prefix"] for x in prefixes] if prefixes else default



async def addMessage(cur, message):
    """
    Parse a message and add it to a countdown

    Notes
    -----
    If the message is invalid or incorrect, a reaction will be added accordingly

    Parameters
    ----------
    cur : psycopg.cursor
        The database cursor
    message : discord.Message
        The Discord message object

    Returns
    -------
    bool
        Whether the message was valid and added to the countdown
    """

    # Parse message number
    match = re.search("^[0-9,]+", message.content)
    if not match: return False
    number = int(match[0].replace(",", ""))

    # Attempt to add result
    cur.execute("CALL addMessage(%s,%s,%s,%s,%s,null,null,null);", (
        message.id, message.channel.id, message.author.id, number,
        message.created_at
    ))
    result = cur.fetchone()

    # Process result
    if result["result"] == 'badNumber':
        await message.add_reaction("❌")
    if result["result"] == 'badUser':
        await message.add_reaction("⛔")
    if result["pin"]:
        await message.pin()
    if result["reactions"]:
        cur.execute("SELECT * FROM getReactions(%s, %s);",
            (message.channel.id, number))
        for reaction in cur.fetchall():
            await message.add_reaction(reaction["value"])

    return result["result"] == 'good'



async def loadCountdown(bot, countdown):
    """
    Loads countdown messages from a Discord countdown

    Parameters
    ----------
    bot : commands.Bot
        The bot to load messages with
    cur : psycopg.cursor
        The database cursor
    countdown : int
        The ID of the countdown to load messages for
    """

    with bot.db_connection.cursor() as cur:
        # Clear countdown
        cur.execute("CALL clearCountdown(%s);", (countdown,))

        # Get Discord messages
        messages = [message async for message in
                       bot.get_channel(countdown).history(limit=10100)]
        messages.reverse()

        # Add messages to countdown
        for message in messages:
            await addMessage(cur, message)

    # Commit changes
    bot.db_connection.commit()
