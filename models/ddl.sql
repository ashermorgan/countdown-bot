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
