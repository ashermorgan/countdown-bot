-- countdown-bot analytic functions and procedures

DROP FUNCTION IF EXISTS speedData;
DROP PROCEDURE IF EXISTS progressStats;
DROP FUNCTION IF EXISTS progressData;
DROP FUNCTION IF EXISTS leaderboardData;
DROP FUNCTION IF EXISTS historicalContributorData;
DROP FUNCTION IF EXISTS heatmapData;
DROP FUNCTION IF EXISTS etaData;
DROP FUNCTION IF EXISTS contributorData;

-- Get overall contributor data for a countdown
CREATE FUNCTION contributorData (
    _countdownID BIGINT -- The countdown channel ID
)
RETURNS TABLE (
    ranking BIGINT,       -- The user's (1-based) contribution ranking
    userID BIGINT,        -- The user ID
    contributions BIGINT, -- The user's number of contributions
    percentage FLOAT      -- The user's percentage of all contributions
)
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

-- Calculate the current ETA for each message in a countdown
CREATE FUNCTION etaData (
    _countdownID BIGINT -- The countdown channel ID
)
RETURNS TABLE (
    _timestamp TIMESTAMPTZ, -- The timestamp of the message
    eta TIMESTAMPTZ         -- The timestamp of the current ETA
)
LANGUAGE plpgsql AS $$
DECLARE
    total INT;
    startTime INT;
BEGIN
    -- Get total and startTime from first message
    SELECT value, extract(epoch FROM timestamp)
    INTO total, startTime
    FROM messages
    WHERE countdownID = _countdownID
    ORDER BY timestamp ASC
    LIMIT 1;

    -- Calculate eta for each message
    RETURN QUERY
    SELECT
        timestamp,
        to_timestamp(startTime + value *
            (extract(epoch FROM timestamp) - startTime) / (total - value)
        ) AS eta
    FROM messages
    WHERE countdownID = _countdownID
        AND extract(epoch FROM timestamp) != startTime
    ORDER BY messageID;
END
$$;

-- Count the number of contributions in a countdown for each day/hour zone
CREATE FUNCTION heatmapData (
    _countdownID BIGINT, -- The countdown channel ID
    _userID BIGINT       -- The user ID to filter by (or NULL for all users)
)
RETURNS TABLE (
    dow NUMERIC,    -- The day of the week (0-6 for Sunday-Saturday)
    hour NUMERIC,   -- The hour of the day (0-23)
    messages BIGINT -- The number of contributions in the zone
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        extract(dow FROM timestamp) AS dow,
        extract(hour FROM timestamp) AS hour,
        count(messageID) as messages
    FROM messages
    WHERE countdownID = _countdownID AND (userID = _userID OR _userID IS NULL)
    GROUP BY dow, hour;
END
$$;

-- Calculate each user's contribution percentage at each message in a countdown
CREATE FUNCTION historicalContributorData (
    _countdownID BIGINT -- The countdown channel ID
)
RETURNS TABLE (
    progress INT,    -- The current countdown progress (0-total)
    userID BIGINT,   -- The user ID
    percentage FLOAT -- The user's percentage of all contributions so far
)
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
    SELECT
        (total - value) AS progress,
        users.userID,
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

-- Get the current leaderboard data for a countdown
CREATE FUNCTION leaderboardData (
    _countdownID BIGINT, -- The countdown channel ID
    _userID BIGINT       -- The user ID to filter by (or NULL for all users)
)
RETURNS TABLE (
    ranking BIGINT,       -- The user's (1-based) leaderboard ranking
    userID BIGINT,        -- The user ID
    total BIGINT,         -- The user's total leaderboard points
    contributions BIGINT, -- The user's number of contributions
    percentage FLOAT,     -- The user's percentage of all contributions
    r1 BIGINT, r2 BIGINT, r3 BIGINT, r4 BIGINT, r5 BIGINT, r6 BIGINT,
    r7 BIGINT, r8 BIGINT, r9 BIGINT -- The number of each point rule applied
)
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

-- Get the current progress for each message in a countdown
CREATE FUNCTION progressData (
    _countdownID BIGINT -- The countdown channel ID
)
RETURNS TABLE (
    _timestamp TIMESTAMPTZ, -- The timestamp of the message
    progress INT            -- The current countdown progress (0-total)
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT timestamp, value
    FROM messages
    WHERE countdownID = _countdownID
    ORDER BY messageID;
END
$$;

-- Get general progress-related statistics for a countdown
CREATE PROCEDURE progressStats (
    _countdownID IN BIGINT,            -- The countdown channel ID
    total OUT INT,                     -- The starting value
    current OUT INT,                   -- The current value
    progress OUT INT,                  -- The countdown progress (0-total)
    percentage OUT DECIMAL,            -- The percentage completion
    startTime OUT TIMESTAMPTZ,         -- The start timestamp
    endTime OUT TIMESTAMPTZ,           -- The real/predicted finish timestamp
    rate OUT DECIMAL,                  -- The rate of contributions per day
    longestBreak OUT INTERVAL,         -- The longest break in contributions
    longestBreakStart OUT TIMESTAMPTZ, -- The start of the longest break
    longestBreakEnd OUT TIMESTAMPTZ    -- The end of the longest break
)
LANGUAGE plpgsql AS $$
BEGIN
    -- Get total and startTime from first message
    SELECT messages.value, messages.timestamp
    INTO total, startTime
    FROM messages
    WHERE messages.countdownID = _countdownID
    ORDER BY messages.timestamp ASC
    LIMIT 1;

    -- Get current and endTime from last message
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
    rate := rate * 60 * 60 * 24; -- Adjust rate from per sec to per day

    -- Calculate longestBreak, longestBreakStart, and longestBreakEnd
    SELECT
        timestamp,
        LEAD(timestamp, 1, NOW()) OVER (ORDER BY timestamp) - timestamp AS delta
    INTO longestBreakStart, longestBreak
    FROM messages
    WHERE messages.countdownID = _countdownID
    ORDER BY delta DESC
    LIMIT 1;
    longestBreakEnd := longestBreakStart + longestBreak;
END
$$;

-- Calculate the number of contributions per period in a countdown
CREATE FUNCTION speedData (
    _countdownID BIGINT, -- The countdown channel ID
    hours INT            -- The period size, in hours
)
RETURNS TABLE (
    periodStart TIMESTAMPTZ, -- The start of the period
    messages BIGINT          -- The number of contributions in the period
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        to_timestamp(
            (extract(epoch FROM timestamp) / hours / 3600)::int * hours * 3600
        ) AS periodStart,
        count(messageID) as messages
    FROM messages
    WHERE countdownID = _countdownID
    GROUP BY periodStart;
END
$$;
