from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "wardrobe.db"


def db_path() -> Path:
    configured = os.getenv("WARDROBE_DB")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_url TEXT NOT NULL,
                category TEXT NOT NULL,
                material TEXT NOT NULL,
                color TEXT NOT NULL,
                style TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                wear_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS outfits (
                id TEXT PRIMARY KEY,
                top_id INTEGER,
                bottom_id INTEGER,
                outerwear_id INTEGER,
                onepiece_id INTEGER,
                shoes_id INTEGER,
                bag_id INTEGER,
                accessory_id INTEGER,
                context_tags TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outfit_id TEXT NOT NULL,
                outfit_json TEXT NOT NULL,
                weather_context TEXT NOT NULL,
                user_score INTEGER NOT NULL,
                reaction TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS preference_weights (
                feature_key TEXT PRIMARY KEY,
                weight REAL NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "tags_json" in data:
        data["tags"] = json.loads(data.pop("tags_json") or "[]")
    return data


def fetch_all_items() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM items ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def insert_item(item: dict[str, Any]) -> dict[str, Any]:
    tags = item.get("tags") or []
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO items (image_url, category, material, color, style, tags_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item["image_url"],
                item["category"],
                item["material"],
                item["color"],
                item["style"],
                json.dumps(tags, ensure_ascii=False),
            ),
        )
        row = connection.execute(
            "SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return row_to_dict(row)


def update_item(item_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"category", "material", "color", "style", "tags", "wear_count"}
    normalized = {key: value for key, value in updates.items() if key in allowed}
    if not normalized:
        with get_connection() as connection:
            row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return row_to_dict(row) if row else None

    assignments: list[str] = []
    values: list[Any] = []
    for key, value in normalized.items():
        if key == "tags":
            assignments.append("tags_json = ?")
            values.append(json.dumps(value, ensure_ascii=False))
        else:
            assignments.append(f"{key} = ?")
            values.append(value)
    assignments.append("updated_at = CURRENT_TIMESTAMP")
    values.append(item_id)

    with get_connection() as connection:
        connection.execute(
            f"UPDATE items SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict(row) if row else None


def delete_item(item_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
    return cursor.rowcount > 0


def get_preference_weights() -> dict[str, float]:
    with get_connection() as connection:
        rows = connection.execute("SELECT feature_key, weight FROM preference_weights").fetchall()
    return {row["feature_key"]: float(row["weight"]) for row in rows}


def apply_preference_updates(updates: dict[str, float]) -> None:
    if not updates:
        return
    with get_connection() as connection:
        for feature_key, delta in updates.items():
            connection.execute(
                """
                INSERT INTO preference_weights (feature_key, weight)
                VALUES (?, ?)
                ON CONFLICT(feature_key) DO UPDATE SET
                    weight = MAX(-5.0, MIN(5.0, preference_weights.weight + excluded.weight)),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (feature_key, delta),
            )


def insert_feedback(
    outfit_id: str,
    outfit: dict[str, Any],
    context: dict[str, Any],
    score: int,
    reaction: str | None,
) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO feedback_logs
                (outfit_id, outfit_json, weather_context, user_score, reaction)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                outfit_id,
                json.dumps(outfit, ensure_ascii=False),
                json.dumps(context, ensure_ascii=False),
                score,
                reaction,
            ),
        )
        row = connection.execute(
            "SELECT * FROM feedback_logs WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


def feedback_summary(limit: int = 12) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, outfit_id, user_score, reaction, created_at
            FROM feedback_logs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def seed_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    existing_urls = {item["image_url"] for item in fetch_all_items()}
    for item in items:
        if item["image_url"] not in existing_urls:
            created.append(insert_item(item))
    return created
