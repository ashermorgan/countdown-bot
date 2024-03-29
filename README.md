# countdown-bot
A Discord bot that facilitates countdowns and generates detailed countdown analytics



## Setup
1. Install the Python dependencies
    ```
    pip install -r requirements.txt
    ```

2. Go to the [Discord Developer Portal](https://discord.com/developers/) and create an application and a bot

3. Run `setup.py`
    ```
    python setup.py
    ```

4. Open `settings.json` (which was generated by `setup.py`) and add your bot's token
    ```json
    {"token": "YOUR_TOKEN_HERE", "prefixes": ["c."], "database": "sqlite:///data.sqlite3"}
    ```

5. Run the bot
    ```
    python run.py
    ```

6. Add the bot to your server
    ```
    https://discordapp.com/oauth2/authorize?client_id=BOT_ID_HERE&scope=bot&permissions=101440
    ```

7. Send `c.help` to the bot get a list of commands and a description of the bot's behavior
