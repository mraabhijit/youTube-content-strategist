from config import settings
from db.mongo_client import db

# Expire trend documents after 90 days
db[settings.collection_trends].create_index(
    "timestamp", expireAfterSeconds=60 * 60 * 24 * 90
)

# Expire simulated replay docs after 180 days, keep real ones
db[settings.collection_replay].create_index(
    "timestamp", expireAfterSeconds=60 * 60 * 24 * 180
)

print(" TTL indexes created.")
