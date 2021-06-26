# Import dependencies
import discord
from discord.ext import commands


# Import modules
from src import analyticsCog, utilitiesCog, Session
from src.botUtilities import addMessage, COLORS, getCountdown, getPrefix



# Create Discord bot
bot = commands.Bot(command_prefix=getPrefix, case_insensitive=True)



# Add cogs
bot.add_cog(analyticsCog.Analytics(bot))
bot.add_cog(utilitiesCog.Utilities(bot))




@bot.event
async def on_ready():
    print(f"Connected to Discord as {bot.user}")



@bot.event
async def on_message(obj):
    # Respond to @mentions
    if bot.user in obj.mentions:
        embed=discord.Embed(title="countdown-bot", description=f"Use `{(await bot.get_prefix(obj))[0]}help` to view help information", color=COLORS["embed"])
        await obj.channel.send(embed=embed)

    # Parse countdown message
    with Session() as session:
        countdown = getCountdown(session, obj.channel.id)
        if (countdown and obj.author.name != "countdown-bot"):
            # Add message to countdown and commit changes
            if (await addMessage(countdown, obj)): session.commit()

    # Run commands
    try:
        await bot.process_commands(obj)
    except:
        pass



@bot.event
async def on_command_error(ctx, error):
    # Send error embed
    embed=discord.Embed(title="Error", description=str(error), color=COLORS["error"])
    if (isinstance(error, commands.CommandNotFound)):
        embed.description = f"Command not found: `{str(error)[9:-14]}`"
    else:
        embed.description = str(error)
    embed.description += f"\nUse `{(await bot.get_prefix(ctx))[0]}help` to view help information\n"
    await ctx.send(embed=embed)
