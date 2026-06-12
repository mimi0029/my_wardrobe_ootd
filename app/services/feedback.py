from __future__ import annotations

from app.services.recommender import outfit_feature_keys


LEARNING_RATE = 0.18


def build_preference_updates(outfit: dict, score: int) -> dict[str, float]:
    """Convert a 1-5 score into reward deltas for outfit feature weights."""

    reward = (score - 3) / 2
    if reward == 0:
        return {}

    updates: dict[str, float] = {}
    for key in outfit_feature_keys(outfit):
        updates[key] = updates.get(key, 0) + reward * LEARNING_RATE
    return updates
