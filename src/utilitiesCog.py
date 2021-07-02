# Import dependencies
import discord
from discord.ext import commands

# Import modules
from src.botUtilities import COLORS, getContextCountdown, getCountdown, loadCountdown
from src.models import Countdown, Prefix, Reaction



class Utilities(commands.Cog):
    def __init__(self, bot, databaseSessionMaker):
        self.bot = bot
        self.databaseSessionMaker = databaseSessionMaker
        self.bot.remove_command("help")



    @commands.command()
    async def activate(self, ctx):
        """
        Turns a channel into a countdown
        """

        with self.databaseSessionMaker() as session:
            # Channel is already a countdown
            if (getCountdown(session, ctx.channel.id)):
                embed = discord.Embed(title="Error", description="This channel is already a countdown", color=COLORS["error"])
                await ctx.send(embed=embed)

            # Channel is a DM
            elif (not isinstance(ctx.channel, discord.channel.TextChannel)):
                embed = discord.Embed(title="Error", description="This command must be run inside a server", color=COLORS["error"])
                await ctx.send(embed=embed)

            # User isn't authorized
            elif (not ctx.message.author.guild_permissions.administrator):
                embed = discord.Embed(title="Error", description="You must be an administrator to turn a channel into a countdown", color=COLORS["error"])
                await ctx.send(embed=embed)

            # Channel is valid
            else:
                # Create countdown
                countdown = Countdown(
                    id = ctx.channel.id,
                    server_id = ctx.channel.guild.id,
                    timezone = 0,
                    prefixes = [Prefix(countdown_id=ctx.channel.id, value=x) for x in self.bot.prefixes],
                    reactions = [],
                    messages = [],
                )

                # Send initial response
                print(f"Activated {self.bot.get_channel(ctx.channel.id)} as a countdown")
                embed = discord.Embed(title=":clock3: Loading Countdown", description="@here This channel is now a countdown\nPlease wait to start counting", color=COLORS["embed"])
                msg = await ctx.send(embed=embed)

                # Load countdown
                await loadCountdown(self.bot, countdown)
                session.add(countdown)
                session.commit()

                # Send final response
                embed = discord.Embed(title=":white_check_mark: Countdown Activated", description="@here This channel is now a countdown\nYou may start counting!", color=COLORS["embed"])
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
            embed.color = COLORS["error"]
            embed.description = "This command must be run in a countdown channel or a server with a countdown channel"
            await ctx.send(embed=embed)
            return

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Get / set settings
            if (key is None):
                embed.description = f"**Countdown Channel:** <#{countdown.id}>\n"
                embed.description += f"**Command Prefixes:** `{'`, `'.join([x.value for x in countdown.prefixes])}`\n"
                embed.description += f"**Countdown Timezone:** {countdown.getTimezone()}\n"
                if (len(countdown.reactions) == 0):
                    embed.description += f"**Reactions:** none\n"
                else:
                    embed.description += f"**Reactions:**\n"
                for number in list(dict.fromkeys([x.number for x in countdown.reactions])):
                    embed.description += f"**-** #{number}: {', '.join([x.value for x in countdown.reactions if x.number == number])}\n"
            elif (not ctx.message.author.guild_permissions.administrator):
                embed.color = COLORS["error"]
                embed.description = f"You must be an administrator to modify settings"
            elif (len(args) == 0):
                embed.color = COLORS["error"]
                embed.description = f"Please provide a value for the setting"
            elif (key in ["tz", "timezone"]):
                try:
                    countdown.timezone = float(args[0])
                except:
                    embed.color = COLORS["error"]
                    embed.description = f"Invalid timezone: {args[0]}"
                else:
                    embed.description = f"Timezone set to {countdown.getTimezone()}"
            elif (key in ["prefix", "prefixes"]):
                countdown.prefixes = [Prefix(countdown_id=ctx.channel.id, value=x) for x in args]
                embed.description = f"Prefixes updated"
            elif (key in ["react"]):
                try:
                    number = int(args[0])
                    if (number < 0):
                        embed.color = COLORS["error"]
                        embed.description = f"Number must be greater than zero"
                    elif (len(args) == 1):
                        countdown.reactions = [x for x in countdown.reactions if x.number != number]
                        embed.description = f"Removed reactions for #{number}"
                    else:
                        countdown.reactions = [x for x in countdown.reactions if x.number != number]
                        countdown.reactions += [Reaction(countdown_id=countdown.id, number=number, value=x) for x in args[1:]]
                        embed.description = f"Updated reactions for #{number}"
                except:
                    embed.color = COLORS["error"]
                    embed.description = f"Invalid number: {args[0]}"
            else:
                embed.color = COLORS["error"]
                embed.description = f"Setting not found: `{key}`\n"
                embed.description += f"Use `{(await self.bot.get_prefix(ctx))[0]}help config` to view the list of settings"

            # Save changes
            session.commit()

        # Send embed
        await ctx.send(embed=embed)



    @commands.command()
    async def deactivate(self, ctx):
        """
        Deactivates a countdown channel
        """

        with self.databaseSessionMaker() as session:
            # Channel isn't a countdown
            countdown = getCountdown(session, ctx.channel.id)
            if (not countdown):
                embed = discord.Embed(title="Error", description="This channel isn't a countdown", color=COLORS["error"])
                await ctx.send(embed=embed)

            # User isn't authorized
            elif (not ctx.author.guild_permissions.administrator):
                embed = discord.Embed(title="Error", description="You must be an administrator to deactivate a countdown channel", color=COLORS["error"])
                await ctx.send(embed=embed)

            # Channel is valid
            else:
                # Delete countdown
                session.delete(countdown)
                session.commit()

                # Send response
                print(f"Deactivated {self.bot.get_channel(ctx.channel.id)} as a countdown")
                embed = discord.Embed(title=":octagonal_sign: Countdown Deactivated", description="@here This channel is no longer a countdown", color=COLORS["embed"])
                await ctx.send(embed=embed)



    @commands.command(aliases=["h", ""])
    async def help(self, ctx, command=None):
        """
        Shows help information
        """

        # Initialize help information
        prefixes = await self.bot.get_prefix(ctx)
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
                "**-** `analytics`, `a`: Shows all countdown analytics\n" \
                "**-** `contributors`, `c`: Shows information about countdown contributors\n" \
                "**-** `eta`, `e`: Shows information about the estimated completion date\n" \
                "**-** `heatmap`: Shows a heatmap of when messages are sent\n" \
                "**-** `leaderboard`, `l`: Shows the countdown leaderboard\n" \
                "**-** `progress`, `p`: Shows information about countdown progress\n" \
                "**-** `speed`, `s`: Shows information about countdown speed\n",
            "behavior":
                "**-** Reacts with :no_entry: when a user counts out of turn\n" \
                "**-** Reacts with :x: when a user counts incorrectly\n" \
                "**-** Ignores messages that don't start with a (positive) number\n" \
                "**-** Pins numbers every 2% if the countdown started at 500 or higher\n",
            "getting-started":
                f"**1.** View help information using the `{prefixes[0]}help` command\n" \
                f"**2.** Activate a new countdown channel using the `{prefixes[0]}activate` command\n" \
                f"**3.** Change my settings using the `{prefixes[0]}config` command\n" \
                f"**4.** View countdown analytics using the `{prefixes[0]}analytics` command\n",
            "troubleshooting":
                f"**1.** Run `{prefixes[0]}ping` to make sure that I'm online\n" \
                f"**2.** If I reacted incorrectly to a message, remove my incorrect reaction(s)\n" \
                f"**3.** Run `{prefixes[0]}reload` in the countdown channel\n",
            "activate":
                "**Name:** activate\n" \
                "**Description:** Turns a channel into a countdown\n" \
                f"**Usage:** `{prefixes[0]}activate`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Notes:** Users must have admin permissions to turn a channel into a countdown\n",
            "analytics":
                "**Name:** analytics\n" \
                "**Description:** Shows all countdown analytics\n" \
                f"**Usage:** `{prefixes[0]}analytics|a`\n" \
                "**Aliases:** `a`\n" \
                "**Arguments:**\n" \
                "**Notes:** none\n",
            "config":
                "**Name:** config\n" \
                "**Description:** Shows and modifies countdown settings\n" \
                f"**Usage:** `{prefixes[0]}config [<key> <value>...]`\n" \
                "**Aliases:** none\n" \
                "**Arguments:**\n" \
                "**-** `<key>`: The name of the setting to modify (see below).\n" \
                "**-** `<value>`: The new value(s) for the setting. If no key-value pair is supplied, all settings will be shown.\n" \
                "**Available Settings:**\n" \
                "**-** `prefix`, `prefixes`: The prefix(es) for the self.bot.\n" \
                "**-** `tz`, `timezone`: The UTC offset, in hours.\n" \
                "**-** `react`: The reactions for a certain number. Ex: `react 0 :partying_face: :smile:`\n" \
                "**Notes:** Users must have admin permissions to modify settings\n",
            "contributors":
                "**Name:** contributors\n" \
                "**Description:** Shows information about countdown contributors\n" \
                f"**Usage:** `{prefixes[0]}contributors|c [history|h]`\n" \
                "**Aliases:** `c`\n" \
                "**Arguments:**\n" \
                "**-** `history`, `h`: Shows historical data about countdown contributors\n" \
                "**Notes:** The contributors embed will only show the top 20 contributors\n",
            "deactivate":
                "**Name:** deactivate\n" \
                "**Description:** Deactivates a countdown channel\n" \
                f"**Usage:** `{prefixes[0]}deactivate`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Notes:** Users must have admin permissions to deactivate a countdown channel\n",
            "eta":
                "**Name:** eta\n" \
                "**Description:** Shows information about the estimated completion date\n" \
                f"**Usage:** `{prefixes[0]}eta|e [<period>]`\n" \
                "**Aliases:** `e`\n" \
                "**Arguments:**\n" \
                "**-** `<period>`: The size of the period in hours. The default is 24 hours.\n" \
                "**Notes:** none\n",
            "heatmap":
                "**Name:** heatmap\n" \
                "**Description:** Shows a heatmap of when countdown messages are sent\n" \
                f"**Usage:** `{prefixes[0]}heatmap [<user>]`\n" \
                "**Aliases:** none\n" \
                "**Arguments:**\n" \
                "**-** `<user>`: The username or nickname of the user to view heatmap information about. If no value is supplied, the general heatmap will be shown.\n" \
                "**Notes:** none\n",
            "help":
                "**Name:** help\n" \
                "**Description:** Shows help information\n" \
                f"**Usage:** `{prefixes[0]}help|h [<command>]`\n" \
                "**Aliases:** `h`\n" \
                "**Arguments:**\n" \
                "**-** `<command>`: The command to view help information about. If no value is supplied, general help information will be shown.\n" \
                "**Notes:** none\n",
            "leaderboard":
                "**Name:** leaderboard\n" \
                "**Description:** Shows the countdown leaderboard\n" \
                f"**Usage:** `{prefixes[0]}leaderboard|l [<user>]`\n" \
                "**Aliases:** `l`\n" \
                "**Arguments:**\n" \
                "**-** `<user>`: The rank, username, or nickname of the user to view leaderboard information about. If no value is supplied, the whole leaderboard will be shown.\n" \
                "**Notes:** The leaderboard embed will only show the top 20 contributors\n",
            "ping":
                "**Name:** ping\n" \
                "**Description:** Pings the bot\n" \
                f"**Usage:** `{prefixes[0]}ping`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Notes:** none\n",
            "progress":
                "**Name:** progress\n" \
                "**Description:** Shows information about countdown progress\n" \
                f"**Usage:** `{prefixes[0]}progress|p`\n" \
                "**Aliases:** `p`\n" \
                "**Arguments:** none\n" \
                "**Notes:** none\n",
            "reload":
                "**Name:** reload\n" \
                "**Description:** Reloads the countdown cache\n" \
                f"**Usage:** `{prefixes[0]}reload`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Notes:** none\n",
            "speed":
                "**Name:** speed\n" \
                "**Description:** Shows information about countdown speed\n" \
                f"**Usage:** `{prefixes[0]}speed|s [<period>]`\n" \
                "**Aliases:** `s`\n" \
                "**Arguments:**\n" \
                "**-** `<period>`: The size of the period in hours. The default is 24 hours.\n" \
                "**Notes:** none\n",
        }

        # Create embed
        embed=discord.Embed(title=":grey_question: countdown-bot Help", color=COLORS["embed"])
        if (command is None):
            embed.add_field(name="Command Prefixes :gear:", value=help_text["prefixes"], inline=False)
            embed.add_field(name="Utility Commands :wrench:", value=help_text["utility-commands"], inline=False)
            embed.add_field(name="Analytics Commands :bar_chart:", value=help_text["analytics-commands"], inline=False)
            embed.add_field(name="Behavior in Countdown Channels :robot:", value=help_text["behavior"], inline=False)
            embed.add_field(name="Getting Started :rocket:", value=help_text["getting-started"], inline=False)
            embed.add_field(name="Troubleshooting :screwdriver:", value=help_text["troubleshooting"], inline=False)
            embed.description = f"Use `{prefixes[0]}help command` to get more info on a command"
        elif (command.lower() in ["activate"]):
            embed.description = help_text["activate"]
        elif (command.lower() in ["a", "analytics"]):
            embed.description = help_text["analytics"]
        elif (command.lower() in ["config"]):
            embed.description = help_text["config"]
        elif (command.lower() in ["c", "contributors"]):
            embed.description = help_text["contributors"]
        elif (command.lower() in ["deactivate"]):
            embed.description = help_text["deactivate"]
        elif (command.lower() in ["e", "eta"]):
            embed.description = help_text["eta"]
        elif (command.lower() in ["heatmap"]):
            embed.description = help_text["heatmap"]
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



    @commands.command()
    async def ping(self, ctx):
        """
        Pings the bot
        """

        embed=discord.Embed(title=":ping_pong: Pong!", color=COLORS["embed"])
        embed.description = f"**Latency:** {round(self.bot.latency * 1000)} ms\n"
        await ctx.send(embed=embed)



    @commands.command()
    async def reload(self, ctx):
        """
        Reloads the countdown cache
        """

        with self.databaseSessionMaker() as session:
            countdown = getCountdown(session, ctx.channel.id)
            if (countdown):
                # Send initial response
                embed = discord.Embed(title=":clock3: Reloading Countdown Cache", description="Please wait to continue counting.", color=COLORS["embed"])
                msg = await ctx.channel.send(embed=embed)

                # Reload messages
                await loadCountdown(self.bot, countdown)
                session.commit()

                # Send final response
                print(f"Reloaded messages from {self.bot.get_channel(ctx.channel.id)}")
                embed = discord.Embed(title=":white_check_mark: Countdown Cache Reloaded", description="Done! You may continue counting!", color=COLORS["embed"])
                await msg.edit(embed=embed)
            else:
                embed = discord.Embed(title="Error", description="This command must be used in a countdown channel", color = COLORS["error"])
                await ctx.channel.send(embed=embed)
