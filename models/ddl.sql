DROP FUNCTION IF EXISTS speedData;
DROP PROCEDURE IF EXISTS progressStats;
DROP FUNCTION IF EXISTS progressData;
DROP FUNCTION IF EXISTS leaderboardData;
DROP FUNCTION IF EXISTS historicalContributorData;
DROP FUNCTION IF EXISTS heatmapData;
DROP FUNCTION IF EXISTS etaData;
DROP FUNCTION IF EXISTS contributorData;
DROP PROCEDURE IF EXISTS addMessage;
DROP TYPE IF EXISTS addMessageResults;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS countdowns;

CREATE TABLE countdowns (
    countdownID INT PRIMARY KEY, -- Discord channel ID
    serverID INT NOT NULL
);

CREATE TABLE messages (
    messageID INT PRIMARY KEY, -- Discord message ID
    countdownID INT REFERENCES countdowns(countdownID),
    userID INT NOT NULL, -- Discord user ID
    value INT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE TYPE addMessageResults AS ENUM (
    'badCountdown', 'badNumber', 'badUser', 'good'
);

-- Validate and add a new countdown message
CREATE PROCEDURE addMessage
    (_messageID IN INT, _countdownID IN INT, _userID IN INT, _value IN INT,
    _timestamp IN TIMESTAMPTZ, result OUT addMessageResults)
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
        INSERT INTO messages
            (messageID, userID, countdownID, value, timestamp)
            VALUES (_messageID, _userID, _countdownID, _value, _timestamp);
        result := 'good';
    END IF;
END
$$;

CREATE FUNCTION contributorData (_countdownID INT)
RETURNS TABLE (ranking BIGINT, userID INT, contributions BIGINT,
    percentage FLOAT)
LANGUAGE plpgsql AS $$
DECLARE
    progress INT;
BEGIN
    -- Get total from first message
    SELECT count(messageID)
        INTO progress
        FROM messages
        WHERE countdownID = _countdownID;

    RETURN QUERY
    SELECT
        rank() OVER (ORDER BY count(messageID) DESC) AS ranking,
        messages.userID,
        count(messageID) AS contributions,
        (100.0 * count(messageID) / progress)::float AS percentage
    FROM messages
    WHERE countdownID = _countdownID
    GROUP BY messages.userID;
END
$$;

CREATE FUNCTION etaData (_countdownID INT)
RETURNS TABLE (_timestamp TIMESTAMPTZ, eta TIMESTAMPTZ)
LANGUAGE plpgsql AS $$
DECLARE
    total INT;
    startTime INT;
BEGIN
    -- Get startTime and total from first message
    SELECT value, extract(epoch FROM timestamp)
        INTO total, startTime
        FROM messages
        WHERE countdownID = _countdownID
        ORDER BY timestamp ASC
        LIMIT 1;

    -- Calculate eta for each message
    RETURN QUERY
    SELECT timestamp, to_timestamp(startTime + value *
        (extract(epoch FROM timestamp) - startTime) / (total - value))
    FROM messages
    WHERE countdownID = _countdownID
        AND extract(epoch FROM timestamp) != startTime
    ORDER BY messageID;
END
$$;

CREATE FUNCTION heatmapData (_countdownID INT, _userID INT)
RETURNS TABLE (dow NUMERIC, hour NUMERIC, messages BIGINT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT extract(dow FROM timestamp) AS dow,
        extract(hour FROM timestamp) AS hour, count(messageID) as messages
        FROM messages
        WHERE countdownID = _countdownID
            AND (userID = _userID OR _userID IS NULL)
        GROUP BY dow, hour;
END
$$;

CREATE FUNCTION historicalContributorData (_countdownID INT)
RETURNS TABLE (progress INT, userID INT, percentage FLOAT)
LANGUAGE plpgsql AS $$
DECLARE
    total INT;
BEGIN
    -- Get total from first message
    SELECT value
        INTO total
        FROM messages
        WHERE countdownID = _countdownID
        ORDER BY timestamp ASC
        LIMIT 1;

    -- Calculator percentage for each user for each message
    RETURN QUERY
    SELECT (total - value) AS progress, users.userID,
        (
            sum(CASE messages.userID WHEN users.userID THEN 1 ELSE 0 END)
            OVER (PARTITION BY users.userID ORDER BY timestamp)
        )::float / (total - value + 1)
        FROM messages, (
            SELECT DISTINCT messages.userID
            FROM messages
            WHERE countdownID = _countdownID
        ) users
        WHERE countdownID = _countdownID;
END
$$;

CREATE FUNCTION leaderboardData (_countdownID INT, _userID INT)
RETURNS TABLE (ranking BIGINT, userID INT, total BIGINT, contributions BIGINT,
    percentage FLOAT, r1 BIGINT, r2 BIGINT, r3 BIGINT, r4 BIGINT, r5 BIGINT,
    r6 BIGINT, r7 BIGINT, r8 BIGINT, r9 BIGINT)
LANGUAGE plpgsql AS $$
DECLARE
    total INT;
    progress INT;
BEGIN
    -- Get total from first message
    SELECT value
        INTO total
        FROM messages
        WHERE countdownID = _countdownID
        ORDER BY timestamp ASC
        LIMIT 1;

    -- Get progress from last message
    SELECT total - value + 1
        INTO progress
        FROM messages
        WHERE countdownID = _countdownID
        ORDER BY timestamp DESC
        LIMIT 1;

    RETURN QUERY
    SELECT * FROM (
        -- Assign rankings based on total points
        SELECT row_number() OVER (ORDER BY points.total DESC), *
        FROM (
            -- Count points and rule breakdowns for each user
            SELECT categorizedMessages.userID,
                sum(CASE rule
                    WHEN 1 THEN 0    -- First
                    WHEN 2 THEN 1000 -- 1000s
                    WHEN 3 THEN 500  -- 1001s
                    WHEN 4 THEN 200  -- 200s
                    WHEN 5 THEN 100  -- 201s
                    WHEN 6 THEN 100  -- 100s
                    WHEN 7 THEN 50   -- 101s
                    WHEN 8 THEN 12   -- Odds
                    ELSE 10          -- Evens
                END) AS total,
                count(rule) AS contributions,
                (100.0 * count(rule) / progress)::float AS percentage,
                sum(CASE rule WHEN 1 THEN 1 ELSE 0 END) AS r1,
                sum(CASE rule WHEN 2 THEN 1 ELSE 0 END) AS r2,
                sum(CASE rule WHEN 3 THEN 1 ELSE 0 END) AS r3,
                sum(CASE rule WHEN 4 THEN 1 ELSE 0 END) AS r4,
                sum(CASE rule WHEN 5 THEN 1 ELSE 0 END) AS r5,
                sum(CASE rule WHEN 6 THEN 1 ELSE 0 END) AS r6,
                sum(CASE rule WHEN 7 THEN 1 ELSE 0 END) AS r7,
                sum(CASE rule WHEN 8 THEN 1 ELSE 0 END) AS r8,
                sum(CASE rule WHEN 9 THEN 1 ELSE 0 END) AS r9
            FROM (
                -- Get qualifying rule for each message
                SELECT
                    messages.userID,
                    CASE TRUE
                        WHEN value=total  THEN 1 -- First
                        WHEN value%1000=0 THEN 2 -- 1000s
                        WHEN value%1000=1 THEN 3 -- 1001s
                        WHEN value%200=0  THEN 4 -- 200s
                        WHEN value%200=1  THEN 5 -- 201s
                        WHEN value%100=0  THEN 6 -- 100s
                        WHEN value%100=1  THEN 7 -- 101s
                        WHEN value%2=1    THEN 8 -- Odds
                        ELSE 9                   -- Evens
                    END AS rule
                FROM messages
                WHERE countdownID = _countdownID
            ) categorizedMessages
            GROUP BY categorizedMessages.userID
        ) points
    ) rankings
    WHERE rankings.userID = _userID OR _userID IS NULL;
END
$$;

CREATE FUNCTION progressData (_countdownID INT)
RETURNS TABLE (_timestamp TIMESTAMPTZ, progress INT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT timestamp, value
    FROM messages
    WHERE countdownID = _countdownID
    ORDER BY messageID;
END
$$;

CREATE PROCEDURE progressStats
    (_countdownID IN INT,
        total OUT INT,
        current OUT INT,
        progress OUT INT,
        percentage OUT DECIMAL,
        startTime OUT TIMESTAMPTZ,
        endTime OUT TIMESTAMPTZ,
        rate OUT DECIMAL,
        longestBreak OUT INTERVAL,
        longestBreakStart OUT TIMESTAMPTZ,
        longestBreakEnd OUT TIMESTAMPTZ
    )
LANGUAGE plpgsql AS $$
BEGIN
    -- Get startTime and total from first message
    SELECT messages.value, messages.timestamp
        INTO total, startTime
        FROM messages
        WHERE messages.countdownID = _countdownID
        ORDER BY messages.timestamp ASC
        LIMIT 1;

    -- Get endTime and current from last message
    SELECT messages.value, messages.timestamp
    INTO current, endTime
        FROM messages
        WHERE messages.countdownID = _countdownID
        ORDER BY messages.timestamp DESC
        LIMIT 1;

    -- Calculate progress and percent
    progress := total - current;
    percentage := 100.0 * progress / total;

    -- Calculate rate and update endTime
    IF current = 0 THEN
        -- Countdown has ended, so endTime is already correct
        rate := (total - current) / extract(epoch FROM (endTime - startTime));
    ELSEIF progress = 0 THEN
        -- Countdown only has 1 message
        rate := 0;
        endTime = NOW();
    ELSE
        rate := progress / extract(epoch FROM (NOW() - startTime));
        endTime := to_timestamp(extract(epoch FROM NOW()) + (current / rate));
    END IF;
    rate := rate * 60 * 60 * 24;

    -- Calculate longestBreak, longestBreakStart, and longestBreakEnd
    SELECT timestamp,
        LEAD(timestamp, 1, NOW()) OVER (ORDER BY timestamp) - timestamp AS delta
        INTO longestBreakStart, longestBreak
        FROM messages
        WHERE messages.countdownID = _countdownID
        ORDER BY delta DESC
        LIMIT 1;
    longestBreakEnd := longestBreakStart + longestBreak;
END
$$;

CREATE FUNCTION speedData (_countdownID INT, hours INT)
RETURNS TABLE (periodStart TIMESTAMPTZ, messages BIGINT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT to_timestamp((extract(epoch FROM timestamp) / hours / 60 / 60)::int
        * hours * 60 * 60) AS periodStart,
        count(messageID) as messages
    FROM messages
    WHERE countdownID = _countdownID
    GROUP BY periodStart;
END
$$;
