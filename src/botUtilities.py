# Import dependencies
import discord
import re

# Import modules
from src import Session, settings
from src.models import Countdown, Message, MessageIncorrectError, MessageNotAllowedError



COLORS = {
    "error": 0xD52C42,
    "embed": 0x248AD1,
}



async def getUsername(bot, id):
    """
    Get a username from a user ID.

    Parameters
    ----------
    bot : commands.Bot
        The bot
    id : int
        The user ID.

    Returns
    -------
    str
        The username (ex: "user#0000").
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

    return (await (bot.get_guild(server)).fetch_member(id)).nick or await getUsername(id)



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



def getContextCountdown(session, ctx, resortToFirst=True):
    """
    Get the most relevant countdown to a certain context.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        The database session to use
    ctx : discord.ext.commands.Context
        The context
    resortToFirst : bool
        Whether to return the 1st countdown if no relevant countdowns are found

    Returns
    -------
    Countdown
        The countdown
    """

    global settings

    if (isinstance(ctx.channel, discord.channel.TextChannel)):
        # Countdown channel
        countdown = getCountdown(session, ctx.channel.guild.id)
        if (countdown): return countdown

        # Server with countdown channel: get first countdown in this server that use the current prefix
        countdown = session.query(Countdown).filter(Countdown.server_id == ctx.channel.guild.id and ctx.prefix in [x.value for x in Countdown.prefixes]).first()
        if (countdown): return countdown

    # First countdown channel
    countdown = session.query(Countdown).first()
    if (resortToFirst and countdown): return countdown
    else: raise Exception("Countdown channel not found")



def getPrefix(bot, ctx):
    """
    Get the bot prefix for a certain context.

    Parameters
    ----------
    bot : commands.Bot
        The bot
    ctx : discord.ext.commands.Context
        The context
    """

    with Session() as session:
        # Countdown channel
        global settings
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
        return settings["prefixes"]



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
