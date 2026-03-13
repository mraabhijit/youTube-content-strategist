import uuid
from datetime import UTC, datetime

from config import settings
from db.mongo_client import db

# Write a complex nested document
test_doc = {
    "session_id": str(uuid.uuid4()),
    "nested": {
        "topic": "AI tools",
        "metrics": {"ctr": 0.082, "avd": 0.64, "composite_reward": 0.3052},
        "tags": ["faceless", "viral", "listicle"],
    },
    "timestamp": datetime.now(UTC),
}

inserted = db[settings.collection_replay].insert_one(test_doc)
retrieved = db[settings.collection_replay].find_one({"_id": inserted.inserted_id})

# Verify every nested field survived the round trip
assert retrieved["nested"]["topic"] == "AI tools"
assert retrieved["nested"]["metrics"]["ctr"] == 0.082
assert retrieved["nested"]["tags"][1] == "viral"

print(" Check 1 Passed — Data integrity confirmed")
print(f"   Written and retrieved session: {retrieved['session_id']}")

# Clean up test document
db[settings.collection_replay].delete_one({"_id": inserted.inserted_id})
