# Import dependencies
from dotenv import load_dotenv
import logging
import os
import psycopg

# Import modules
from .bot import CountdownBot

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
db_connection = psycopg.connect(os.environ.get("DATABASE"), row_factory=psycopg.rows.dict_row)

# Run bot
bot = CountdownBot(db_connection, [os.environ.get("PREFIX", "!")])
bot.run(os.environ.get("TOKEN"))
