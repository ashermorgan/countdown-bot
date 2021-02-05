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

4. Add your bot to the countdown channel and copy the ID of the channel into a `channels.txt` file in the root directory. ex:
    ```
    <ID OF CHANNEL #1>
    <ID OF CHANNEL #2>
    ```

5. Run the bot
    ```
    python bot.py
    ```



## Behavior
- When a user posts out of turn the bot reacts to the message with ⛔.
- When a user posts an incorrect number the bot reacts to the message with ❌.
- When a user posts a number divisible by 200 the bot pins it.
- When a user posts 0 the bot reacts with 🥳.



## Commands
If a command is not run in a countdown channel, the bot will run it for the 1st countdown channel.

### contributors
**Description:** Shows information about countdown contributors

**Usage:** `!countdown contributors|c`


### help
**Description:** Shows help information

**Usage:** `!countdown help [command]`


### leaderboard
**Description:** Shows the countdown leaderboard

**Usage:** `!countdown leaderboard|l [user]`


### progress
**Description:** Shows information about countdown progress

**Usage:** `!countdown progress|p`


### speed
**Description:** Shows countdown speed statistics

**Usage:** `!countdown speed|s [hours=24.0]`


### reload
**Description:** Reloads the countdown cache

**Usage:** `!countdown reload`
