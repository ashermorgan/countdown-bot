# countdown-bot
A Discord bot that facilitates countdowns and generates detailed countdown analytics



## Setup
Install the Python dependencies
```
pip install -r requirements.txt
```

Go to the [Discord Developer Portal](https://discord.com/developers/) and create an application and a bot

Create `.env` file and add settings:
```
TOKEN=...
PREFIX=!
DATABASE=postgresql://...
LOG_FILE=log.txt
LOG_LEVEL=INFO
```

Initialize the PostgreSQL database
```
psql 'postgresql://...' -f models/ddl.sql -f models/dml-utils.sql -f models/dml-core.sql -f models/dml-analytics.sql
```

Run the bot
```
python -m countdown_bot
```

Add the bot to your server
```
https://discordapp.com/oauth2/authorize?client_id=BOT_ID_HERE&scope=bot&permissions=101440
```

Send `!help` to the bot get a list of commands and a description of the bot's behavior
