# Import dependencies
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker



# Load settings
settings = {}
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json"), "a+") as f:
    f.seek(0)
    settings = json.load(f)



# Connect to database and create tables
from src.models import Base
engine = create_engine(settings["database"])
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)



# Import bot so it can be easily imported from src
from src.bot import bot as countdownBot
