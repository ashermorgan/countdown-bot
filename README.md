# countdown-bot
A Discord bot that facilitates countdowns and generates detailed countdown analytics



## Setup
1. Install the Python dependencies
    ```
    pip install -r requirements.txt
    ```

2. Go to the [Discord Developer Portal](https://discord.com/developers/) and create an application and a bot

3. Create `.env` file and add settings:
    ```
    TOKEN=...
    PREFIX=!
    DATABASE=sqlite:///data.sqlite3
    LOG_FILE=log.txt
    LOG_LEVEL=INFO
    ```

4. Run the bot
    ```
    python -m countdown_bot
    ```

5. Add the bot to your server
    ```
    https://discordapp.com/oauth2/authorize?client_id=BOT_ID_HERE&scope=bot&permissions=101440
    ```

6. Send `!help` to the bot get a list of commands and a description of the bot's behavior
