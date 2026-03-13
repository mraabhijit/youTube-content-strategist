import random
import uuid
from datetime import UTC, datetime
from typing import Optional

# import numpy as np
from config import settings
from db.mongo_client import db
from states import NICHES, THUMBNAIL_STYLES, TITLE_FORMATS, TOPICS


def simulate_reward(
    topic: str, thumbnail: str, title_format: str, competition_score: float
) -> dict:
    """
    Simulate a realistic CTR and AVD based on the video config.
    Some combos naturally perform better - mirroring real YouTube behaviour.
    """
    base_ctr = random.uniform(0.02, 0.12)  # 2% to 12% CTR
    base_avd = random.uniform(0.38, 0.75)  # 30% to 75% retention

    # High-performing combos get a realistic boost
    if topic in ["AI tools", "finance"] and title_format in ["how_to", "listicle"]:
        base_ctr += random.uniform(0.03, 0.06)
    if thumbnail in ["clean_minimal", "high_contrast"]:
        base_avd += random.uniform(0.05, 0.12)

    # Competition suppresses performance — higher saturation, harder to stand out
    # At competition=1.0: CTR reduced by 50%, AVD by 20%
    # At competition=0.1: CTR reduced by only 5%, AVD by 2% (near content gap)
    ctr_multiplier = 1 - (competition_score * 0.70)
    avd_multiplier = 1 - (competition_score * 0.35)

    return {
        "ctr": round(min(base_ctr * ctr_multiplier, 0.20), 4),  # cap at 20%
        "avd": round(min(base_avd * avd_multiplier, 0.95), 4),  # cap at 95%
    }


def generate_episode() -> dict:
    """
    Generate one full simulated experienc: trend + config + reward.
    Returns all three documents linked by session_id.
    """

    session_id = str(uuid.uuid4())
    topic = random.choice(TOPICS)
    thumbnail = random.choice(THUMBNAIL_STYLES)
    title_format = random.choice(TITLE_FORMATS)
    niche = random.choice(NICHES)
    competition_score = round(
        random.uniform(0.1, 1.0), 2
    )  # 0.1 for lesser videos in the space or content gap, 1.0 for heavily populated
    timestamp = datetime.now(UTC)

    trend_doc = {
        "session_id": session_id,
        "niche": niche,
        "trending_topic": topic,
        "avg_niche_ctr": round(random.uniform(0.03, 0.09), 4),
        "competition_score": competition_score,
        "timestamp": timestamp,
    }

    config_doc = {
        "session_id": session_id,
        "topic": topic,
        "thumbnail_style": thumbnail,
        "title_format": title_format,
        "timestamp": timestamp,
    }

    reward = simulate_reward(topic, thumbnail, title_format, competition_score)
    replay_doc = {
        "session_id": session_id,
        "topic": topic,
        "thumbnail_style": thumbnail,
        "title_format": title_format,
        "ctr": reward["ctr"],
        "avd": reward["avd"],
        "composite_reward": round((reward["ctr"] * 0.6) + (reward["avd"] * 0.4), 4),
        "competition_score": competition_score,
        "avg_niche_ctr": round(random.uniform(0.03, 0.09), 4),
        "avg_views": round(random.uniform(1000, 500000), 0),
        "timestamp": timestamp,
    }

    return {
        "trend": trend_doc,
        "config": config_doc,
        "replay": replay_doc,
    }


def run_simulation(n_episodes: Optional[int] = None):
    """
    Run n_episodes of simulation and bulk-insert into MongoDB."""

    n = n_episodes or settings.simulation_episodes
    trends, configs, replays = [], [], []

    print(f"Generation {n} simulated episodes.")

    for _ in range(n):
        episode = generate_episode()
        trends.append(episode["trend"])
        configs.append(episode["config"])
        replays.append(episode["replay"])

    db[settings.collection_trends].insert_many(trends)
    db[settings.collection_configs].insert_many(configs)
    db[settings.collection_replay].insert_many(replays)

    print(f" Inserted {n} documents into each collection.")
    print(
        f"   - {settings.collection_trends}: {db[settings.collection_trends].count_documents({})} docs"
    )
    print(
        f"   - {settings.collection_configs}: {db[settings.collection_configs].count_documents({})} docs"
    )
    print(
        f"   - {settings.collection_replay}: {db[settings.collection_replay].count_documents({})} docs"
    )


if __name__ == "__main__":
    run_simulation()
