from datetime import UTC, datetime

from config import settings
from db.mongo_client import db
from feedback.fetcher import fetch_video_metrics


def process_pending_videos():
    """
    Find all video configs that have been uploaded but not yet
    had their real performance data recorded. Fetch and store results.
    """
    # Find configs that have a video_id but no corresponding replay reward
    pending = list(
        db[settings.collection_configs].find(
            {"video_id": {"$exists": True}, "reward_recorded": {"$ne": True}},
            {"_id": 0},
        )
    )

    if not pending:
        print("No pending videos to process.")
        return 0

    print(f"Found {len(pending)} pending videos.")
    recorded = 0

    for config in pending:
        video_id = config["video_id"]
        upload_date = config["upload_date"]

        print(f"\nProcessing video {video_id}...")
        metrics = fetch_video_metrics(video_id, upload_date)

        if metrics is None:
            continue

        # Write real experience to replay collection
        replay_doc = {
            "session_id": config["session_id"],
            "video_id": video_id,
            "topic": config["topic"],
            "thumbnail_style": config["thumbnail_style"],
            "title_format": config["title_format"],
            "competition_score": config.get("competition_score", 0.5),
            "avg_niche_ctr": config.get("avg_niche_ctr", 0.05),
            "avg_views": config.get("avg_views", 50000),
            "ctr": metrics["ctr"],
            "avd": metrics["avd"],
            "composite_reward": metrics["composite_reward"],
            "source": "real",  # distinguishes real from simulated data
            "timestamp": datetime.now(UTC),
        }

        db[settings.collection_replay].insert_one(replay_doc)

        # Mark config as processed
        db[settings.collection_configs].update_one(
            {"session_id": config["session_id"]}, {"$set": {"reward_recorded": True}}
        )

        print(
            f"   Recorded — CTR: {metrics['ctr']}, AVD: {metrics['avd']}, Reward: {metrics['composite_reward']}"
        )
        recorded += 1

    print(f"\nProcessed {recorded} videos.")
    return recorded


def run_feedback_cycle():
    """
    Full feedback loop:
    1. Fetch real performance data for pending videos
    2. Retrain agent if new data was recorded
    """
    print("=" * 50)
    print("Starting feedback cycle...")

    recorded = process_pending_videos()

    if recorded > 0:
        print("\nNew data recorded — triggering retraining...")
        from feedback.retrainer import retrain

        retrain()
    else:
        print("\nNo new data — skipping retraining.")

    print("\nFeedback cycle complete.")
    print("=" * 50)


if __name__ == "__main__":
    run_feedback_cycle()
