from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ItemUpdate(BaseModel):
    category: str | None = None
    material: str | None = None
    color: str | None = None
    style: str | None = None
    tags: list[str] | None = None
    wear_count: int | None = Field(default=None, ge=0)


class WeatherRequest(BaseModel):
    city: str | None = None
    temperature: float | None = None
    weather: str | None = None
    uv_index: float | None = Field(default=None, ge=0)


class RecommendRequest(BaseModel):
    temperature: float = 24
    weather: str = "晴"
    uv_index: float = Field(default=4, ge=0)
    sun_protection: bool = False
    occasion: Literal["职场通勤", "周末约会", "户外运动", "晚宴", "日常休闲"] = "日常休闲"
    carry_load: Literal["少量物品", "需带电脑/文件", "运动装备"] = "少量物品"
    lucky_color: str | None = None
    city: str | None = None


class FeedbackRequest(BaseModel):
    outfit_id: str
    outfit: dict[str, Any]
    context: dict[str, Any]
    score: int = Field(ge=1, le=5)
    reaction: Literal["喜欢", "一般", "不喜欢"] | None = None
