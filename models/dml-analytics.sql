-- countdown-bot analytic functions and procedures

DROP FUNCTION IF EXISTS speedData;
DROP PROCEDURE IF EXISTS progressStats;
DROP FUNCTION IF EXISTS progressData;
DROP FUNCTION IF EXISTS leaderboardData;
DROP FUNCTION IF EXISTS historicalContributorData;
DROP PROCEDURE IF EXISTS heatmapStats;
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
    -- Get total countdown progress
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
    _timestamp TIMESTAMP, -- The timestamp of the message
    eta TIMESTAMP         -- The timestamp of the current ETA
)
LANGUAGE plpgsql AS $$
DECLARE
    total INT;
    startTime INT;
    _timezone INTERVAL;
BEGIN
    -- Get total and startTime from first message
    SELECT value, extract(epoch FROM timestamp)
    INTO total, startTime
    FROM messages
    WHERE countdownID = _countdownID
    ORDER BY messageID ASC
    LIMIT 1;

    -- Get timezone
    SELECT timezone
    INTO _timezone
    FROM countdowns
    WHERE countdownID = _countdownID;

    -- Calculate eta for each message
    RETURN QUERY
    SELECT
        timestamp AT TIME ZONE _timezone,
        to_timestamp(startTime + total *
            (extract(epoch FROM timestamp) - startTime) / (total - value)
        ) AT TIME ZONE _timezone AS eta
    FROM messages
    WHERE countdownID = _countdownID AND value != total
    ORDER BY messageID;
END
$$;

-- Count the number of contributions in a countdown for each day/hour zone
CREATE FUNCTION heatmapData (
    _countdownID BIGINT, -- The countdown channel ID
    _userID BIGINT       -- The user ID to filter by (or NULL for all users)
)
RETURNS TABLE (
    dow NUMERIC,    -- The day of the week (0-6 for Sun-Sat)
    hour NUMERIC,   -- The hour of the day (0-23)
    messages BIGINT -- The number of contributions in the zone
)
LANGUAGE plpgsql AS $$
DECLARE
    _timezone INTERVAL;
BEGIN
    -- Get timezone
    SELECT timezone
    INTO _timezone
    FROM countdowns
    WHERE countdownID = _countdownID;

    RETURN QUERY
    SELECT
        extract(dow FROM timestamp AT TIME ZONE _timezone) AS dow,
        extract(hour FROM timestamp AT TIME ZONE _timezone) AS hour,
        count(messageID) as messages
    FROM messages
    WHERE countdownID = _countdownID AND (userID = _userID OR _userID IS NULL)
    GROUP BY dow, hour;
END
$$;

CREATE PROCEDURE heatmapStats (
    _countdownID IN BIGINT, -- The countdown channel ID
    curDow OUT NUMERIC,     -- The current day of the week (0-6 for Sun-Sat)
    curHour OUT NUMERIC     -- The current hour of the day (0-23)
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT
        extract(dow FROM NOW() AT TIME ZONE timezone) AS dow,
        extract(hour FROM NOW() AT TIME ZONE timezone) AS hour
    INTO curDow, curHour
    FROM countdowns
    WHERE countdownID = _countdownID;
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
    ORDER BY messageID ASC
    LIMIT 1;

    -- Calculator percentage for each user for each message
    RETURN QUERY
    SELECT
        (total - value) AS progress,
        users.userID,
        (
            sum(CASE messages.userID WHEN users.userID THEN 1 ELSE 0 END)
            OVER (PARTITION BY users.userID ORDER BY messageID)
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
    ORDER BY messageID ASC
    LIMIT 1;

    -- Get progress from last message
    SELECT total - value + 1
    INTO progress
    FROM messages
    WHERE countdownID = _countdownID
    ORDER BY messageID DESC
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
    _timestamp TIMESTAMP, -- The timestamp of the message
    progress INT          -- The current countdown progress (0-total)
)
LANGUAGE plpgsql AS $$
DECLARE
    _timezone INTERVAL;
BEGIN
    -- Get timezone
    SELECT timezone
    INTO _timezone
    FROM countdowns
    WHERE countdownID = _countdownID;

    RETURN QUERY
    SELECT timestamp AT TIME ZONE _timezone, value
    FROM messages
    WHERE countdownID = _countdownID
    ORDER BY messageID;
END
$$;

-- Get general progress-related statistics for a countdown
CREATE PROCEDURE progressStats (
    _countdownID IN BIGINT,          -- The countdown channel ID
    total OUT INT,                   -- The starting value
    current OUT INT,                 -- The current value
    progress OUT INT,                -- The countdown progress (0-total)
    percentage OUT DECIMAL,          -- The percentage completion
    startTime OUT TIMESTAMP,         -- The start timestamp
    startAge OUT INTERVAL,           -- The time since the start
    endTime OUT TIMESTAMP,           -- The real/predicted finish timestamp
    endAge OUT INTERVAL,             -- The time since/until the finish
    rate OUT DECIMAL,                -- The rate of contributions per day
    longestBreak OUT INTERVAL,       -- The longest break in contributions
    longestBreakStart OUT TIMESTAMP, -- The start of the longest break
    longestBreakEnd OUT TIMESTAMP    -- The end of the longest break
)
LANGUAGE plpgsql AS $$
DECLARE
    _timezone INTERVAL;
    _now TIMESTAMP;
BEGIN
    -- Get timezone
    SELECT timezone
    INTO _timezone
    FROM countdowns
    WHERE countdownID = _countdownID;

    SELECT NOW() AT TIME ZONE _timezone INTO _now;

    -- Get total and startTime from first message
    SELECT messages.value, messages.timestamp
    INTO total, startTime AT TIME ZONE _timezone
    FROM messages
    WHERE messages.countdownID = _countdownID
    ORDER BY messageID ASC
    LIMIT 1;

    -- Get current and endTime from last message
    SELECT messages.value, messages.timestamp
    INTO current, endTime AT TIME ZONE _timezone
    FROM messages
    WHERE messages.countdownID = _countdownID
    ORDER BY messageID DESC
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
        rate := progress / extract(epoch FROM (_now - startTime));
        endTime := to_timestamp(extract(epoch FROM _now) + (current / rate))
            AT TIME ZONE _timezone;
    END IF;
    rate := rate * 60 * 60 * 24; -- Adjust rate from per sec to per day

    -- Calculate startAge and endAge
    startAge := _now - startTime;
    endAge := _now - endTime;

    -- Calculate longestBreak, longestBreakStart, and longestBreakEnd
    SELECT
        timestamp AT TIME ZONE _timezone,
        CASE
            WHEN value = 0 THEN '0'
            ELSE LEAD(timestamp, 1, NOW()) OVER (ORDER BY messageID) - timestamp
        END AS delta
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
    periodStart TIMESTAMP, -- The start of the period
    messages BIGINT        -- The number of contributions in the period
)
LANGUAGE plpgsql AS $$
DECLARE
    _timezone INTERVAL;
BEGIN
    -- Get timezone
    SELECT timezone
    INTO _timezone
    FROM countdowns
    WHERE countdownID = _countdownID;

    RETURN QUERY
    SELECT
        to_timestamp(
            floor(extract(epoch FROM timestamp AT TIME ZONE _timezone) / hours
            / 3600)::int * hours * 3600
        ) AT TIME ZONE '0:00' AS periodStart,
        count(messageID) as messages
    FROM messages
    WHERE countdownID = _countdownID
    GROUP BY periodStart;
END
$$;
