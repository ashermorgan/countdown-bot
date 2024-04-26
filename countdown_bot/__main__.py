# Import dependencies
from dotenv import load_dotenv
import logging
import os
import psycopg

# Import modules
from .bot import CountdownBot
from .models import getSessionMaker

# Load settings
load_dotenv()

# Setup logging
logger = logging.getLogger()
logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO")))
logging.basicConfig(
    format = "[{asctime}] [{levelname:<8}] {name}: {message}",
    style="{",
    filename = os.environ.get("LOG_FILE", "log.txt"),
)

# Connect to database
databaseSessionMaker = getSessionMaker(os.environ.get("DATABASE"))
db_connection = psycopg.connect(os.environ.get("DATABASE2"), row_factory=psycopg.rows.dict_row)

# Run bot
bot = CountdownBot(databaseSessionMaker, [os.environ.get("PREFIX", "!")], db_connection)
bot.run(os.environ.get("TOKEN"))
