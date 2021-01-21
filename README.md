# countdown-bot
A Discord bot to facilitate countdowns.

# Setup
1. Install the Python dependencies
    ```
    pip install -r requirements.txt
    ```

2. Go to the [Discord Developer Portal](https://discord.com/developers/) and create an application and a bot.

3. Copy your bot's token into a `.env` file in the root directory. ex:
    ```
    DISCORD_TOKEN="YOUR_DISCORD_TOKEN_HERE"
    ```

4. Add your bot to the countdown channel and copy the ID of the channel into a `channels.txt` file in the root directory. ex:
    ```
    <ID OF CHANNEL #1>
    <ID OF CHANNEL #2>
    ```

5. Run the bot
    ```
    python bot.py
    ```
