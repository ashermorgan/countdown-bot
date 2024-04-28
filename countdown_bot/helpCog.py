# Import dependencies
import discord
from discord.ext import commands

# Import modules
from .botUtilities import COLORS, CommandError



class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")



    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Log status
        self.logger.info(f"Added to {guild} (ID {guild.id})")

        # Get command prefix
        prefix = self.bot.prefixes[0]

        # Create embed
        embed=discord.Embed(title=":rocket: Getting Started with countdown-bot", color=COLORS["embed"])
        embed.description = f"Thanks for adding me to your server! Here are some steps for getting started:\n"
        embed.description += f"**1.** View help information using the `{prefix}help` command\n"
        embed.description += f"**2.** Activate a new countdown channel using the `{prefix}activate` command\n"
        embed.description += f"**3.** Change my settings using the `{prefix}config` command\n"
        embed.description += f"**4.** View countdown analytics using the `{prefix}analytics` command\n"

        # Send embed
        await ctx.guild.system_channel.send(embed=embed)



    @commands.Cog.listener()
    async def on_message(self, obj):
        # Respond to @mentions
        if self.bot.user in obj.mentions:
            embed=discord.Embed(title="countdown-bot", description=f"Use `{(await self.bot.get_prefix(obj))[0]}help` to view help information", color=COLORS["embed"])
            await obj.channel.send(embed=embed)



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
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}activate`\n" \
                "**Notes:** Users must have admin permissions to turn a channel into a countdown\n",
            "analytics":
                "**Name:** analytics\n" \
                "**Description:** Shows all countdown analytics\n" \
                f"**Usage:** `{prefixes[0]}analytics|a`\n" \
                "**Aliases:** `a`\n" \
                "**Arguments: none**\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}analytics`\n" \
                "**Notes:** none\n",
            "config":
                "**Name:** config\n" \
                "**Description:** Shows and modifies countdown settings\n" \
                f"**Usage:** `{prefixes[0]}config [<key> <value>...]`\n" \
                "**Aliases:** none\n" \
                "**Arguments:**\n" \
                "**-** `<key>`: The name of the setting to modify. If no key is supplied, all settings will be shown\n" \
                "**-** `<value>`: The new value(s) for the setting\n" \
                "**Available Settings:**\n" \
                "**-** `prefix`, `prefixes`: The prefix(es) for the bot\n" \
                "**-** `tz`, `timezone`: The UTC offset in hours\n" \
                "**-** `react`: The reactions for a certain number\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}config`\n" \
                f"**-** `{prefixes[0]}config prefixes prefix1 prefix2 prefix3`\n" \
                f"**-** `{prefixes[0]}config timezone -1.5`\n" \
                f"**-** `{prefixes[0]}config react 0 :partying_face: :smile:`\n" \
                "**Notes:** Users must have admin permissions to modify settings\n",
            "contributors":
                "**Name:** contributors\n" \
                "**Description:** Shows information about countdown contributors\n" \
                f"**Usage:** `{prefixes[0]}contributors|c [history|h]`\n" \
                "**Aliases:** `c`\n" \
                "**Arguments:**\n" \
                "**-** `history`, `h`: Shows historical data about countdown contributors\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}contributors`\n" \
                f"**-** `{prefixes[0]}contributors history`\n" \
                "**Notes:** The contributors embed will only show the top 20 contributors\n",
            "deactivate":
                "**Name:** deactivate\n" \
                "**Description:** Deactivates a countdown channel\n" \
                f"**Usage:** `{prefixes[0]}deactivate`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}deactivate`\n" \
                "**Notes:** Users must have admin permissions to deactivate a countdown channel\n",
            "eta":
                "**Name:** eta\n" \
                "**Description:** Shows information about the estimated completion date\n" \
                f"**Usage:** `{prefixes[0]}eta|e`\n" \
                "**Aliases:** `e`\n" \
                "**Arguments:** none\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}eta`\n" \
                "**Notes:** none\n",
            "heatmap":
                "**Name:** heatmap\n" \
                "**Description:** Shows a heatmap of when countdown messages are sent\n" \
                f"**Usage:** `{prefixes[0]}heatmap [<user>]`\n" \
                "**Aliases:** none\n" \
                "**Arguments:**\n" \
                "**-** `<user>`: The user to view heatmap information about. If no value is supplied, the general heatmap will be shown\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}heatmap`\n" \
                f"**-** `{prefixes[0]}heatmap @Alice`\n" \
                "**Notes:** none\n",
            "help":
                "**Name:** help\n" \
                "**Description:** Shows help information\n" \
                f"**Usage:** `{prefixes[0]}help|h [<command>]`\n" \
                "**Aliases:** `h`\n" \
                "**Arguments:**\n" \
                "**-** `<command>`: The command to view help information about. If no value is supplied, general help information will be shown\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}help`\n" \
                f"**-** `{prefixes[0]}help config`\n" \
                "**Notes:** none\n",
            "leaderboard":
                "**Name:** leaderboard\n" \
                "**Description:** Shows the countdown leaderboard\n" \
                f"**Usage:** `{prefixes[0]}leaderboard|l [<user>]`\n" \
                "**Aliases:** `l`\n" \
                "**Arguments:**\n" \
                "**-** `<user>`: The user to view leaderboard information about. If no value is supplied, the whole leaderboard will be shown\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}leaderboard`\n" \
                f"**-** `{prefixes[0]}leaderboard @Alice`\n" \
                "**Notes:** The leaderboard embed will only show the top 20 contributors\n",
            "ping":
                "**Name:** ping\n" \
                "**Description:** Pings the bot\n" \
                f"**Usage:** `{prefixes[0]}ping`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}ping`\n" \
                "**Notes:** none\n",
            "progress":
                "**Name:** progress\n" \
                "**Description:** Shows information about countdown progress\n" \
                f"**Usage:** `{prefixes[0]}progress|p`\n" \
                "**Aliases:** `p`\n" \
                "**Arguments:** none\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}progress`\n" \
                "**Notes:** none\n",
            "reload":
                "**Name:** reload\n" \
                "**Description:** Reloads the countdown cache\n" \
                f"**Usage:** `{prefixes[0]}reload`\n" \
                "**Aliases:** none\n" \
                "**Arguments:** none\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}reload`\n" \
                "**Notes:** This command must be used in a countdown channel\n",
            "speed":
                "**Name:** speed\n" \
                "**Description:** Shows information about countdown speed\n" \
                f"**Usage:** `{prefixes[0]}speed|s [<period>]`\n" \
                "**Aliases:** `s`\n" \
                "**Arguments:**\n" \
                "**-** `<period>`: The size of the period in hours (the default is 24 hours)\n" \
                "**Examples:**\n" \
                f"**-** `{prefixes[0]}speed`\n" \
                f"**-** `{prefixes[0]}speed 48`\n" \
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
            embed.description = f"Use `{prefixes[0]}help <command>` to get more info on a command"
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
            raise CommandError(f"Command not found: `{command}`")

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
