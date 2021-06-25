# Import dependencies
import json
import os

# Write to settings.json
with open(os.path.join(os.path.dirname(__file__), "settings.json"), "w") as f:
    data = {
        "token": "YOUR_TOKEN_HERE",
        "prefixes": ["c."],
        "database": "sqlite:///data.sqlite3"
    }
    json.dump(data, f)
