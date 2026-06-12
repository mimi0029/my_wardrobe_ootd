from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import (
    apply_preference_updates,
    delete_item,
    feedback_summary,
    fetch_all_items,
    get_preference_weights,
    init_db,
    insert_feedback,
    insert_item,
    seed_items,
    update_item,
)
from app.schemas import FeedbackRequest, ItemUpdate, RecommendRequest, WeatherRequest
from app.seed_data import DEMO_ITEMS
from app.services.feedback import build_preference_updates
from app.services.recommender import generate_outfit_options
from app.services.vision import extract_tags_from_image
from app.services.weather import get_weather_context


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
STATIC_DIR = PROJECT_ROOT / "app" / "static"

app = FastAPI(
    title="Smart Wardrobe OOTD MVP",
    description="智能可解释衣橱与 OOTD 推荐系统原型",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/items")
def list_items() -> list[dict[str, Any]]:
    return fetch_all_items()


@app.post("/api/items")
def create_item(image: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(image.filename or "upload.jpg").suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp/gif 图片")

    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as file:
        shutil.copyfileobj(image.file, file)

    tags = extract_tags_from_image(destination)
    item = insert_item(
        {
            "image_url": f"/uploads/{filename}",
            "category": tags["category"],
            "material": tags["material"],
            "color": tags["color"],
            "style": tags["style"],
            "tags": tags["tags"],
        }
    )
    item["vision"] = {
        "confidence": tags["confidence"],
        "explanation": tags["explanation"],
    }
    return item


@app.patch("/api/items/{item_id}")
def patch_item(item_id: int, payload: ItemUpdate) -> dict[str, Any]:
    item = update_item(item_id, payload.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="单品不存在")
    return item


@app.delete("/api/items/{item_id}")
def remove_item(item_id: int) -> dict[str, bool]:
    if not delete_item(item_id):
        raise HTTPException(status_code=404, detail="单品不存在")
    return {"deleted": True}


@app.post("/api/weather")
def weather(payload: WeatherRequest) -> dict[str, Any]:
    return get_weather_context(
        city=payload.city,
        temperature=payload.temperature,
        weather=payload.weather,
        uv_index=payload.uv_index,
    )


@app.post("/api/outfits/recommend")
def recommend(payload: RecommendRequest) -> dict[str, Any]:
    context = payload.model_dump()
    items = fetch_all_items()
    options = generate_outfit_options(items, context, get_preference_weights(), option_count=3)
    return {"context": context, "options": options}


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, Any]:
    updates = build_preference_updates(payload.outfit, payload.score)
    apply_preference_updates(updates)
    log = insert_feedback(
        payload.outfit_id,
        payload.outfit,
        payload.context,
        payload.score,
        payload.reaction,
    )
    return {"logged": log, "preference_updates": updates}


@app.get("/api/feedback/summary")
def feedback_log_summary() -> list[dict[str, Any]]:
    return feedback_summary()


@app.post("/api/demo/seed")
def seed_demo_items() -> dict[str, Any]:
    created = seed_items(DEMO_ITEMS)
    return {"created": len(created), "items": fetch_all_items()}


@app.get("/")
def root() -> Any:
    from fastapi.responses import FileResponse

    return FileResponse(STATIC_DIR / "index.html")
