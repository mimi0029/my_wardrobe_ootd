from __future__ import annotations

from pathlib import Path
from typing import Any


COLOR_BUCKETS = [
    ("黑色", (35, 35, 35)),
    ("白色", (235, 235, 225)),
    ("米白色", (220, 205, 180)),
    ("藏青色", (25, 45, 90)),
    ("浅蓝色", (120, 170, 210)),
    ("灰色", (135, 135, 135)),
    ("驼色", (175, 130, 80)),
    ("棕色", (115, 75, 45)),
    ("红色", (175, 50, 55)),
    ("粉色", (220, 140, 160)),
    ("绿色", (70, 135, 95)),
    ("黄色", (220, 180, 65)),
]

KEYWORD_TAGS = {
    "linen": ("亚麻", "极简", "上衣", ["透气", "夏季"]),
    "cotton": ("纯棉", "休闲", "上衣", ["亲肤", "日常"]),
    "silk": ("真丝", "优雅", "上衣", ["垂坠", "晚宴"]),
    "wool": ("羊毛", "通勤", "外套", ["保暖", "秋冬"]),
    "leather": ("皮质", "复古", "外套", ["硬挺", "秋冬"]),
    "shirt": ("纯棉", "通勤", "上衣", ["衬衫", "可叠穿"]),
    "tee": ("纯棉", "休闲", "上衣", ["T恤", "日常"]),
    "pants": ("纯棉", "通勤", "裤装", ["利落"]),
    "trouser": ("羊毛", "通勤", "裤装", ["垂坠"]),
    "skirt": ("真丝", "优雅", "裙装", ["半裙"]),
    "dress": ("真丝", "优雅", "连衣裙", ["连体", "晚宴"]),
    "coat": ("羊毛", "通勤", "外套", ["保暖"]),
    "jacket": ("皮质", "休闲", "外套", ["防风"]),
    "sneaker": ("织物", "运动", "鞋子", ["运动鞋", "舒适"]),
    "loafer": ("皮质", "通勤", "鞋子", ["乐福鞋"]),
    "heel": ("皮质", "优雅", "鞋子", ["高跟鞋"]),
    "bag": ("皮质", "通勤", "包包", ["容量适中"]),
    "tote": ("帆布", "通勤", "包包", ["托特包", "可装电脑"]),
    "backpack": ("尼龙", "运动", "包包", ["双肩包", "可装电脑"]),
    "hat": ("棉麻", "休闲", "配饰", ["帽子", "防晒"]),
    "sunglasses": ("树脂", "极简", "配饰", ["墨镜", "防晒"]),
}


def extract_tags_from_image(file_path: Path) -> dict[str, Any]:
    """Extract explainable wardrobe tags from an uploaded image.

    In production this function is the integration point for GPT-4V, Claude
    Vision, YOLO, or a fine-tuned fashion classifier. The MVP keeps a local
    fallback so the workflow is usable without external API keys.
    """

    material, style, category, tags = _infer_from_filename(file_path.name)
    color = _dominant_color(file_path) or _infer_color_from_filename(file_path.name)

    return {
        "category": category,
        "material": material,
        "color": color,
        "style": style,
        "tags": sorted(set(tags + ["AI初筛", "可编辑"])),
        "confidence": 0.72,
        "explanation": "MVP 使用图片主色与文件名启发式识别；可替换为视觉大模型输出。",
    }


def _infer_from_filename(filename: str) -> tuple[str, str, str, list[str]]:
    name = filename.lower()
    for keyword, result in KEYWORD_TAGS.items():
        if keyword in name:
            return result
    return "混纺", "休闲", "上衣", ["待确认"]


def _infer_color_from_filename(filename: str) -> str:
    name = filename.lower()
    mapping = {
        "navy": "藏青色",
        "blue": "浅蓝色",
        "white": "白色",
        "cream": "米白色",
        "beige": "米白色",
        "black": "黑色",
        "gray": "灰色",
        "grey": "灰色",
        "camel": "驼色",
        "brown": "棕色",
        "red": "红色",
        "pink": "粉色",
        "green": "绿色",
        "yellow": "黄色",
    }
    for keyword, color in mapping.items():
        if keyword in name:
            return color
    return "米白色"


def _dominant_color(path: Path) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        with Image.open(path) as image:
            image.thumbnail((80, 80))
            rgb_image = image.convert("RGB")
            pixels = list(rgb_image.getdata())
    except Exception:
        return None

    if not pixels:
        return None

    avg = tuple(sum(channel) / len(pixels) for channel in zip(*pixels))
    return min(COLOR_BUCKETS, key=lambda item: _distance(avg, item[1]))[0]


def _distance(left: tuple[float, float, float], right: tuple[int, int, int]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right))
