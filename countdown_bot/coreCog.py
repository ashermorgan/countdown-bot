# Import dependencies
import discord
from discord.ext import commands

# Import modules
from .botUtilities import COLORS, CommandError, CountdownNotFound, isCountdown, loadCountdown, getContextCountdown, addMessage



class Core(commands.Cog):
    def __init__(self, bot, db_connection):
        self.bot = bot
        self.db_connection = db_connection



    @commands.Cog.listener()
    async def on_message(self, obj):
        # Parse countdown message
        with self.db_connection.cursor() as cur:
            if (await addMessage(cur, obj)):
                self.db_connection.commit()



    @commands.command()
    async def activate(self, ctx):
        """
        Turns a channel into a countdown
        """

        with self.db_connection.cursor() as cur:
            # Check if channel is already a countdown
            if (isCountdown(cur, ctx.channel.id)):
                raise CommandError("This channel is already a countdown")

            # Check if channel is a DM
            if (not isinstance(ctx.channel, discord.channel.TextChannel)):
                raise CommandError("This command must be run inside a server")

            # Check if user isn't authorized
            if (not ctx.message.author.guild_permissions.administrator):
                raise CommandError("You must be an administrator to turn a channel into a countdown")

            # Create countdown
            cur.execute("CALL createCountdown(%s, %s, %s);",
                (ctx.channel.id, ctx.channel.guild.id, self.bot.prefixes[0]))

            # Send initial response
            self.bot.logger.info(f"Activated {self.bot.get_channel(ctx.channel.id)} (ID {ctx.channel.id}) as a countdown")
            embed = discord.Embed(title=":clock3: Loading Countdown", description="This channel is now a countdown\nPlease wait to start counting", color=COLORS["embed"])
            msg = await ctx.send(embed=embed)

            # Load countdown
            await loadCountdown(self.bot, ctx.channel.id)
            self.db_connection.commit()

            # Send final response
            embed = discord.Embed(title=":white_check_mark: Countdown Activated", description="This channel is now a countdown\nYou may start counting!", color=COLORS["embed"])
            await msg.edit(embed=embed)



    @commands.command()
    async def config(self, ctx, key=None, *args):
        """
        Shows and modifies countdown settings
        """

        # Create embed
        embed = discord.Embed(title=":gear: Countdown Settings", color=COLORS["embed"])

        # Make sure context is in a server
        if (not isinstance(ctx.channel, discord.channel.TextChannel)):
            raise CommandError("This command must be run in a countdown channel or a server with a countdown channel")

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)

            if not countdown:
                raise CountdownNotFound()

            # Get / set settings
            if (key is None):
                embed.description = f"**Countdown Channel:** <#{countdown}>\n"

                cur.execute("SELECT * from getPrefixes(%s);", (countdown,))
                prefixes = [x["prefix"] for x in cur.fetchall()]
                embed.description += f"**Command Prefixes:** `{'`, `'.join(prefixes)}`\n"

                cur.execute("CALL getTimezone(%s, null);", (countdown,))
                timezone = cur.fetchone()["_timezone"]
                if (timezone >= 0):
                    embed.description += f"**Countdown Timezone:** UTC+{timezone:.2f}\n"
                else:
                    embed.description += f"**Countdown Timezone:** UTC-{abs(timezone):.2f}\n"

                cur.execute("SELECT * FROM getReactions(%s, NULL);", (countdown,))
                reactions = cur.fetchall()
                if (len(reactions) == 0):
                    embed.description += f"**Reactions:** none\n"
                else:
                    embed.description += f"**Reactions:**\n"
                for number in reversed(list(set([x["number"] for x in reactions]))):
                    embed.description += f"**-** #{number}: {', '.join([x["value"] for x in reactions if x["number"] == number])}\n"

                embed.description += f"\nUse `{ctx.prefix}help config` to view more information about settings\n"
                embed.description += f"Use `{ctx.prefix}config <key> <value>` to modify settings\n"
            elif (not ctx.message.author.guild_permissions.administrator):
                raise CommandError("You must be an administrator to modify settings")
            elif (len(args) == 0):
                raise CommandError("Please provide a value for the setting")
            elif (key in ["tz", "timezone"]):
                try:
                    timezone = float(args[0])
                except:
                    raise CommandError(f"Invalid timezone: `{args[0]}`")
                else:
                    cur.execute("CALL setTimezone(%s, %s);", (countdown, timezone))
                    if (timezone >= 0):
                        embed.description = f"Timezone set to UTC+{timezone:.2f}\n"
                    else:
                        embed.description = f"Timezone set to UTC-{abs(timezone):.2f}\n"
            elif (key in ["prefix", "prefixes"]):
                cur.execute("CALL setPrefixes(%s, %s);", (countdown, list(args)))
                embed.description = f"Prefixes updated"
            elif (key in ["react"]):
                try:
                    number = int(args[0])
                except:
                    raise CommandError(f"Invalid number: `{args[0]}`")
                if (number < 0):
                    raise CommandError("Number must be greater than zero")
                cur.execute("CALL setReactions(%s, %s, %s);",
                    (countdown, number, list(args[1:])))
                if (len(args) == 1):
                    embed.description = f"Removed reactions for #{number}"
                else:
                    embed.description = f"Updated reactions for #{number}"
            else:
                raise CommandError(f"Setting not found: `{key}`")

            # Save changes
            self.db_connection.commit()

        # Send embed
        await ctx.send(embed=embed)



    @commands.command()
    async def deactivate(self, ctx):
        """
        Deactivates a countdown channel
        """

        with self.db_connection.cursor() as cur:
            # Check if channel isn't a countdown
            if (not isCountdown(cur, ctx.channel.id)):
                raise CommandError("This channel isn't a countdown")

            # Check if user isn't authorized
            if (not ctx.author.guild_permissions.administrator):
                raise CommandError("You must be an administrator to deactivate a countdown channel")

            # Delete countdown
            cur.execute("CALL deleteCountdown(%s);",
                (ctx.channel.id,))
            self.db_connection.commit()

            # Send response
            self.bot.logger.info(f"Deactivated {self.bot.get_channel(ctx.channel.id)} (ID {ctx.channel.id}) as a countdown")
            embed = discord.Embed(title=":octagonal_sign: Countdown Deactivated", description="This channel is no longer a countdown", color=COLORS["embed"])
            await ctx.send(embed=embed)



    @commands.command()
    async def reload(self, ctx):
        """
        Reloads the countdown cache
        """

        with self.db_connection.cursor() as cur:
            # Check if channel isn't a countdown
            if (not isCountdown(cur, ctx.channel.id)):
                raise CommandError("Countdown not found\nThis command must be used in a countdown channel")

            # Send initial response
            embed = discord.Embed(title=":clock3: Reloading Countdown Cache", description="Please wait to continue counting", color=COLORS["embed"])
            msg = await ctx.channel.send(embed=embed)

            # Reload messages
            await loadCountdown(self.bot, ctx.channel.id)
            self.db_connection.commit()

            # Send final response
            self.bot.logger.info(f"Reloaded messages from {self.bot.get_channel(ctx.channel.id)} (ID {ctx.channel.id})")
            embed = discord.Embed(title=":white_check_mark: Countdown Cache Reloaded", description="Done! You may continue counting!", color=COLORS["embed"])
            await msg.edit(embed=embed)
