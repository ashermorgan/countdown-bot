-- countdown-bot core functions and procedures

DROP PROCEDURE IF EXISTS setTimezone;
DROP PROCEDURE IF EXISTS getTimezone;
DROP PROCEDURE IF EXISTS setReactions;
DROP FUNCTION IF EXISTS getReactions;
DROP PROCEDURE IF EXISTS addMessage;
DROP TYPE IF EXISTS addMessageResults;
DROP PROCEDURE IF EXISTS deleteCountdown;
DROP PROCEDURE IF EXISTS createCountdown;
DROP PROCEDURE IF EXISTS clearCountdown;
DROP PROCEDURE IF EXISTS setPrefixes;
DROP FUNCTION IF EXISTS getPrefixes;

-- Get the active prefixes for a countdown channel
CREATE FUNCTION getPrefixes (
    _countdownID BIGINT -- The countdown channel ID
)
RETURNS TABLE (
    prefix VARCHAR(8) -- An active prefix
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT value
    FROM prefixes
    WHERE prefixes.countdownID = _countdownID;
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

-- Get the timezone of a countdown
CREATE PROCEDURE getTimezone (
    _countdownID IN BIGINT, -- The countdown channel ID
    _timezone OUT INTERVAL  -- The timezone as a UTC offest
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT timezone
    INTO _timezone
    FROM countdowns
    WHERE countdownID = _countdownID;
END
$$;

-- Set the timezone of a countdown
CREATE PROCEDURE setTimezone (
    _countdownID IN BIGINT, -- The countdown channel ID
    _timezone IN INTERVAL   -- The timezone as a UTC offest
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE countdowns
    SET timezone = _timezone
    WHERE countdownID = _countdownID;
END
$$;
