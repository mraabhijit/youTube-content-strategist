from itertools import product

import numpy as np
import tensorflow as tf
from config import settings
from db.mongo_client import db
from states import THUMBNAIL_STYLES, TITLE_FORMATS, TOPICS

ACTION_SPACE = list(product(TOPICS, THUMBNAIL_STYLES, TITLE_FORMATS))
N_ACTIONS = len(ACTION_SPACE)  # 150
ACTION_INDEX = {action: idx for idx, action in enumerate(ACTION_SPACE)}
TOPIC_INDEX = {topic: idx for idx, topic in enumerate(TOPICS)}


def build_model(state_dim: int) -> tf.keras.Model:
    """
    Predicts a single reward value for a given state+action pair.
    """
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(state_dim,), name="state_action_input"),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="linear", name="reward_output"),
        ]
    )
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mse")
    return model


def encode_state(doc: dict) -> list:
    topic_encoding = [0.0] * len(TOPICS)
    topic_idx = TOPIC_INDEX.get(doc.get("topic", ""), -1)
    if topic_idx >= 0:
        topic_encoding[topic_idx] = 1.0

    competition = doc.get("competition_score", 0.5)
    avg_ctr = doc.get("avg_niche_ctr", 0.05) * 10
    avg_views = np.log1p(doc.get("avg_views", 10000)) / 13  # less aggressive scaling

    return topic_encoding + [competition, avg_ctr, avg_views]


def encode_action(action: tuple) -> list:
    """
    One-hot encode the action tuple into a fixed-length vector.
    """
    topic_enc = [0.0] * len(TOPICS)
    thumb_enc = [0.0] * len(THUMBNAIL_STYLES)
    title_enc = [0.0] * len(TITLE_FORMATS)

    topic_enc[TOPICS.index(action[0])] = 1.0
    thumb_enc[THUMBNAIL_STYLES.index(action[1])] = 1.0
    title_enc[TITLE_FORMATS.index(action[2])] = 1.0

    return topic_enc + thumb_enc + title_enc  # 6 + 5 + 5 = 16 features


def load_replay_data():
    """
    Each training sample is a state+action vector mapped to a single reward.
    State: 9 features, Action: 16 features, Total input: 25 features.
    """
    docs = list(db[settings.collection_replay].find({}, {"_id": 0}))

    if not docs:
        raise ValueError("No replay data found. Run the simulator first.")

    X, y = [], []

    for doc in docs:
        state = encode_state(doc)
        action_key = (doc["topic"], doc["thumbnail_style"], doc["title_format"])
        action_enc = encode_action(action_key)

        competition = doc.get("competition_score", 0.5)
        context_reward = doc["composite_reward"] * (1 - (competition * 0.3))

        X.append(state + action_enc)  # 25 features total
        y.append(context_reward)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train(epochs: int = 100, batch_size: int = 32):
    print("Loading replay data from MongoDB...")
    X, y = load_replay_data()
    print(f"  Loaded {len(X)} training samples.")
    print(f"  Input shape: {X.shape}")
    print(f"  Reward range: {y.min():.4f} to {y.max():.4f}")

    state_action_dim = X.shape[1]
    model = build_model(state_action_dim)
    model.summary()

    print(f"\nTraining for {epochs} epochs...")
    history = model.fit(
        X, y, epochs=epochs, batch_size=batch_size, validation_split=0.1, verbose=1
    )

    final_loss = history.history["loss"][-1]
    print(f"\n Training complete. Final loss: {final_loss:.6f}")

    model.save("models/bandit_model.keras")
    print(" Model saved to models/bandit_model.keras")

    return model, history


def recommend(
    model: tf.keras.Model,
    topic: str,
    competition_score: float,
    avg_niche_ctr: float,
    avg_views: float = 50000,
) -> dict:
    """
    Score all 150 actions against the current state, return the best one.
    """
    topic_encoding = [0.0] * len(TOPICS)
    topic_idx = TOPIC_INDEX.get(topic, -1)
    if topic_idx >= 0:
        topic_encoding[topic_idx] = 1.0

    avg_ctr_scaled = avg_niche_ctr * 10
    avg_views_scaled = np.log1p(avg_views) / 13

    state = topic_encoding + [competition_score, avg_ctr_scaled, avg_views_scaled]

    # Score every possible action against this state
    all_inputs = []
    for action in ACTION_SPACE:
        action_enc = encode_action(action)
        all_inputs.append(state + action_enc)

    all_inputs = np.array(all_inputs, dtype=np.float32)
    predicted_rewards = model.predict(all_inputs, verbose=0).flatten()
    best_idx = np.argmax(predicted_rewards)
    best_action = ACTION_SPACE[best_idx]

    return {
        "topic": best_action[0],
        "thumbnail_style": best_action[1],
        "title_format": best_action[2],
        "expected_reward": round(float(predicted_rewards[best_idx]), 4),
    }


def main():
    import os

    os.makedirs("models", exist_ok=True)

    model, history = train(epochs=100)

    print("\n--- Recommendation Test ---")
    rec = recommend(
        model,
        topic="finance",
        competition_score=0.9,
        avg_niche_ctr=0.04,
        avg_views=15000,
    )
    print(f"High competition (finance): {rec}")

    rec = recommend(
        model,
        topic="AI tools",
        competition_score=0.2,
        avg_niche_ctr=0.07,
        avg_views=200000,
    )
    print(f"Low competition (AI tools content gap): {rec}")

    rec = recommend(
        model,
        topic="stoicism",
        competition_score=0.5,
        avg_niche_ctr=0.05,
        avg_views=50000,
    )
    print(f"Mid competition (stoicism): {rec}")


def diagnose():
    X, y = load_replay_data()
    print(f"X shape: {X.shape}")
    print(f"y shape: {y.shape}")
    print(f"\nState feature means: {X.mean(axis=0)}")
    print(f"State feature stds:  {X.std(axis=0)}")
    print(f"\nReward target mean: {y.mean()}")
    print(f"Reward target max:  {y.max()}")
    print(f"Reward target std:  {y.std()}")
    print(f"\nNon-baseline targets (actual rewards placed): {(y > y.mean()).sum()}")
    print(f"Sample state row: {X[0]}")
    print(f"Sample target non-zero slots: {(y[0] > y[0].mean()).sum()}")


if __name__ == "__main__":
    main()
