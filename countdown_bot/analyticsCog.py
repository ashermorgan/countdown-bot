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
from .botUtilities import COLORS, POINT_RULES, CommandError, CountdownNotFound, getUsername, getContributor, getContextCountdown



class Analytics(commands.Cog):
    def __init__(self, bot, db_connection):
        self.bot = bot
        self.db_connection = db_connection



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

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)
            if not countdown:
                raise CountdownNotFound()

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
                cur.execute("SELECT * FROM contributorData(%s);", (countdown,))
                contributors = [x["userid"] for x in cur.fetchall()]
                cur.execute("SELECT * FROM historicalContributorData(%s);", (countdown,))
                data = cur.fetchall()

                if not data:
                    raise CommandError("The countdown doesn't have enough messages yet")

                # Plot data and add legend
                for author in contributors[:15]:
                    # Top 15 contributors get included in the legend
                    ax.plot([x["progress"] for x in data if x["userid"] == author], [x["percentage"] for x in data if x["userid"] == author], label=await getUsername(self.bot, author))
                for author in contributors[15:]:
                    ax.plot([x["progress"] for x in data if x["userid"] == author], [x["percentage"] for x in data if x["userid"] == author])
                ax.legend(bbox_to_anchor=(1,1.025), loc="upper left")

                # Save graph
                fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                file = discord.File(tmp.name, filename="image.png")

                # Add content to embed
                embed.description = f"**Countdown Channel:** <#{countdown}>"
                embed.set_image(url="attachment://image.png")
            elif (option == ""):
                # Create figure
                fig, ax = plt.subplots()

                # Get stats
                cur.execute("SELECT * FROM contributorData(%s);", (countdown,))
                data = cur.fetchall()

                if not data:
                    raise CommandError("The countdown doesn't have enough messages yet")

                # Add data to graph
                pieData = ax.pie([x["contributions"] for x in data], autopct="%1.1f%%", startangle=90)

                # Add legend
                ax.legend(pieData[0], [await getUsername(self.bot, x["userid"]) for x in
                    data[:15]], bbox_to_anchor=(1,1.025), loc="upper left")

                # Save graph
                fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
                file = discord.File(tmp.name, filename="image.png")

                # Add content to embed
                embed.description = f"**Countdown Channel:** <#{countdown}>"
                ranksColumn = ""
                usersColumn = ""
                contributionsColumn = ""
                for i in range(0, min(len(data), 20)):
                    ranksColumn += f"{i+1:,}\n"
                    contributionsColumn += f"{data[i]['contributions']:,} *({data[i]['percentage']:.1f}%)*\n"
                    usersColumn += f"<@{data[i]['userid']}>\n"
                embed.add_field(name="Rank", value=ranksColumn, inline=True)
                embed.add_field(name="User", value=usersColumn, inline=True)
                embed.add_field(name="Contributions", value=contributionsColumn, inline=True)
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
    async def eta(self, ctx):
        """
        Shows information about the estimated completion date
        """

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)
            if not countdown:
                raise CountdownNotFound()

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":calendar: Countdown Estimated Completion Date", color=COLORS["embed"])

            # Get stats
            cur.execute("CALL progressStats(%s,null,null,null,null,null,null,null,null,null,null,null,null);", (countdown,))
            stats = cur.fetchone()
            cur.execute("SELECT * FROM etaData(%s);", (countdown,))
            data = cur.fetchall()

            if not data:
                raise CommandError("The countdown doesn't have enough messages yet")

            # Create figure
            fig, ax = plt.subplots()
            ax.set_xlabel("Time")
            fig.autofmt_xdate()

            # Add ETA data to graph
            ax.plot([x["_timestamp"] for x in data], [x["eta"] for x in data], "C0", label="Estimated Completion Date")

            # Add reference line graph
            ax.plot([data[0]["_timestamp"], data[-1]["_timestamp"]], [data[0]["_timestamp"], data[-1]["_timestamp"]], "--C1", label="Current Date")

            # Add legend
            ax.legend()

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Calculate embed data
            maxEta = max([x["eta"] for x in data])
            maxDate = [x["_timestamp"] for x in data if x["eta"] == maxEta][0]
            minEta = min([x["eta"] for x in data])
            minDate = [x["_timestamp"] for x in data if x["eta"] == minEta][0]

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{countdown}>\n\n"
            embed.description += f"**Maximum Estimate:** {maxEta.date()} (on {maxDate.date()})\n"
            embed.description += f"**Minimum Estimate:** {minEta.date()} (on {minDate.date()})\n"
            if stats['endage'] > timedelta(seconds=0):
                embed.description += f"**Actual Completion Date:** {stats['endtime'].date()} ({stats['endage'].days:,} days ago)\n"
            else:
                embed.description += f"**Current Estimate:** {stats['endtime'].date()} ({(-1 * stats['endage']).days:,} days from now)\n"
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

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)
            if not countdown:
                raise CountdownNotFound()

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

            # Get heatmap data
            cur.execute("CALL heatmapStats(%s, null, null);",
                (countdown,))
            stats = cur.fetchone()
            cur.execute("SELECT * FROM heatmapData(%s, %s);",
                (countdown, userID))
            data = cur.fetchall()

            if not data:
                print(countdown, userID, data)
                raise CommandError("The countdown doesn't have enough messages yet")

            # Create heatmap matrix
            matrix = [[0 for i in range(24)] for j in range(7)]
            for row in data:
                matrix[int(row["dow"])][int(row["hour"])] = row["messages"]

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
            cax = ax.matshow(np.ma.masked_equal(np.array(matrix), 0), cmap=cmap, aspect="auto")
            fig.colorbar(cax)

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Get embed data
            total = np.sum(matrix)
            averageValue = total / (24*7)
            maxValue = np.max(matrix)
            maxWeekday = np.where(matrix == maxValue)[0][0]
            maxHour = np.where(matrix == maxValue)[1][0]
            currentWeekday = int(stats['curdow'])
            currentHour = int(stats['curhour'])
            currentValue = matrix[currentWeekday][currentHour]

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{countdown}>\n\n"
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

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)
            if not countdown:
                raise CountdownNotFound()

            # Create embed
            embed=discord.Embed(title=":trophy: Countdown Leaderboard", color=COLORS["embed"])

            # Get user
            if (user == None):
                userID = None
            else:
                userID = await getContributor(self.bot, countdown, user)

            # Get leaderboard
            cur.execute("SELECT * FROM leaderboardData(%s, %s);",
                (countdown, userID))
            data = cur.fetchall()

            if not data:
                raise CommandError("The countdown doesn't have enough messages yet")

            if (user is None):
                # Add description
                embed.description = f"**Countdown Channel:** <#{countdown}>"

                # Add leaderboard
                ranks = ""
                points = ""
                users = ""
                for row in data[:20]:
                    ranks += f"{row['ranking']:,}\n"
                    points += f"{row['total']:,}\n"
                    users += f"<@{row['userid']}>\n"
                embed.add_field(name="Rank",value=ranks, inline=True)
                embed.add_field(name="Points",value=points, inline=True)
                embed.add_field(name="User",value=users, inline=True)

                # Add leaderboard rules
                rules = ""
                values = ""
                for rule in POINT_RULES:
                    rules += f"{POINT_RULES[rule][0]}\n"
                    values += f"{POINT_RULES[rule][1]} points\n"
                embed.add_field(name="Rules", value="Only 1 rule is applied towards each number", inline=False)
                embed.add_field(name="Numbers", value=rules, inline=True)
                embed.add_field(name="Points", value=values, inline=True)
            else:
                # Add description
                embed.description = f"**Countdown Channel:** <#{countdown}>\n\n"
                embed.description += f"**User:** <@{data[0]['userid']}>\n"
                embed.description += f"**Rank:** #{data[0]['ranking']:,}\n"
                embed.description += f"**Total Points:** {data[0]['total']:,}\n"
                embed.description += f"**Total Contributions:** {data[0]['contributions']:,} *({round(data[0]['percentage'])}%)*\n"

                # Add points breakdown
                rules = ""
                points = ""
                percentage = ""
                for rule in POINT_RULES:
                    rules += f"{POINT_RULES[rule][0]}\n"
                    points += f"{data[0][rule] * POINT_RULES[rule][1]:,} *({data[0][rule]:,})*\n"
                    if (data[0]['total'] > 0):
                        percentage += f"{round(data[0][rule] * POINT_RULES[rule][1] / data[0]['total'] * 100, 1)}%\n"
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

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)
            if not countdown:
                raise CountdownNotFound()

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":chart_with_downwards_trend: Countdown Progress", color=COLORS["embed"])

            # Get progress stats
            cur.execute("SELECT * FROM progressData(%s);", (countdown,))
            data = cur.fetchall()
            cur.execute("CALL progressStats(%s,null,null,null,null,null,null,null,null,null,null,null,null);", (countdown,))
            stats = cur.fetchone()

            if not data:
                raise CommandError("The countdown doesn't have enough messages yet")

            # Create figure
            fig, ax = plt.subplots()
            ax.set_xlabel("Time")
            ax.set_ylabel("Progress")
            fig.autofmt_xdate()

            # Add data to graph
            x = [data[0]["_timestamp"]] + [x["_timestamp"] for x in data]
            y = [0] + [x["progress"] for x in data]
            ax.plot(x, y)

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Calculate embed data
            longestBreakDuration = timedelta(days=stats["longestbreak"].days, seconds=stats["longestbreak"].seconds)
            longestBreakStart = stats["longestbreakstart"].date()
            longestBreakEnd = stats["longestbreakend"].date()

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{countdown}>\n\n"
            embed.description += f"**Progress:** {stats['progress']:,} / {stats['total']:,} ({stats['percentage']:.1f}%)\n"
            embed.description += f"**Average Progress per Day:** {stats['rate']:,.0f}\n"
            embed.description += f"**Longest Break:** {longestBreakDuration} ({stats['longestbreakstart'].date()} to {stats['longestbreakend'].date()})\n"
            embed.description += f"**Start Date:** {stats['starttime'].date()} ({stats['startage'].days:,} days ago)\n"
            if stats['endage'] > timedelta(seconds=0):
                embed.description += f"**End Date:** {stats['endtime'].date()} ({stats['endage'].days:,} days ago)\n"
            else:
                embed.description += f"**Estimated End Date:** {stats['endtime'].date()} ({(-1 * stats['endage']).days:,} days from now)\n"
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
    async def speed(self, ctx, period="24"):
        """
        Shows information about countdown speed
        """

        with self.db_connection.cursor() as cur:
            # Get countdown channel
            countdown = getContextCountdown(cur, ctx)
            if not countdown:
                raise CountdownNotFound()

            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()

            # Create embed
            embed=discord.Embed(title=":stopwatch: Countdown Speed", color=COLORS["embed"])

            # Parse period
            try:
                period = int(period)
            except ValueError:
                raise CommandError(f"Invalid number: `{period}`")

            # Get data
            cur.execute("SELECT * FROM speedData(%s, %s);", (countdown, period))
            data = cur.fetchall()

            if not data:
                raise CommandError("The countdown doesn't have enough messages yet")

            # Create figure
            fig, ax = plt.subplots()
            ax.set_xlabel("Time")
            ax.set_ylabel("Progress per Period")
            fig.autofmt_xdate()

            # Add data to graph
            period = timedelta(hours=period)
            for row in data:
                ax.bar(row["periodstart"], row["messages"], width=period, align="edge", color="#1f77b4")

            # Save graph
            fig.savefig(tmp.name, bbox_inches="tight", pad_inches=0.2)
            file = discord.File(tmp.name, filename="image.png")

            # Calculate embed data
            maxSpeed = max([x["messages"] for x in data])
            avgSpeed = round(sum([x["messages"] for x in data]) / len(data))
            curSpeed = data[-1]["messages"]
            curPeriod = data[-1]["periodstart"]

            # Add content to embed
            embed.description = f"**Countdown Channel:** <#{countdown}>\n\n"
            embed.description += f"**Period Size:** {period}\n"
            embed.description += f"**Average Progress per Period:** {avgSpeed:,}\n"
            embed.description += f"**Record Progress per Period:** {maxSpeed:,}\n"
            embed.description += f"**Last Period Start:** {curPeriod}\n"
            embed.description += f"**Progress during Last Period:** {curSpeed:,}\n"
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
