# Import dependencies
import discord
import re

# Import modules
from src.models import Countdown, Message, MessageIncorrectError, MessageNotAllowedError



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



def getPrefix(databaseSessionMaker, ctx, default):
    """
    Get the bot prefix for a certain context

    Parameters
    ----------
    databaseSessionMaker : sqlalchemy.orm.sessionmaker
        The database session maker
    ctx : discord.ext.commands.Context
        The context
    default : list
        The default prefixes
    """

    with databaseSessionMaker() as session:
        # Countdown channel
        countdown = getCountdown(session, ctx.channel.id)
        if (countdown and len(countdown.prefixes) > 0):
            return [x.value for x in countdown.prefixes]

        # Server with countdown channels
        if (isinstance(ctx.channel, discord.channel.TextChannel)):
            serverCountdowns = session.query(Countdown).filter(Countdown.server_id == ctx.channel.guild.id).all()
            # Get list of prefixes
            prefixes = []
            for countdown in serverCountdowns:
                prefixes += [x.value for x in countdown.prefixes]
            if (len(prefixes) > 0):
                return list(dict.fromkeys(prefixes))

        # Return default prefixes
        return default



def parseMessage(message):
    """
    Parses a countdown message from a Discord message

    Parameters
    ----------
    message : discord.Message
        The Discord message

    Returns
    -------
    Message
    """

    return Message(
        id = message.id,
        countdown_id = message.channel.id,
        author_id = message.author.id,
        timestamp = message.created_at,
        number = int(re.findall("^[0-9,]+", message.content)[0].replace(",","")),
    )



async def addMessage(countdown, rawMessage):
    """
    Parse a message and add it to a countdown

    Notes
    -----
    If the message is invalid or incorrect, a reacted will be added accordingly

    Parameters
    ----------
    countdown : Countdown
        The countdown
    rawMessage : discord.Message
        The Discord message object

    Returns
    -------
    bool
        Whether the message was valid and added to the countdown
    """

    try:
        # Parse message
        message = parseMessage(rawMessage)

        # Add message
        countdown.addMessage(message)

        # Mark important messages
        if (message.number in [x.number for x in countdown.reactions]):
            for reaction in [x for x in countdown.reactions if x.number == message.number]:
                try:
                    await rawMessage.add_reaction(reaction.value)
                except:
                    pass
        if (countdown.messages[0].number >= 500 and message.number % (countdown.messages[0].number // 50) == 0):
            await rawMessage.pin()
    except MessageNotAllowedError:
        await rawMessage.add_reaction("⛔")
        return False
    except MessageIncorrectError:
        await rawMessage.add_reaction("❌")
        return False
    except:
        return False
    else:
        return True



async def loadCountdown(bot, countdown):
    """
    Loads countdown messages from a Discord countdown

    Parameters
    ----------
    bot : commands.Bot
        The bot to load messages with
    countdown : Countdown
        The countdown to load messages for
    """

    # Clear countdown
    countdown.messages = []

    # Get Discord messages
    rawMessages = await bot.get_channel(countdown.id).history(limit=10100).flatten()
    rawMessages.reverse()

    # Add messages to countdown
    for rawMessage in rawMessages:
        await addMessage(countdown, rawMessage)
