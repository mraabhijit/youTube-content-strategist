from datetime import UTC, datetime

from config import settings
from db.mongo_client import db
from googleapiclient.discovery import build


def get_youtube_client():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def fetch_channel_id(youtube, handle: str) -> str | None:
    """
    Resolve a channel handle or name to a channel ID.
    Example handle: '@mkbhd' or 'MrBeast'
    """
    response = (
        youtube.search()
        .list(q=handle, type="channel", part="id,snippet", maxResults=1)
        .execute()
    )

    items = response.get("items", [])
    if not items:
        print(f"Channel '{handle}' not found.")
        return None

    channel_id = items[0]["id"]["channelId"]
    channel_name = items[0]["snippet"]["title"]
    print(f"Found channel: {channel_name} ({channel_id})")
    return channel_id


def fetch_recent_videos(youtube, channel_id: str, max_results: int = 10) -> list:
    """
    Fetch the most recent videos from a channel.
    """
    response = (
        youtube.search()
        .list(
            channelId=channel_id,
            type="video",
            part="id,snippet",
            order="date",
            maxResults=max_results,
        )
        .execute()
    )

    video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
    titles = {
        item["id"]["videoId"]: item["snippet"]["title"]
        for item in response.get("items", [])
    }
    upload_dates = {
        item["id"]["videoId"]: item["snippet"]["publishedAt"]
        for item in response.get("items", [])
    }

    return [video_ids, titles, upload_dates]


def fetch_video_stats(youtube, video_ids: list) -> dict:
    """
    Fetch view counts and like counts for a list of video IDs.
    """
    response = (
        youtube.videos()
        .list(id=",".join(video_ids), part="statistics,contentDetails")
        .execute()
    )

    stats = {}
    for item in response.get("items", []):
        vid_id = item["id"]
        s = item["statistics"]
        stats[vid_id] = {
            "view_count": int(s.get("viewCount", 0)),
            "like_count": int(s.get("likeCount", 0)),
            "comment_count": int(s.get("commentCount", 0)),
        }

    return stats


def ingest_channel(handle: str, niche: str, max_results: int = 10):
    """
    Full ingestion pipeline for a public channel.
    Fetches recent video metadata and stores in market_trends.
    """
    youtube = get_youtube_client()

    print(f"\nIngesting channel: {handle}")
    channel_id = fetch_channel_id(youtube, handle)
    if not channel_id:
        return

    video_ids, titles, upload_dates = fetch_recent_videos(
        youtube, channel_id, max_results
    )
    if not video_ids:
        print("No videos found.")
        return

    stats = fetch_video_stats(youtube, video_ids)

    docs = []
    for vid_id in video_ids:
        s = stats.get(vid_id, {})
        view_count = s.get("view_count", 0)

        # Estimate competition score from engagement ratio
        like_ratio = s.get("like_count", 0) / max(view_count, 1)
        competition_score = round(min(like_ratio * 20, 1.0), 2)

        doc = {
            "video_id": vid_id,
            "channel_id": channel_id,
            "channel_handle": handle,
            "niche": niche,
            "title": titles.get(vid_id, ""),
            "view_count": view_count,
            "like_count": s.get("like_count", 0),
            "comment_count": s.get("comment_count", 0),
            "competition_score": competition_score,
            "upload_date": upload_dates.get(vid_id, ""),
            "source": "youtube_api",
            "timestamp": datetime.now(UTC),
        }
        docs.append(doc)

    if docs:
        db[settings.collection_trends].insert_many(docs)
        print(f" Inserted {len(docs)} trend documents from {handle}")

        print("\nSample document:")
        sample = docs[0]
        for k, v in sample.items():
            if k not in ["_id", "timestamp"]:
                print(f"  {k}: {v}")

    return docs


if __name__ == "__main__":
    # Test with any public channel — swap handle and niche as needed
    ingest_channel(handle="MrBeast", niche="entertainment", max_results=5)
    ingest_channel(handle="mkbhd", niche="tech", max_results=5)
