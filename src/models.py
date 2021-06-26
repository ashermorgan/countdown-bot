# Import dependencies
from datetime import datetime, timedelta
import math
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base



# The rules for awarding leaderboard points
POINT_RULES = {
    "1000s": 1000,
    "1001s": 500,
    "200s": 200,
    "201s": 100,
    "100s": 100,
    "101s": 50,
    "Prime Numbers": 15,
    "Odd Numbers": 12,
    "Even Numbers": 10,
    "First Number": 0,
}



# Error classes
class MessageNotAllowedError(Exception):
    """Raised when someone posts twice in a row."""
    pass

class MessageIncorrectError(Exception):
    """Raised when someone posts an incorrect number."""
    pass



# Initialize declarative base
Base = declarative_base()



class Countdown(Base):
    """
    A Discord countdown

    Attributes
    ----------
    id : int
        The countdown's ID
    server_id : int
        The countdown's server's ID
    timezone : float
        The countdown's UTC offset (in hours)
    prefixes : list
        The countdown's command prefixes
    reactions : list
        The countdown's custom reactions
    messages : list
        The messages in the countdown
    """

    __tablename__ = "countdown"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer)
    timezone = Column(Float)
    prefixes = relationship("Prefix", back_populates="countdown", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="countdown", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="countdown", cascade="all, delete-orphan")

    def addMessage(self, message):
        """
        Add a message to the countdown

        Parameters
        ----------
        message : Message
            The message object

        Raises
        ------
        MessageNotAllowedError
            If the author posted the last message
        MessageIncorrectError
            If the message content is incorrect
        """

        if (len(self.messages) != 0 and message.author_id == self.messages[-1].author_id):
            raise MessageNotAllowedError()
        elif (len(self.messages) != 0 and message.number + 1 != self.messages[-1].number):
            raise MessageIncorrectError()
        else:
            self.messages += [message]

    def contributors(self):
        """
        Get countdown contributor statistics.

        Returns
        -------
        list
            A list of contributor statistics.
        """

        # Get contributors
        authors = list(set([x.author_id for x in self.messages]))

        # Get contributions
        contributors = []
        for author in authors:
            contributors += [{
                "author":author,
                "contributions":len([x for x in self.messages if x.author_id == author]),
            }]

        # Sort contributors by contributions
        contributors = sorted(contributors, key=lambda x: x["contributions"], reverse=True)

        # Return contributors
        return contributors

    def eta(self, period=timedelta(days=1)):
        """
        Get countdown eta statistics.

        Parameters
        ----------
        period : timedelta
            The period size. The default is 1 day.

        Returns
        -------
        list
            The countdown eta statistics.
        """

        # Make sure countdown has at least two messages
        if (len(self.messages) < 2):
            return [[], []]

        # Initialize period data
        periodEnd = self.messages[0].timestamp + timedelta(hours=self.timezone) + period
        lastMessage = 0

        # Initialize result and add first data point
        data = [[self.messages[0].timestamp + timedelta(hours=self.timezone)], [self.messages[0].timestamp + timedelta(hours=self.timezone)]]

        # Calculate timestamp for last data point
        if (self.messages[-1].number == 0):
            end = self.messages[-1].timestamp + timedelta(hours=self.timezone)
        else:
            end = datetime.utcnow() + timedelta(hours=self.timezone)

        # Add data points
        while (periodEnd < end):
            # Advance to last message in period
            while (lastMessage+1 < len(self.messages) and self.messages[lastMessage+1].timestamp + timedelta(hours=self.timezone) < periodEnd):
                lastMessage += 1

            # Calculate data
            rate = (self.messages[0].number - self.messages[lastMessage].number) / ((periodEnd - (self.messages[0].timestamp + timedelta(hours=self.timezone))) / timedelta(days=1))
            eta = periodEnd + timedelta(days=self.messages[lastMessage].number/rate)
            data[0] += [periodEnd]
            data[1] += [eta]

            # Advance to next period
            periodEnd += period

        # Add last data point
        data[0] += [end]
        data[1] += [self.progress()["eta"]]

        # Return eta data
        return data

    def leaderboard(self):
        """
        Get countdown leaderboard.

        Returns
        -------
        list
            The leaderboard.
        """

        if (len(self.messages) == 0):
            return []

        # Get list of prime numbers
        curTest = 5
        search = 1
        primes = [2, 3]
        while curTest < self.messages[0].number:
            if curTest%(primes[search]) == 0:
                curTest = curTest + 2
                search = 1
            else:
                if primes[search] > math.sqrt(curTest):
                    primes.append(curTest)
                    curTest = curTest + 2
                    search = 1
                else:
                    search = search + 1

        # Calculate contributor points
        points = {}
        for message in self.messages:
            if (message.author_id not in points):
                points[message.author_id] = {
                    "author": message.author_id,
                    "breakdown": {
                        "1000s": 0,
                        "1001s": 0,
                        "200s": 0,
                        "201s": 0,
                        "100s": 0,
                        "101s": 0,
                        "Prime Numbers": 0,
                        "Odd Numbers": 0,
                        "Even Numbers": 0,
                        "First Number": 0,
                    },
                }
            if (message.number == self.messages[0].number): points[message.author_id]["breakdown"]["First Number"] += 1
            elif (message.number % 1000 == 0):              points[message.author_id]["breakdown"]["1000s"] += 1
            elif (message.number % 1000 == 1):              points[message.author_id]["breakdown"]["1001s"] += 1
            elif (message.number % 200 == 0):               points[message.author_id]["breakdown"]["200s"] += 1
            elif (message.number % 200 == 1):               points[message.author_id]["breakdown"]["201s"] += 1
            elif (message.number % 100 == 0):               points[message.author_id]["breakdown"]["100s"] += 1
            elif (message.number % 100 == 1):               points[message.author_id]["breakdown"]["101s"] += 1
            elif (message.number in primes):                points[message.author_id]["breakdown"]["Prime Numbers"] += 1
            elif (message.number % 2 == 1):                 points[message.author_id]["breakdown"]["Odd Numbers"] += 1
            else:                                           points[message.author_id]["breakdown"]["Even Numbers"] += 1

        # Create ranked leaderboard
        leaderboard = []
        for contributor in points.values():
            contributor["contributions"] = sum(contributor["breakdown"].values())
            contributor["points"] = sum([contributor["breakdown"][x] * POINT_RULES[x] for x in contributor["breakdown"]])
            leaderboard += [contributor]
        leaderboard = sorted(leaderboard, key=lambda x: x["points"], reverse=True)
        return leaderboard

    def progress(self):
        """
        Get countdown progress statistics.

        Returns
        -------
        dict
            A dictionary containing countdown progress statistics.
        """

        # Get basic statistics
        if (len(self.messages) > 0):
            total = self.messages[0].number
            current = self.messages[-1].number
            percentage = (total - current) / total * 100
            start = self.messages[0].timestamp
        else:
            total = 0
            current = 0
            percentage = 0
            start = datetime.utcnow()

        # Get rate statistics
        if (len(self.messages) > 1 and self.messages[-1].number == 0):
            # The countdown has already finished
            rate = (total - current)/((self.messages[-1].timestamp - self.messages[0].timestamp) / timedelta(days=1))
            eta = self.messages[-1].timestamp
        elif (len(self.messages) > 1):
            # The countdown is still going
            rate = (total - current)/((datetime.utcnow() - self.messages[0].timestamp) / timedelta(days=1))
            eta = datetime.utcnow() + timedelta(days=current/rate)
        else:
            rate = 0
            eta = datetime.utcnow()

        # Get list of progress
        progress = [{"time":x.timestamp, "progress":x.number} for x in self.messages]

        # Return stats
        return {
            "total": total,
            "current": current,
            "percentage": percentage,
            "progress": progress,
            "start": start,
            "rate": rate,
            "eta": eta,
        }

    def speed(self, period=timedelta(days=1)):
        """
        Get countdown speed statistics.

        Parameters
        ----------
        periodLength : timedelta
            The period size. The default is 1 day.

        Returns
        -------
        list
            The countdown speed statistics.
        """

        # Calculate speed statistics
        data = [[], []]
        periodStart = datetime(2018, 1, 1) # Starts on Monday, Jan 1st
        for message in self.messages:
            # If data point isn't in the current period
            while (message.timestamp + timedelta(hours=self.timezone) - period >= periodStart):
                periodStart += period

            # Add new period if needed
            if (len(data[0]) == 0 or data[0][-1] != periodStart):
                data[0] += [periodStart]
                data[1] += [0]

            # Otherwise add the latest diff to the current period
            data[1][-1] += 1

        # Return speed statistics
        return data



class Prefix(Base):
    """
    A command prefix for a countdown

    Attributes
    ----------
    id : int
        The prefix's ID
    countdown_id : int
        The prefix's countdown's ID
    countdown : Countdown
        The prefix's countdown
    value : string
        The command prefix
    """
    
    __tablename__ = "prefix"

    id = Column(Integer, primary_key=True)
    countdown_id = Column(Integer, ForeignKey("countdown.id"))
    countdown = relationship("Countdown", back_populates="prefixes")
    value = Column(String)



class Reaction(Base):
    """
    A custom countdown reaction

    Attributes
    ----------
    id : int
        The reaction's ID
    countdown_id : int
        The prefix's countdown's ID
    countdown : Countdown
        The prefix's countdown
    number : int
        The number that the reaction applies to
    value : string
        The reaction
    """
    
    __tablename__ = "reaction"

    id = Column(Integer, primary_key=True)
    countdown_id = Column(Integer, ForeignKey("countdown.id"))
    countdown = relationship("Countdown", back_populates="reactions")
    number = Column(Integer)
    value = Column(String)



class Message(Base):
    """
    A countdown message

    Attributes
    ----------
    id : int
        The message's ID
    countdown_id : int
        The message's countdown's ID
    countdown : Countdown
        The message's countdown
    author_id : int
        The message's author's ID
    timestamp : datetime.datetime
        The message's timestamp
    number : int
        The message's number
    """

    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    countdown_id = Column(Integer, ForeignKey("countdown.id"))
    countdown = relationship("Countdown", back_populates="messages")
    author_id = Column(Integer)
    timestamp = Column(DateTime)
    number = Column(Integer)
