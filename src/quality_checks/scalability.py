import time

from config import settings
from data.simulator import generate_episode, run_simulation
from db.mongo_client import db

# Check current document count
current_count = db[settings.collection_replay].count_documents({})
print(f"Current replay documents: {current_count}")

# Top up to 10,000 if needed
target = 10000
if current_count < target:
    needed = target - current_count
    print(f"Generating {needed} additional documents to reach {target}...")
    run_simulation(n_episodes=needed)

total = db[settings.collection_replay].count_documents({})
print(f"Total replay documents: {total}")

# Check 1 — Write performance at scale
print("\nTesting write performance...")

batch = [generate_episode()["replay"] for _ in range(1000)]
start = time.perf_counter()
db[settings.collection_replay].insert_many(batch)
write_ms = (time.perf_counter() - start) * 1000
print(f"Bulk insert 1000 docs: {write_ms:.1f}ms")

# Check 2 — Read performance at scale
print("\nTesting read performance...")
start = time.perf_counter()
docs = list(db[settings.collection_replay].find({}, {"_id": 0}))
read_ms = (time.perf_counter() - start) * 1000
print(f"Full collection read ({len(docs)} docs): {read_ms:.1f}ms")

# Check 3 — Indexed query performance
print("\nTesting indexed query performance...")
db[settings.collection_replay].create_index("topic")
db[settings.collection_replay].create_index("competition_score")

start = time.perf_counter()
results = list(
    db[settings.collection_replay].find(
        {"topic": "AI tools", "competition_score": {"$lt": 0.3}}, {"_id": 0}
    )
)
query_ms = (time.perf_counter() - start) * 1000
print(f"Filtered query ({len(results)} results): {query_ms:.1f}ms")

# Check 4 — Aggregation performance
print("\nTesting aggregation performance...")
start = time.perf_counter()
pipeline = [
    {
        "$group": {
            "_id": "$topic",
            "avg_reward": {"$avg": "$composite_reward"},
            "count": {"$sum": 1},
        }
    },
    {"$sort": {"avg_reward": -1}},
]
agg_results = list(db[settings.collection_replay].aggregate(pipeline))
agg_ms = (time.perf_counter() - start) * 1000
print(f"Aggregation across all docs: {agg_ms:.1f}ms")

print("\n--- Scalability Report ---")
print(f"Total documents:        {db[settings.collection_replay].count_documents({})}")
print(f"Bulk write (1000 docs): {write_ms:.1f}ms")
print(f"Full collection read:   {read_ms:.1f}ms")
print(f"Filtered query:         {query_ms:.1f}ms")
print(f"Aggregation:            {agg_ms:.1f}ms")

all_passed = all([write_ms < 5000, read_ms < 10000, query_ms < 2000, agg_ms < 5000])

if all_passed:
    print("\n Check 4 Passed — Scalability requirement confirmed")
else:
    print("\n Check 4 Failed — Review slow operations above")
