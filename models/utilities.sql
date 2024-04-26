-- countdown-bot utility procedures

DROP PROCEDURE IF EXISTS setReactions;
DROP FUNCTION IF EXISTS getReactions;
DROP PROCEDURE IF EXISTS addMessage;
DROP TYPE IF EXISTS addMessageResults;
DROP PROCEDURE IF EXISTS deleteCountdown;
DROP PROCEDURE IF EXISTS createCountdown;
DROP PROCEDURE IF EXISTS clearCountdown;
DROP PROCEDURE IF EXISTS isCountdown;
DROP PROCEDURE IF EXISTS getUserContextCountdown;
DROP PROCEDURE IF EXISTS getServerContextCountdown;
DROP PROCEDURE IF EXISTS setPrefixes;
DROP FUNCTION IF EXISTS getPrefixes;

-- Get the active prefixes for a server
CREATE FUNCTION getPrefixes (
    _serverID BIGINT, -- The server ID
    channelID BIGINT  -- The channel ID
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

-- Set the command prefixes used by a countdown channel
CREATE PROCEDURE setPrefixes (
    _countdownID BIGINT,   -- The countdown channel ID
    _prefixes VARCHAR(8)[] -- The prefix values
)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM prefixes
    WHERE countdownID = _countdownID;

    INSERT INTO prefixes (countdownID, value)
    SELECT _countdownID, *
    FROM unnest(_prefixes);
END
$$;

-- Get the most relevant countdown to a server channel
CREATE PROCEDURE getServerContextCountdown (
    _serverID IN BIGINT,   -- The server ID
    channelID IN BIGINT,   -- The channel ID
    prefix IN VARCHAR(8),  -- The prefix used to invoke the bot
    countdownID OUT BIGINT -- The ID of the most relevant countdown
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
    _userID IN BIGINT,     -- The user ID
    countdownID OUT BIGINT -- The ID of the most relevant countdown
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

-- Determine if a channel is a countdown
CREATE PROCEDURE isCountdown (
    channelID IN BIGINT, -- The channel ID
    result OUT BOOLEAN   -- Whether the channel is a countdown
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM countdowns
        WHERE countdownID = channelID
    ) INTO result;
END
$$;

-- Delete all messages in a countdown
CREATE PROCEDURE clearCountdown (
    _countdownID IN BIGINT -- The countdown channel ID
)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE
    FROM messages
    WHERE countdownID = _countdownID;
END
$$;

-- Create a new countdown
CREATE PROCEDURE createCountdown (
    _countdownID IN BIGINT, -- The countdown channel ID
    _serverID IN BIGINT,    -- The server ID
    prefix IN VARCHAR(8)    -- The initial prefix
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO countdowns (countdownID, serverID)
    VALUES (_countdownID, _serverID);
    INSERT INTO prefixes (countdownID, value)
    VALUES (_countdownID, prefix);
END
$$;

-- Delete a countdown
CREATE PROCEDURE deleteCountdown (
    _countdownID IN BIGINT -- The countdown channel ID
)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE
    FROM countdowns
    WHERE countdownID = _countdownID;
END
$$;

-- Possible results of the addMessage procedure
CREATE TYPE addMessageResults AS ENUM (
    'badCountdown', -- Countdown doesn't exist or has ended
    'badNumber',    -- Message number is incorrect
    'badUser',      -- User sent consecutive messages
    'good'          -- Message was successfully added
);

-- Validate and add a new countdown message
CREATE PROCEDURE addMessage (
    _messageID IN BIGINT,         -- The message ID
    _countdownID IN BIGINT,       -- The message countdown ID
    _userID IN BIGINT,            -- The message user ID
    _value IN INT,                -- The message value
    _timestamp IN TIMESTAMPTZ,    -- The message timestamp
    result OUT addMessageResults, -- The operation result
    pin OUT BOOLEAN,              -- Whether the message should be pinned
    reactions OUT BOOLEAN         -- Whether the message has custom reactions
)
LANGUAGE plpgsql AS $$
DECLARE
    lastMessage record;
    total INT;
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

    -- Initialize pin and reactions
    pin := FALSE;
    reactions := FALSE;

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

        -- Get total from first message
        SELECT value
        INTO total
        FROM messages
        WHERE countdownID = _countdownID
        ORDER BY timestamp ASC
        LIMIT 1;

        -- Check if message should be pinned
        IF total >= 500 AND _value % (total / 50) = 0 AND _value != 0 THEN
            pin := TRUE;
        END IF;

        -- Check if message has custom reactions
        IF EXISTS(SELECT 1 FROM reactions
            WHERE countdownID = _countdownID AND number = _value
        ) THEN
            reactions := TRUE;
        END IF;
    END IF;
END
$$;

-- Get the custom reactions for a number in a countdown
CREATE FUNCTION getReactions (
    _countdownID BIGINT, -- The countdown channel ID
    _number INT          -- The number (or NULL for all numbers)
)
RETURNS TABLE (
    value VARCHAR(8), -- A custom reaction
    number INT        -- The number
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT reactions.value, reactions.number
    FROM reactions
    WHERE countdownID = _countdownID
        AND (reactions.number = _number OR _number IS NULL)
    ORDER BY reactions.number DESC;
END
$$;

-- Set the custom reactions for a number in a countdown
CREATE PROCEDURE setReactions (
    _countdownID BIGINT,    -- The countdown channel ID
    _number INT,            -- The number
    _reactions VARCHAR(8)[] -- The custom reactions
)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM reactions
    WHERE countdownID = _countdownID AND number = _number;

    INSERT INTO reactions (countdownID, number, value)
    SELECT _countdownID, _number, *
    FROM unnest(_reactions);
END
$$;
