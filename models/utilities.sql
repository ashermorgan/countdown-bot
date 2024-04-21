-- countdown-bot utility procedures

DROP PROCEDURE IF EXISTS getUserContextCountdown;
DROP PROCEDURE IF EXISTS getServerContextCountdown;
DROP FUNCTION IF EXISTS getPrefixes;
DROP PROCEDURE IF EXISTS addMessage;
DROP TYPE IF EXISTS addMessageResults;

-- Possible results of the addMessage procedure
CREATE TYPE addMessageResults AS ENUM (
    'badCountdown', -- Countdown doesn't exist or has ended
    'badNumber',    -- Message number is incorrect
    'badUser',      -- User sent consecutive messages
    'good'          -- Message was successfully added
);

-- Validate and add a new countdown message
CREATE PROCEDURE addMessage (
    _messageID IN INT,           -- The message ID
    _countdownID IN INT,         -- The message countdown ID
    _userID IN INT,              -- The message user ID
    _value IN INT,               -- The message value
    _timestamp IN TIMESTAMPTZ,   -- The message timestamp
    result OUT addMessageResults -- The operation result
)
LANGUAGE plpgsql AS $$
DECLARE
    lastMessage record;
BEGIN
    -- Get last countdown message
    SELECT countdowns.countdownID, messageID, userID, value, timestamp
    INTO lastMessage
    FROM countdowns

    -- Still return a row if the countdown is empty
    LEFT OUTER JOIN messages
        ON messages.countdownID = countdowns.countdownID

    WHERE countdowns.countdownID = _countdownID
    ORDER BY messages.value ASC
    LIMIT 1;

    -- Validate message
    IF lastMessage.countdownID IS NULL OR lastMessage.value = 0 THEN
        -- Countdown doesn't exist or has ended
        result := 'badCountdown';

    ELSEIF lastMessage.value IS NOT NULL AND
        lastMessage.value != _value + 1 THEN
        -- Message contains the wrong number
        result := 'badNumber';

    ELSEIF lastMessage.userID = _userID THEN
        -- User sent consecutive messages
        result := 'badUser';

    ELSE
        -- Message is valid, insert it into messages
        INSERT INTO messages (messageID, userID, countdownID, value, timestamp)
            VALUES (_messageID, _userID, _countdownID, _value, _timestamp);
        result := 'good';
    END IF;
END
$$;

-- Get the active prefixes for a server
CREATE FUNCTION getPrefixes (
    _serverID IN INT, -- The server ID
    channelID IN INT  -- The channel ID
)
RETURNS TABLE (
    prefix VARCHAR(8) -- An active prefix
)
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS(
        SELECT 1
        FROM countdowns
        WHERE countdownID = channelID
    ) THEN
        -- Filter prefixes if channel is a countdown
        RETURN QUERY
        SELECT value
        FROM prefixes
        WHERE prefixes.countdownID = channelID;
    ELSE
        -- Return all server prefixes if channel is not a countdown
        RETURN QUERY
        SELECT DISTINCT value
        FROM prefixes
        JOIN countdowns ON countdowns.countdownID = prefixes.countdownID
        WHERE countdowns.serverID = _serverID;
    END IF;
END
$$;

-- Get the most relevant countdown to a server channel
CREATE PROCEDURE getServerContextCountdown (
    _serverID IN INT,     -- The server ID
    channelID IN INT,     -- The channel ID
    prefix IN VARCHAR(8), -- The prefix used to invoke the bot
    countdownID OUT INT   -- The ID of the most relevant countdown
)
LANGUAGE plpgsql AS $$
BEGIN
    -- Check if the channel is a countdown
    SELECT countdowns.countdownID
    INTO countdownID
    FROM countdowns
    WHERE countdowns.countdownID = channelID

    UNION ALL
    (
        -- Get server countdowns by prefix sorted by most recent activity
        SELECT countdowns.countdownID
        FROM countdowns
        LEFT OUTER JOIN messages
            ON messages.countdownID = countdowns.countdownID
        JOIN prefixes
            ON prefixes.countdownID = countdowns.countdownID
        WHERE serverID = _serverID AND prefixes.value = prefix
        GROUP BY countdowns.countdownID
        ORDER BY max(messages.timestamp) DESC NULLS LAST
    )
    LIMIT 1;
END
$$;

-- Get the most relevant countdown to a user
CREATE PROCEDURE getUserContextCountdown (
    _userID IN INT,     -- The user ID
    countdownID OUT INT -- The ID of the most relevant countdown
)
LANGUAGE plpgsql AS $$
BEGIN
    -- Get user countdowns sorted by most recent activity
    SELECT countdowns.countdownID
    INTO countdownID
    FROM countdowns
    LEFT OUTER JOIN messages ON messages.countdownID = countdowns.countdownID
    WHERE userID = _userID
    GROUP BY countdowns.countdownID
    ORDER BY max(messages.timestamp) DESC NULLS LAST
    LIMIT 1;
END
$$;
