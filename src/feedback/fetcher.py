from datetime import UTC, datetime, timedelta
from typing import Optional

from feedback.youtube_auth import get_authenticated_service


def fetch_video_metrics(video_id: str, upload_date: datetime) -> Optional[dict]:
    """
    Fetch CTR and AVD for a video after its 48 hour performance window.
    Returns None if the window hasn't elapsed yet.
    """
    now = datetime.now(UTC)
    window_end = upload_date + timedelta(hours=48)

    if now < window_end:
        hours_remaining = (window_end - now).seconds // 3600
        print(f"  Video {video_id} - {hours_remaining}h remaining in window.")
        return None

    analytics = get_authenticated_service("youtubeAnalytics", "v2")

    start_date = upload_date.strftime("%Y-%m-%d")
    end_date = window_end.strftime("%Y-%m-%d")

    try:
        response = (
            analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="impressionClickThroughRate,averageViewPercentage",
                dimensions="video",
                filters=f"video=={video_id}",
            )
            .execute()
        )

        rows = response.get("rows", [])
        if not rows:
            print(f"   No analytics data yet for video {video_id}.")
            return None

        ctr = rows[0][1] / 100  # API returns percentage
        avd = rows[0][2] / 100

        return {
            "video_id": video_id,
            "ctr": round(ctr, 4),
            "avd": round(avd, 4),
            "composite_reward": round((ctr * 0.6) + (avd * 0.4), 4),
            "fetched_at": now,
        }

    except Exception as e:
        print(f"   Error fetching metrics for {video_id}: {e}")
        return None
