import time

import numpy as np
import tensorflow as tf
from agent.bandit import recommend
from config import settings
from db.mongo_client import db

# Load the saved model
model = tf.keras.models.load_model("models/bandit_model.keras")

# Test args covering different market contexts
test_cases = [
    dict(topic="AI tools", competition_score=0.2, avg_niche_ctr=0.07, avg_views=200000),
    dict(topic="finance", competition_score=0.9, avg_niche_ctr=0.04, avg_views=15000),
    dict(topic="stoicism", competition_score=0.5, avg_niche_ctr=0.05, avg_views=50000),
    dict(
        topic="minimalism", competition_score=0.3, avg_niche_ctr=0.06, avg_views=80000
    ),
    dict(
        topic="productivity", competition_score=0.7, avg_niche_ctr=0.05, avg_views=30000
    ),
]

# Warm up pass — first inference is always slower due to TF graph compilation
recommend(model, **test_cases[0])

# Timed passes
times = []
for case in test_cases * 3:  # 15 total runs across all contexts
    start = time.perf_counter()

    # Simulate full cycle — MongoDB query + recommendation
    _ = db[settings.collection_replay].find_one(
        {"source": {"$exists": True}}, {"_id": 0}
    )
    rec = recommend(model, **case)

    elapsed = (time.perf_counter() - start) * 1000
    times.append(elapsed)

avg_ms = np.mean(times)
max_ms = np.max(times)
p95_ms = np.percentile(times, 95)

print("\n--- Latency Report ---")
print(f"Runs:            {len(times)}")
print(f"Average latency: {avg_ms:.1f}ms")
print(f"P95 latency:     {p95_ms:.1f}ms")
print(f"Max latency:     {max_ms:.1f}ms")
print(f"2000ms limit:    {' All runs passed' if max_ms < 2000 else ' Exceeded limit'}")

if max_ms < 2000:
    print("\n Check 3 Passed — Latency requirement confirmed")
else:
    print("\n Check 3 Failed — Investigate MongoDB connection or model size")
