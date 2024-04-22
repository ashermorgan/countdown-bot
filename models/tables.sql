-- countdown-bot tabe definitions

DROP TABLE IF EXISTS reactions;
DROP TABLE IF EXISTS prefixes;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS countdowns;

-- Records countdown channels
CREATE TABLE countdowns (
    countdownID BIGINT PRIMARY KEY, -- The Discord channel ID
    serverID BIGINT NOT NULL        -- The channel's Discord server ID
);

-- Records contributions to countdowns
CREATE TABLE messages (
    messageID BIGINT PRIMARY KEY,      -- The Discord message ID
    countdownID BIGINT NOT NULL,       -- The countdown ID
    userID BIGINT NOT NULL,            -- The author's Discord user ID
    value INT NOT NULL,                -- The message's numeric value
    timestamp TIMESTAMPTZ NOT NULL,    -- The message timestamp
    FOREIGN KEY (countdownID) REFERENCES countdowns(countdownID)
);

-- Records bot command prefixes
CREATE table prefixes (
    prefixID SERIAL PRIMARY KEY, -- The prefix ID
    countdownID BIGINT NOT NULL, -- The countdown ID
    value VARCHAR(8) NOT NULL,   -- The prefix
    FOREIGN KEY (countdownID) REFERENCES countdowns(countdownID)
);

-- Records custom countdown reactions
CREATE table reactions (
    prefixID SERIAL PRIMARY KEY, -- The reaction ID
    countdownID BIGINT NOT NULL, -- The countdown ID
    number INT NOT NULL,   -- The prefix
    value CHAR NOT NULL,   -- The reaction
    FOREIGN KEY (countdownID) REFERENCES countdowns(countdownID)
);
