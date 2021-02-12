# countdown-bot
A Discord bot to facilitate countdowns.



## Setup
1. Install the Python dependencies
    ```
    pip install -r requirements.txt
    ```

2. Go to the [Discord Developer Portal](https://discord.com/developers/) and create an application and a bot.

3. Copy your bot's token into a `.env` file in the root directory. ex:
    ```
    DISCORD_TOKEN="YOUR_DISCORD_TOKEN_HERE"
    ```

4. Add the bot to your server.
    ```
    https://discordapp.com/oauth2/authorize?client_id=BOT_ID_HERE&scope=bot&permissions=232512
    ```

5. Copy the ID of each countdown channel into a `channels.txt` file in the root directory. ex:
    ```
    <ID OF CHANNEL #1>
    <ID OF CHANNEL #2>
    ```

6. Run the bot
    ```
    python bot.py
    ```

7. Run `c.help` to get a list of commands and a description of the bot's behavior.
