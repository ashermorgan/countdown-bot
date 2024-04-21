-- countdown-bot utility procedures

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
