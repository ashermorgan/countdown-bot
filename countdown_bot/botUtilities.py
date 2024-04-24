# Import dependencies
import discord
import re

# Import modules
from .models import Countdown, Message



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
        The username (ex: "user#0000")
    """

    user = await bot.fetch_user(id)
    return f"{user.name}#{user.discriminator}"



async def getNickname(bot, server, id):
    """
    Get a user's nickname in a server

    Parameters
    ----------
    bot : commands.Bot
        The bot
    server : int
        The server ID
    id : int
        The user ID

    Returns
    -------
    str
        The nickname
    """

    return (await (bot.get_guild(server)).fetch_member(id)).nick or await getUsername(bot, id)



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

    # Get countdown contributors
    contributors = [x["author"] for x in countdown.contributors()]

    # Get user from mention
    if (re.match("^<@!\d+>$", text) and int(text[3:-1]) in contributors):
        return int(text[3:-1])
    elif (re.match("^<@!\d+>$", text)):
        raise ContributorNotFound(text)

    # Get user from username
    for contributor in contributors:
        try:
            username = await getUsername(bot, contributor)
        except:
            continue
        if (username.lower().startswith(text.lower())):
            return contributor

    # Get user from nickname
    for contributor in contributors:
        try:
            nickname = await getNickname(bot, countdown.server_id, contributor)
        except:
            continue
        if (nickname.lower().startswith(text.lower())):
            return contributor

    raise ContributorNotFound(text)



def getCountdown(session, id):
    """
    Get a countdown object

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        The database session to use
    id : int
        The countdown id

    Returns
    -------
    Countdown
        The Countdown
    """

    return session.query(Countdown).filter(Countdown.id == id).first()



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
        (ctx.channel.id,))
    return cur.fetchone()[0]



def getContextCountdown(session, ctx):
    """
    Get the most relevant countdown to a certain context

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        The database session to use
    ctx : discord.ext.commands.Context
        The context

    Returns
    -------
    Countdown
        The countdown

    Raises
    ------
    CountdownNotFound
        If a matching countdown cannot be found
    """

    if (isinstance(ctx.channel, discord.channel.TextChannel)):
        # Countdown channel
        countdown = getCountdown(session, ctx.channel.id)
        if (countdown): return countdown

        # Server with countdown channel: get first countdown in this server that use the current prefix
        countdown = session.query(Countdown).filter(Countdown.server_id == ctx.channel.guild.id and ctx.prefix in [x.value for x in Countdown.prefixes]).first()
        if (countdown): return countdown

    if (isinstance(ctx.channel, discord.channel.DMChannel)):
        # DM with user who has contributed to a countdown: get the first countdown they ever contributed to
        firstMessage = session.query(Message).filter(Message.author_id == ctx.author.id).order_by(Message.timestamp).first()
        if (firstMessage): return firstMessage.countdown

    raise CountdownNotFound()

def getContextCountdown2(cur, ctx):
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
        return cur.fetchone()[0]

    if (isinstance(ctx.channel, discord.channel.DMChannel)):
        # DM with a user
        cur.execute("CALL getUserContextCountdown(%s, null);",
            (ctx.author.id,))
        return cur.fetchone()[0]

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
        cur.execute("SELECT * FROM getPrefixes(%s, %s);",
            (ctx.channel.guild.id, ctx.channel.id))
        prefixes = cur.fetchall()
        return [x[0] for x in prefixes] if prefixes else default



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
    if result[0] == 'badNumber':
        await message.add_reaction("❌")
    if result[0] == 'badUser':
        await message.add_reaction("⛔")
    if result[1]:
        await message.pin()
    if result[2]:
        cur.execute("SELECT * FROM getReactions(%s, %s);",
            (message.channel.id, number))
        for reaction in cur.fetchall():
            await message.add_reaction(reaction[0])

    return result[0] == 'good'



async def loadCountdown(bot, countdown):
    """
    Loads countdown messages from a Discord countdown

    Parameters
    ----------
    bot : commands.Bot
        The bot to load messages with
    cur : psycopg.cursor
        The database cursor
    countdown : Countdown
        The countdown to load messages for
    """

    with bot.db_connection.cursor() as cur:
        # Clear countdown
        cur.execute("CALL clearCountdown(%s);", (countdown.id,))

        # Get Discord messages
        messages = [message async for message in
                       bot.get_channel(countdown.id).history(limit=10100)]
        messages.reverse()

        # Add messages to countdown
        for message in messages:
            await addMessage(cur, message)

    # Commit changes
    bot.db_connection.commit()
