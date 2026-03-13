from datetime import UTC, datetime

from config import settings
from db.mongo_client import db

db[settings.collection_configs].update_one(
    {"session_id": "your-session-id-here"},
    {
        "$set": {
            "video_id": "your-youtube-video-id",
            "upload_date": datetime.now(UTC),
            "reward_recorded": False,
        }
    },
)
print(" Video upload recorded.")
