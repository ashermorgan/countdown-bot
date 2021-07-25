# Import dependencies
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import os
import re
import tempfile

# Import modules
from src.botUtilities import COLORS, getContextCountdown, getUsername, getContributor, CommandError
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

        # Run analytics commands
        await self.contributors(ctx, "")
        await self.contributors(ctx, "history")
        await self.eta(ctx)
        await self.heatmap(ctx)
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

            # Create embed
            embed=discord.Embed(title=":busts_in_silhouette: Countdown Contributors", color=COLORS["embed"])

            # Make sure the countdown has started
            if (option.lower() in ["h", "history"]):
                # Create figure
                fig, ax = plt.subplots()
                ax.set_xlabel("Progress")
                ax.set_ylabel("Percentage of Contributions")
                ax.yaxis.set_major_formatter(PercentFormatter())

                # Get stats
                contributors = countdown.historicalContributors()

                # Plot data and add legend
                for author in list(contributors.keys())[:min(len(contributors), 15)]:
                    # Top 15 contributors get included in the legend
                    ax.plot([x["progress"] for x in contributors[author]], [x["percentage"] * 100 for x in contributors[author]], label=await getUsername(self.bot, author))
                for author in list(contributors.keys())[15:max(len(contributors), 15)]:
                    ax.plot([x["progress"] for x in contributors[author]], [x["percentage"] * 100 for x in contributors[author]])
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

                # Get stats
                contributors = countdown.contributors()

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
                raise CommandError(f"Unrecognized option: `{option}`")

        # Send embed
        try:
            await ctx.send(file=file, embed=embed)
        except:
            await ctx.send(embed=embed)

        # Remove temp file
        try:
            os.remove(tmp.name)
        except Exception as e:
            self.bot.logger.error(f"Unable to delete temp file {tmp.name}", exc_info=e)



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
            except ValueError:
                raise CommandError(f"Invalid number: `{period}`")

            # Make sure period is valid
            if (period < 0.01):
                raise CommandError("The period cannot be less than 0.01 hours")

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
        except Exception as e:
            self.bot.logger.error(f"Unable to delete temp file {tmp.name}", exc_info=e)



    @commands.command()
    async def heatmap(self, ctx, user=None):
        """
        Shows a heatmap of when countdown messages are sent
        """

        with self.databaseSessionMaker() as session:
            # Get countdown channel
            countdown = getContextCountdown(session, ctx)

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":calendar_spiral: Countdown Heatmap", color=COLORS["embed"])

            # Get user
            if (user == None):
                userID = None
            else:
                userID = await getContributor(self.bot, countdown, user)

            # Get heatmap matrix
            heatmapMatrix = countdown.heatmap(userID)

            # Define hour and weekday names
            hours = ["12 AM", "1 AM", "2 AM", "3 AM", "4 AM", "5 AM", "6 AM", "7 AM", "8 AM", "9 AM", "10 AM", "11 AM", "12 PM", "1 PM", "2 PM", "3 PM", "4 PM", "5 PM", "6 PM", "7 PM", "8 PM", "9 PM", "10 PM", "11 PM"]
            weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

            # Create figure
            fig, ax = plt.subplots()
            ax.set_xlabel("Hour of Day")
            ax.set_xticks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23])
            ax.set_xticklabels(hours)
            ax.set_ylabel("Day of Week")
            ax.set_yticks([0, 1, 2, 3, 4, 5, 6])
            ax.set_yticklabels(weekdays)

            # Add data to graph
            cmap = plt.get_cmap("jet").copy()
            cmap.set_bad("gray")
            cax = ax.matshow(np.ma.masked_equal(np.array(heatmapMatrix), 0), cmap=cmap, aspect="auto")
            fig.colorbar(cax)

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Get embed data
            total = np.sum(heatmapMatrix)
            averageValue = total / (24*7)
            maxValue = np.max(heatmapMatrix)
            maxWeekday = np.where(heatmapMatrix == maxValue)[0][0]
            maxHour = np.where(heatmapMatrix == maxValue)[1][0]
            currentWeekday = ((datetime.utcnow() + timedelta(hours=countdown.timezone)).weekday() + 1) % 7
            currentHour = (datetime.utcnow() + timedelta(hours=countdown.timezone)).hour
            currentValue = heatmapMatrix[currentWeekday][currentHour]

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{countdown.id}>\n\n"
            if (userID): embed.description += f"**User:** <@{userID}>\n"
            embed.description += f"**Total Contributions:** {total:,}\n"
            embed.description += f"**Average Contributions per Zone:** {round(averageValue):,}\n"
            embed.description += f"**Best Zone:** {hours[maxHour]} to {hours[(maxHour + 1) % 24]} on {weekdays[maxWeekday]}s - {maxValue:,} contributions\n"
            embed.description += f"**Current Zone:** {hours[currentHour]} to {hours[(currentHour + 1) % 24]} on {weekdays[currentWeekday]}s - {currentValue:,} contributions\n"
            embed.set_image(url="attachment://image.png")

        # Send embed
        try:
            await ctx.send(file=file, embed=embed)
        except:
            await ctx.send(embed=embed)

        # Remove temp file
        try:
            os.remove(tmp.name)
        except Exception as e:
            self.bot.logger.error(f"Unable to delete temp file {tmp.name}", exc_info=e)



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
            if (user is None):
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
                # Get user rank
                if (re.match("^\d+$", user) and int(user) > 0 and int(user) <= len(leaderboard)):
                    rank = int(user) - 1
                else:
                    rank = [x["author"] for x in leaderboard].index(await getContributor(self.bot, countdown, user))

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
        except Exception as e:
            self.bot.logger.error(f"Unable to delete temp file {tmp.name}", exc_info=e)



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
            except ValueError:
                raise CommandError(f"Invalid number: `{period}`")

            # Make sure period is valid
            if (period < 0.01):
                raise CommandError("The period cannot be less than 0.01 hours")

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
        except Exception as e:
            self.bot.logger.error(f"Unable to delete temp file {tmp.name}", exc_info=e)
