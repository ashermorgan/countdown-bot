# Import dependencies
from datetime import datetime, timedelta
import math
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base



Base = declarative_base()



def getSessionMaker(location):
    """
    Create a sessionmaker from a database URI

    Parameters
    ----------
    location : str
        The location of the database
    """

    engine = create_engine(location)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)



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
class EmptyCountdownError(Exception):
    """Raised when an action cannot be completed because the countdown is empty."""
    pass

class MessageNotAllowedError(Exception):
    """Raised when someone posts twice in a row."""
    pass

class MessageIncorrectError(Exception):
    """Raised when someone posts an incorrect number."""
    pass



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

    def getTimezone(self):
        """
        Get the timezone as a string

        Returns
        -------
        str
            The timezone string
        """

        # Get tiemzone
        if (self.timezone >= 0): result = f"UTC+{self.timezone}"
        else: result = f"UTC-{abs(self.timezone)}"

        # Remove ".0" from the end
        if (self.timezone % 1 == 0): result = result[:-2]

        # Return timezone string
        return result

    def contributors(self):
        """
        Get countdown contributor statistics.

        Returns
        -------
        list
            A list of contributor statistics.
        """

        # Make sure countdown has started
        if (len(self.messages) == 0):
            raise EmptyCountdownError()

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
        if (len(self.messages) == 0):
            raise EmptyCountdownError()

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

    def heatmap(self, user=None):
        """
        Get a heatmap of when countdown messages are sent

        Parameters
        ----------
        user : int
            The ID of the specific user to generate the heatmap for (the default is None)

        Returns
        -------
        list
            A 7x24 2D array containing the heatmap
        """

        # Make sure countdown has started
        if (len(self.messages) == 0):
            raise EmptyCountdownError()

        # Initialize result matrix
        result = [[0 for i in range(24)] for j in range(7)]

        for message in self.messages:
            if (user != None and message.author_id != user): continue

            # Apply timezone offset
            timestamp = message.timestamp + timedelta(hours=self.timezone)

            # Get time and weekday
            dayOfWeek = timestamp.weekday()  # 0-6, 0=Monday
            timeOfDay = timestamp.hour  # 0-23

            # Make Sunday the first day of the week
            dayOfWeek = (dayOfWeek + 1) % 7

            # Add data to result matrix
            result[dayOfWeek][timeOfDay] += 1

        # Return result matrix
        return result

    def leaderboard(self):
        """
        Get countdown leaderboard.

        Returns
        -------
        list
            The leaderboard.
        """

        # Make sure countdown has started
        if (len(self.messages) == 0):
            raise EmptyCountdownError()

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

        # Make sure countdown has started
        if (len(self.messages) == 0):
            raise EmptyCountdownError()

        # Get basic statistics
        total = self.messages[0].number
        current = self.messages[-1].number
        percentage = (total - current) / total * 100
        start = self.messages[0].timestamp

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

        # Make sure countdown has started
        if (len(self.messages) == 0):
            raise EmptyCountdownError()

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
