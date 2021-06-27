# Import dependencies
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter
import os
import re
import tempfile

# Import modules
from src.botUtilities import COLORS, getContextCountdown, getNickname, getUsername
from src.models import POINT_RULES



class Analytics(commands.Cog):
    def __init__(self, bot, databaseSessionMaker):
        self.bot = bot
        self.databaseSessionMaker = databaseSessionMaker



    @commands.command(aliases=["a"])
    async def analytics(self, ctx):
        """
        Shows all countdown analytics
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Check if countdown is empty
            if (len(countdown.messages) == 0):
                embed=discord.Embed(title=":bar_chart: Countdown Analytics", color=COLORS["error"])
                embed.description = "The countdown is empty"
                await ctx.send(embed=embed)

            # Run analytics commands
            else:
                await self.contributors(ctx, "")
                await self.contributors(ctx, "history")
                if (len(countdown.messages) >= 2): await self.eta(ctx)  # Countdown must have 2 messages to run eta command
                await self.leaderboard(ctx)
                await self.progress(ctx)
                await self.speed(ctx)



    @commands.command(aliases=["c"])
    async def contributors(self, ctx, option=""):
        """
        Shows information about countdown contributors
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Get stats
            stats = countdown.progress()
            contributors = countdown.contributors()

            # Create embed
            embed=discord.Embed(title=":busts_in_silhouette: Countdown Contributors", color=COLORS["embed"])

            # Make sure the countdown has started
            if (len(countdown.messages) == 0):
                embed.color = COLORS["error"]
                embed.description = "The countdown is empty."
            elif (option.lower() in ["h", "history"]):
                # Create figure
                fig, ax = plt.subplots()
                ax.set_xlabel("Progress")
                ax.set_ylabel("Percentage of Contributions")
                ax.yaxis.set_major_formatter(PercentFormatter())

                # Get historical contributor data
                authors = {}
                for author in contributors:
                    authors[author["author"]] = [{"progress":0, "percentage":0, "total":0}]
                for message in countdown.messages:
                    for author in authors:
                        if (author == message.author_id):
                            authors[author] += [{"progress":(stats["total"] - message.number), "percentage":(authors[author][-1]["total"] + 1)/(stats["total"] - message.number + 1) * 100, "total":authors[author][-1]["total"] + 1}]
                        else:
                            authors[author] += [{"progress":(stats["total"] - message.number), "percentage":(authors[author][-1]["total"] + 0)/(stats["total"] - message.number + 1) * 100, "total":authors[author][-1]["total"] + 0}]

                # Plot data and add legend
                for author in list(authors.keys())[:min(len(authors), 15)]:
                    # Top 15 contributors get included in the legend
                    ax.plot([x["progress"] for x in authors[author]], [x["percentage"] for x in authors[author]], label=await getUsername(self.bot, author))
                for author in list(authors.keys())[15:max(len(authors), 15)]:
                    ax.plot([x["progress"] for x in authors[author]], [x["percentage"] for x in authors[author]])
                ax.legend(bbox_to_anchor=(1,1.025), loc="upper left")

                # Save graph
                fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                file = discord.File(tmp.name, filename="image.png")

                # Add content to embed
                embed.description = f"**Countdown Channel:** <#{countdown.id}>"
                embed.set_image(url="attachment://image.png")
            elif (option == ""):
                # Create figure
                fig, ax = plt.subplots()

                # Add data to graph
                x = [x["author"] for x in contributors]
                y = [x["contributions"] for x in contributors]
                pieData = ax.pie(y, autopct="%1.1f%%", startangle=90)

                # Add legend
                ax.legend(pieData[0], [await getUsername(self.bot, i) for i in x[:min(len(x), 15)]], bbox_to_anchor=(1,1.025), loc="upper left")

                # Save graph
                fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                file = discord.File(tmp.name, filename="image.png")

                # Add content to embed
                embed.description = f"**Countdown Channel:** <#{countdown.id}>"
                ranks = ""
                users = ""
                contributions = ""
                for i in range(0, min(len(x), 20)):
                    ranks += f"{i+1:,}\n"
                    contributions += f"{y[i]:,} *({round(y[i] / len(countdown.messages) * 100, 1)}%)*\n"
                    users += f"<@{x[i]}>\n"
                embed.add_field(name="Rank",value=ranks, inline=True)
                embed.add_field(name="User",value=users, inline=True)
                embed.add_field(name="Contributions",value=contributions, inline=True)
                embed.set_image(url="attachment://image.png")
            else:
                embed.color = COLORS["error"]
                embed.description = f"Unrecognized option: `{option}`\n"
                embed.description += f"Use `{(await self.bot.get_prefix(ctx))[0]}help contributors` to view help information"

        # Send embed
        try:
            await ctx.send(file=file, embed=embed)
        except:
            await ctx.send(embed=embed)

        # Remove temp file
        try:
            os.remove(tmp.name)
        except:
            print(f"Unable to delete temp file: {tmp.name}.")



    @commands.command(aliases=["e"])
    async def eta(self, ctx, period="24.0"):
        """
        Shows information about the estimated completion date
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":calendar: Countdown Estimated Completion Date", color=COLORS["embed"])

            # Parse period
            try:
                period = float(period)
            except:
                embed.color = COLORS["error"]
                embed.description = "The period must be a number"
            else:
                if (len(countdown.messages) < 2):
                    embed.color = COLORS["embed"]
                    embed.description = "The countdown must have at least two messages"
                elif (period < 0.01):
                    embed.color = COLORS["error"]
                    embed.description = "The period cannot be less than 0.01 hours"
                else:
                    # Get stats
                    eta = countdown.eta(timedelta(hours=period))

                    # Create figure
                    fig, ax = plt.subplots()
                    ax.set_xlabel("Time")
                    fig.autofmt_xdate()

                    # Add ETA data to graph
                    ax.plot(eta[0], eta[1], "C0", label="Estimated Completion Date")

                    # Add reference line graph
                    ax.plot([eta[0][0], eta[0][-1]], [eta[0][0], eta[0][-1]], "--C1", label="Current Date")

                    # Add legend
                    ax.legend()

                    # Save graph
                    fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                    file = discord.File(tmp.name, filename="image.png")

                    # Calculate embed data
                    maxEta = max(eta[1])
                    maxDate = eta[0][eta[1].index(maxEta)]
                    minEta = min(eta[1][1:])
                    minDate = eta[0][eta[1].index(minEta)]
                    end = eta[1][-1] + timedelta(hours=countdown.timezone)
                    endDiff = eta[1][-1] - datetime.utcnow()

                    # Add content to embed
                    embed.description = f"**Countdown Channel:** <#{countdown.id}>\n\n"
                    embed.description += f"**Maximum Estimate:** {maxEta.date()} (on {maxDate.date()})\n"
                    embed.description += f"**Minimum Estimate:** {minEta.date()} (on {minDate.date()})\n"
                    if endDiff < timedelta(seconds=0):
                        embed.description += f"**Actual Completion Date:** {end.date()} ({(-1 * endDiff).days:,} days ago)\n"
                    else:
                        embed.description += f"**Current Estimate:** {end.date()} ({endDiff.days:,} days from now)\n"
                    embed.set_image(url="attachment://image.png")

        # Send embed
        try:
            await ctx.send(file=file, embed=embed)
        except:
            await ctx.send(embed=embed)

        # Remove temp file
        try:
            os.remove(tmp.name)
        except:
            print(f"Unable to delete temp file: {tmp.name}.")



    @commands.command(aliases=["l"])
    async def leaderboard(self, ctx, user=None):
        """
        Shows the countdown leaderboard
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Get leaderboard
            leaderboard = countdown.leaderboard()

            # Create embed
            embed=discord.Embed(title=":trophy: Countdown Leaderboard", color=COLORS["embed"])

            # Make sure the countdown has started
            if (len(countdown.messages) == 0):
                embed.color = COLORS["error"]
                embed.description = "The countdown is empty."
            elif (user is None):
                # Add description
                embed.description = f"**Countdown Channel:** <#{countdown.id}>"

                # Add leaderboard
                ranks = ""
                points = ""
                users = ""
                for i in range(0, min(len(leaderboard), 20)):
                    ranks += f"{i+1:,}\n"
                    points += f"{leaderboard[i]['points']:,}\n"
                    users += f"<@{leaderboard[i]['author']}>\n"
                embed.add_field(name="Rank",value=ranks, inline=True)
                embed.add_field(name="Points",value=points, inline=True)
                embed.add_field(name="User",value=users, inline=True)

                # Add leaderboard rules
                rules = ""
                values = ""
                for rule in POINT_RULES:
                    rules += f"{rule}\n"
                    values += f"{POINT_RULES[rule]} points\n"
                embed.add_field(name="Rules", value="Only 1 rule is applied towards each number", inline=False)
                embed.add_field(name="Numbers", value=rules, inline=True)
                embed.add_field(name="Points", value=values, inline=True)
            else:
                rank = None
                if (re.match("^\d+$", user) and int(user) > 0 and int(user) <= len(leaderboard)):
                    # Get user from rank
                    rank = int(user) - 1
                elif (re.match("^<@!\d+>$", user) and int(user[3:-1]) in [x["author"] for x in leaderboard]):
                    # Get user from mention
                    rank = [x["author"] for x in leaderboard].index(int(user[3:-1]))
                else:
                    # Get user from username
                    for contributor in leaderboard:
                        username = await getUsername(self.bot, contributor["author"])
                        if (username.lower().startswith(user.lower())):
                            rank = leaderboard.index(contributor)

                    if (rank == None):
                        # Get user from nickname
                        for contributor in leaderboard:
                            nickname = await getNickname(self.bot, countdown.server_id, contributor["author"])
                            if (nickname.lower().startswith(user.lower())):
                                rank = leaderboard.index(contributor)

                        if (rank == None):
                            # User not found
                            embed.color = COLORS["error"]
                            embed.description = f"User not found: `{user}`"
                            await ctx.send(embed=embed)
                            return

                # Add description
                embed.description = f"**Countdown Channel:** <#{countdown.id}>\n\n"
                embed.description += f"**User:** <@{leaderboard[rank]['author']}>\n"
                embed.description += f"**Rank:** #{rank + 1:,}\n"
                embed.description += f"**Total Points:** {leaderboard[rank]['points']:,}\n"
                embed.description += f"**Total Contributions:** {leaderboard[rank]['contributions']:,} *({round(leaderboard[rank]['contributions'] / len(countdown.messages) * 100, 1)}%)*\n"

                # Add points breakdown
                rules = ""
                points = ""
                percentage = ""
                for category in leaderboard[rank]["breakdown"]:
                    rules += f"{category}\n"
                    points += f"{leaderboard[rank]['breakdown'][category] * POINT_RULES[category]:,} *({leaderboard[rank]['breakdown'][category]:,})*\n"
                    if (leaderboard[rank]['points'] > 0):
                        percentage += f"{round(leaderboard[rank]['breakdown'][category] * POINT_RULES[category] / leaderboard[rank]['points'] * 100, 1)}%\n"
                    else:
                        percentage += "0%\n"
                embed.add_field(name="Category", value=rules, inline=True)
                embed.add_field(name="Points", value=points, inline=True)
                embed.add_field(name="Percentage", value=percentage, inline=True)

        # Send embed
        await ctx.send(embed=embed)



    @commands.command(aliases=["p"])
    async def progress(self, ctx):
        """
        Shows information about countdown progress
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":chart_with_downwards_trend: Countdown Progress", color=COLORS["embed"])

            # Make sure the countdown has started
            if (len(countdown.messages) == 0):
                embed.color = COLORS["error"]
                embed.description = "The countdown is empty."
            else:
                # Get progress stats
                stats = countdown.progress()

                # Create figure
                fig, ax = plt.subplots()
                ax.set_xlabel("Time")
                ax.set_ylabel("Progress")
                fig.autofmt_xdate()

                # Add data to graph
                x = [stats["start"] + timedelta(hours=countdown.timezone)] + [x["time"] + timedelta(hours=countdown.timezone) for x in stats["progress"]]
                y = [0] + [x["progress"] for x in stats["progress"]]
                ax.plot(x, y)

                # Save graph
                fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                file = discord.File(tmp.name, filename="image.png")

                # Calculate embed data
                start = (stats["start"] + timedelta(hours=countdown.timezone)).date()
                startDiff = (datetime.utcnow() - stats["start"]).days
                end = (stats["eta"] + timedelta(hours=countdown.timezone)).date()
                endDiff = stats["eta"] - datetime.utcnow()

                # Add content to embed
                embed.description = f"**Countdown Channel:** <#{countdown.id}>\n\n"
                embed.description += f"**Progress:** {stats['total'] - stats['current']:,} / {stats['total']:,} ({round(stats['percentage'], 1)}%)\n"
                embed.description += f"**Average Progress per Day:** {round(stats['rate']):,}\n"
                embed.description += f"**Start Date:** {start} ({startDiff:,} days ago)\n"
                if endDiff < timedelta(seconds=0):
                    embed.description += f"**End Date:** {end} ({(-1 * endDiff).days:,} days ago)\n"
                else:
                    embed.description += f"**Estimated End Date:** {end} ({endDiff.days:,} days from now)\n"
                embed.set_image(url="attachment://image.png")

        # Send embed
        try:
            await ctx.send(file=file, embed=embed)
        except:
            await ctx.send(embed=embed)

        # Remove temp file
        try:
            os.remove(tmp.name)
        except:
            print(f"Unable to delete temp file: {tmp.name}.")



    @commands.command(aliases=["s"])
    async def speed(self, ctx, period="24.0"):
        """
        Shows information about countdown speed
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":stopwatch: Countdown Speed", color=COLORS["embed"])

            # Parse period
            try:
                period = float(period)
            except:
                embed.color = COLORS["error"]
                embed.description = "The period must be a number"
            else:
                if (len(countdown.messages) == 0):
                    embed.color = COLORS["error"]
                    embed.description = "The countdown is empty."
                elif (period < 0.01):
                    embed.color = COLORS["error"]
                    embed.description = "The period cannot be less than 0.01 hours"
                else:
                    # Get stats
                    stats = countdown.progress()
                    period = timedelta(hours=period)
                    speed = countdown.speed(period)

                    # Create figure
                    fig, ax = plt.subplots()
                    ax.set_xlabel("Time")
                    ax.set_ylabel("Progress per Period")
                    fig.autofmt_xdate()

                    # Add data to graph
                    for i in range(0, len(speed[0])):
                        ax.bar(speed[0][i], speed[1][i], width=period, align="edge", color="#1f77b4")

                    # Save graph
                    fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                    file = discord.File(tmp.name, filename="image.png")

                    # Add content to embed
                    embed.description = f"**Countdown Channel:** <#{countdown.id}>\n\n"
                    embed.description += f"**Period Size:** {period}\n"
                    if (len(countdown.messages) > 1):
                        rate = (stats['total'] - stats['current'])/((countdown.messages[-1].timestamp - countdown.messages[0].timestamp) / period)
                    else:
                        rate = 0
                    embed.description += f"**Average Progress per Period:** {round(rate):,}\n"
                    embed.description += f"**Record Progress per Period:** {max(speed[1]):,}\n"
                    embed.description += f"**Last Period Start:** {speed[0][-1]}\n"
                    embed.description += f"**Progress during Last Period:** {speed[1][-1]:,}\n"
                    embed.set_image(url="attachment://image.png")

        # Send embed
        try:
            await ctx.send(file=file, embed=embed)
        except:
            await ctx.send(embed=embed)

        # Remove temp file
        try:
            os.remove(tmp.name)
        except:
            print(f"Unable to delete temp file: {tmp.name}.")
