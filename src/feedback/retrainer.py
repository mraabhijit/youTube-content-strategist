from pathlib import Path

from config import settings
from db.mongo_client import db


def retrain():
    """
    Retrain the bandit agent on all available replay data.
    Called after new real performance data has been recorded.
    """
    total_docs = db[settings.collection_replay].count_documents({})
    real_docs = db[settings.collection_replay].count_documents({"source": "real"})
    sim_docs = total_docs - real_docs

    print("\n--- Retraining Agent ---")
    print(f"Total replay documents: {total_docs}")
    print(f"  Simulated: {sim_docs}")
    print(f"  Real:      {real_docs}")

    # To avoid circular imports
    from agent.bandit import train

    Path("models").mkdir(exist_ok=True)
    model, history = train(epochs=100)

    final_loss = history.history["loss"][-1]
    val_loss = history.history["val_loss"][-1]

    print("\n  Retraining complete.")
    print(f"   Training loss:   {final_loss:.6f}")
    print(f"   Validation loss: {val_loss:.6f}")

    return model
