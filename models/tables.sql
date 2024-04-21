-- countdown-bot tabe definitions

DROP TABLE IF EXISTS prefixes;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS countdowns;

-- Records countdown channels
CREATE TABLE countdowns (
    countdownID INT PRIMARY KEY, -- The Discord channel ID
    serverID INT NOT NULL        -- The channel's Discord server ID
);

-- Records contributions to countdowns
CREATE TABLE messages (
    messageID INT PRIMARY KEY,      -- The Discord message ID
    countdownID INT NOT NULL,       -- The countdown ID
    userID INT NOT NULL,            -- The author's Discord user ID
    value INT NOT NULL,             -- The message's numeric value
    timestamp TIMESTAMPTZ NOT NULL, -- The message timestamp
    FOREIGN KEY (countdownID) REFERENCES countdowns(countdownID)
);

-- Records bot command prefixes
CREATE table prefixes (
    prefixID SERIAL PRIMARY KEY, -- The prefix ID
    countdownID INT NOT NULL,    -- The countdown ID
    value VARCHAR(8) NOT NULL,   -- The prefix
    FOREIGN KEY (countdownID) REFERENCES countdowns(countdownID)
);
