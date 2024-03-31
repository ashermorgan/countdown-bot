# Import dependencies
import discord
from discord.ext import commands
import logging


# Import modules
from src import analyticsCog, utilitiesCog
from src.botUtilities import addMessage, COLORS, CountdownNotFound, ContributorNotFound, CommandError, getCountdown, getPrefix
from src.models import EmptyCountdownError



class CountdownBot(commands.Bot):
    def __init__(self, databaseSessionMaker, prefixes):
        # Set properties
        self.databaseSessionMaker = databaseSessionMaker
        self.prefixes = prefixes
        self.logger = logging.getLogger(__name__)

        # Get intents
        intents = discord.Intents.default()
        intents.message_content = True

        # Initialize bot
        super().__init__(command_prefix=lambda bot, ctx: getPrefix(self.databaseSessionMaker, ctx, self.prefixes), intents=intents)



    async def setup_hook(self):
        await self.add_cog(analyticsCog.Analytics(self, self.databaseSessionMaker))
        await self.add_cog(utilitiesCog.Utilities(self, self.databaseSessionMaker))



    async def on_ready(self):
        self.logger.info(f"Connected to Discord as {self.user} (ID {self.user.id})")



    async def on_guild_join(self, guild):
        # Print status
        self.logger.info(f"Added to {guild} (ID {guild.id})")

        # Create embed
        embed=discord.Embed(title=":rocket: Getting Started with countdown-bot", color=COLORS["embed"])
        embed.description = f"Thanks for adding me to your server! Here are some steps for getting started:\n"
        embed.description += f"**1.** View help information using the `{self.prefixes[0]}help` command\n"
        embed.description += f"**2.** Activate a new countdown channel using the `{self.prefixes[0]}activate` command\n"
        embed.description += f"**3.** Change my settings using the `{self.prefixes[0]}config` command\n"
        embed.description += f"**4.** View countdown analytics using the `{self.prefixes[0]}analytics` command\n"

        # Send embed
        await guild.system_channel.send(embed=embed)



    async def on_message(self, obj):
        # Respond to @mentions
        if self.user in obj.mentions:
            embed=discord.Embed(title="countdown-bot", description=f"Use `{(await self.get_prefix(obj))[0]}help` to view help information", color=COLORS["embed"])
            await obj.channel.send(embed=embed)

        # Parse countdown message
        with self.databaseSessionMaker() as session:
            countdown = getCountdown(session, obj.channel.id)
            if (countdown):
                # Add message to countdown and commit changes
                if (await addMessage(countdown, obj)): session.commit()

        # Run commands
        try:
            # Make command prefixes, names, and arguments case insensitive
            obj.content = obj.content.lower()

            # Execute command
            await self.process_commands(obj)
        except:
            pass



    async def on_command_error(self, ctx, error):
        # Send error embed
        embed=discord.Embed(title=":warning: Error", description=str(error), color=COLORS["error"])
        if (isinstance(error, commands.CommandNotFound)):
            embed.description = f"Command not found: `{str(error)[9:-14]}`"
        elif (isinstance(error.original, CountdownNotFound)):
            embed.description = f"Countdown not found"
        elif (isinstance(error.original, ContributorNotFound)):
            embed.description = f"Contributor not found: `{error.original.args[0]}`"
        elif (isinstance(error.original, EmptyCountdownError)):
            embed.description = f"The countdown is empty"
        elif (isinstance(error.original, CommandError)):
            embed.description = error.original.args[0]
        else:
            # Unanticipated error
            embed.description = str(error)
            logging.error(f"Error during command {ctx.message.content}", exc_info=error)
        embed.description += f"\n\nUse `{(await self.get_prefix(ctx))[0]}help` to view help information"
        await ctx.send(embed=embed)
