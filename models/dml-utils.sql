-- countdown-bot utility functions and procedures

DROP PROCEDURE IF EXISTS isCountdown;
DROP PROCEDURE IF EXISTS getUserContextCountdown;
DROP PROCEDURE IF EXISTS getServerContextCountdown;
DROP FUNCTION IF EXISTS getServerPrefixes;

-- Get the active prefixes for a server
CREATE FUNCTION getServerPrefixes (
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
