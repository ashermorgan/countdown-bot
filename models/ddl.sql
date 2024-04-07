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
    timestamp TIMESTAMP NOT NULL
);

CREATE TYPE addMessageResults AS ENUM (
    'badCountdown', 'badNumber', 'badUser', 'good'
);

-- Validate and add a new countdown message
CREATE PROCEDURE addMessage
    (_messageID IN INT, _countdownID IN INT, _userID IN INT, _value IN INT,
    _timestamp IN TIMESTAMP, result OUT addMessageResults)
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
$$
