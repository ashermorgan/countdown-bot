# Import dependencies
import discord
from discord.ext import commands
import logging


# Import modules
from . import analyticsCog, coreCog, helpCog
from .botUtilities import addMessage, COLORS, CountdownNotFound, ContributorNotFound, CommandError, getPrefix



class CountdownBot(commands.Bot):
    def __init__(self, db_connection, prefixes):
        # Set properties
        self.db_connection = db_connection
        self.prefixes = prefixes
        self.logger = logging.getLogger(__name__)

        # Get intents
        intents = discord.Intents.default()
        intents.message_content = True

        # Initialize bot
        super().__init__(command_prefix=lambda bot, ctx: getPrefix(self.db_connection, ctx, self.prefixes), intents=intents)



    async def setup_hook(self):
        await self.add_cog(helpCog.Help(self))
        await self.add_cog(coreCog.Core(self, self.db_connection))
        await self.add_cog(analyticsCog.Analytics(self, self.db_connection))



    async def on_ready(self):
        self.logger.info(f"Connected to Discord as {self.user} (ID {self.user.id})")



    async def on_message(self, obj):
        try:
            # Make command prefixes, names, and arguments case insensitive
            obj.content = obj.content.lower()

            # Run commands
            await self.process_commands(obj)
        except:
            pass



    async def on_command_error(self, ctx, error):
        # Rollback database transaction
        self.db_connection.rollback()

        # Send error embed
        embed=discord.Embed(title=":warning: Error", description=str(error), color=COLORS["error"])
        if (isinstance(error, commands.CommandNotFound)):
            embed.description = f"Command not found: `{str(error)[9:-14]}`"
        elif (isinstance(error.original, CountdownNotFound)):
            embed.description = f"Countdown not found"
        elif (isinstance(error.original, ContributorNotFound)):
            embed.description = f"Contributor not found: `{error.original.args[0]}`"
        elif (isinstance(error.original, CommandError)):
            embed.description = error.original.args[0]
        else:
            # Unanticipated error
            embed.description = str(error)
            logging.error(f"Error during command {ctx.message.content}", exc_info=error)
        embed.description += f"\n\nUse `{(await self.get_prefix(ctx))[0]}help` to view help information"
        await ctx.send(embed=embed)
