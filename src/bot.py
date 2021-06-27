# Import dependencies
import discord
from discord.ext import commands


# Import modules
from src import analyticsCog, utilitiesCog
from src.botUtilities import addMessage, COLORS, getCountdown, getPrefix
from src.models import getSessionMaker



class CountdownBot(commands.Bot):
    def __init__(self, databaseLocation, prefixes=["c."]):
        # Initialize bot
        commands.Bot.__init__(self, command_prefix=lambda bot, ctx: getPrefix(self.databaseSessionMaker, ctx, self.prefixes), case_insensitive=True)

        # Set properties
        self.databaseSessionMaker = getSessionMaker(databaseLocation)
        self.prefixes = prefixes

        # Add cogs
        self.add_cog(analyticsCog.Analytics(self, self.databaseSessionMaker))
        self.add_cog(utilitiesCog.Utilities(self, self.databaseSessionMaker))



    async def on_ready(self):
        print(f"Connected to Discord as {self.user}")



    async def on_message(self, obj):
        # Respond to @mentions
        if self.user in obj.mentions:
            embed=discord.Embed(title="countdown-bot", description=f"Use `{(await self.get_prefix(obj))[0]}help` to view help information", color=COLORS["embed"])
            await obj.channel.send(embed=embed)

        # Parse countdown message
        with self.databaseSessionMaker() as session:
            countdown = getCountdown(session, obj.channel.id)
            if (countdown and obj.author.name != "countdown-bot"):
                # Add message to countdown and commit changes
                if (await addMessage(countdown, obj)): session.commit()

        # Run commands
        try:
            await self.process_commands(obj)
        except:
            pass



    async def on_command_error(self, ctx, error):
        # Send error embed
        embed=discord.Embed(title="Error", description=str(error), color=COLORS["error"])
        if (isinstance(error, commands.CommandNotFound)):
            embed.description = f"Command not found: `{str(error)[9:-14]}`"
        else:
            embed.description = str(error)
        embed.description += f"\nUse `{(await self.get_prefix(ctx))[0]}help` to view help information\n"
        await ctx.send(embed=embed)
