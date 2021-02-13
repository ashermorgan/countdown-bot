# Import dependencies
import json
import os

# Write to data.json
with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
    data = {
        "token": "YOUR_TOKEN_HERE",
        "countdowns": {}
    }
    json.dump(data, f)
