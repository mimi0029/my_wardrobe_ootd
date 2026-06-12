from __future__ import annotations

import hashlib
import json
from typing import Any


OPTION_NAMES = ["Option A", "Option B", "Option C"]

CATEGORY_ALIASES = {
    "上衣": "top",
    "衬衫": "top",
    "T恤": "top",
    "针织衫": "top",
    "裤装": "bottom",
    "裤子": "bottom",
    "半裙": "bottom",
    "裙装": "bottom",
    "连衣裙": "onepiece",
    "连体裤": "onepiece",
    "外套": "outerwear",
    "大衣": "outerwear",
    "夹克": "outerwear",
    "鞋子": "shoes",
    "运动鞋": "shoes",
    "包包": "bag",
    "配饰": "accessory",
    "帽子": "accessory",
    "墨镜": "accessory",
}

OCCASION_STYLES = {
    "职场通勤": {"通勤": 4, "极简": 2, "优雅": 2, "运动": -3},
    "周末约会": {"优雅": 3, "休闲": 2, "复古": 2, "运动": -1},
    "户外运动": {"运动": 5, "休闲": 2, "优雅": -2},
    "晚宴": {"优雅": 5, "极简": 2, "通勤": 1, "运动": -4},
    "日常休闲": {"休闲": 4, "极简": 2, "运动": 1},
}

LIGHT_COLORS = {"白色", "米白色", "浅蓝色", "粉色", "黄色"}
HEAT_FRIENDLY = {"纯棉", "亚麻", "真丝", "棉麻"}
COLD_FRIENDLY = {"羊毛", "皮质", "混纺"}


def generate_outfit_options(
    items: list[dict[str, Any]],
    context: dict[str, Any],
    preference_weights: dict[str, float] | None = None,
    option_count: int = 3,
) -> list[dict[str, Any]]:
    preference_weights = preference_weights or {}
    buckets = _bucket_items(items)

    options: list[dict[str, Any]] = []
    for index in range(option_count):
        outfit = _build_one_option(index, buckets, context, preference_weights)
        outfit["id"] = _stable_outfit_id(outfit, context)
        outfit["title"] = OPTION_NAMES[index] if index < len(OPTION_NAMES) else f"Option {index + 1}"
        outfit["reason"] = _explain(outfit, context)
        outfit["missing_slots"] = _missing_slots(outfit)
        options.append(outfit)
    return options


def outfit_feature_keys(outfit: dict[str, Any]) -> list[str]:
    selected = outfit.get("items", {})
    keys: list[str] = []
    normalized_categories: list[str] = []
    styles: list[str] = []

    for item in selected.values():
        if not item:
            continue
        category = normalize_category(item)
        normalized_categories.append(category)
        styles.append(str(item.get("style", "")))
        keys.extend(
            [
                f"category:{category}",
                f"material:{item.get('material', '')}",
                f"color:{item.get('color', '')}",
                f"style:{item.get('style', '')}",
            ]
        )
        for tag in item.get("tags", []):
            keys.append(f"tag:{tag}")

    if "bottom" in normalized_categories and _has_style(styles, "运动"):
        keys.append("combo:skirt_or_pants+sneaker")
    if "onepiece" in normalized_categories and _has_style(styles, "运动"):
        keys.append("combo:dress+sneaker")
    if "outerwear" in normalized_categories and _has_style(styles, "优雅"):
        keys.append("combo:outerwear+elegant")
    return sorted(set(keys))


def normalize_category(item: dict[str, Any]) -> str:
    raw = str(item.get("category", "")).strip()
    if raw in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[raw]
    for key, normalized in CATEGORY_ALIASES.items():
        if key in raw:
            return normalized
    return "accessory"


def _bucket_items(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets = {key: [] for key in ["top", "bottom", "onepiece", "outerwear", "shoes", "bag", "accessory"]}
    for item in items:
        buckets.setdefault(normalize_category(item), []).append(item)
    return buckets


def _build_one_option(
    index: int,
    buckets: dict[str, list[dict[str, Any]]],
    context: dict[str, Any],
    preference_weights: dict[str, float],
) -> dict[str, Any]:
    top = _pick(buckets.get("top", []), "top", context, preference_weights, index)
    bottom = _pick(buckets.get("bottom", []), "bottom", context, preference_weights, index)
    onepiece = _pick(buckets.get("onepiece", []), "onepiece", context, preference_weights, index)
    outerwear = None

    use_onepiece = onepiece and (
        not top
        or not bottom
        or _score_item(onepiece, "onepiece", context, preference_weights)
        > (_score_item(top, "top", context, preference_weights) + _score_item(bottom, "bottom", context, preference_weights)) / 2
    )

    if _needs_outerwear(context):
        outerwear = _pick(buckets.get("outerwear", []), "outerwear", context, preference_weights, index)

    selected = {
        "onepiece": onepiece if use_onepiece else None,
        "top": None if use_onepiece else top,
        "bottom": None if use_onepiece else bottom,
        "outerwear": outerwear,
        "shoes": _pick(buckets.get("shoes", []), "shoes", context, preference_weights, index),
        "bag": _pick(buckets.get("bag", []), "bag", context, preference_weights, index),
        "accessory": _pick(buckets.get("accessory", []), "accessory", context, preference_weights, index),
    }

    return {
        "items": selected,
        "sections": {
            "衣服": [item for item in [selected["onepiece"], selected["top"], selected["bottom"], selected["outerwear"]] if item],
            "配饰": [item for item in [selected["accessory"]] if item],
            "鞋子": [item for item in [selected["shoes"]] if item],
            "包包": [item for item in [selected["bag"]] if item],
        },
    }


def _pick(
    candidates: list[dict[str, Any]],
    slot: str,
    context: dict[str, Any],
    preference_weights: dict[str, float],
    offset: int,
) -> dict[str, Any] | None:
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda item: (_score_item(item, slot, context, preference_weights), -int(item.get("wear_count", 0)), -int(item.get("id", 0))),
        reverse=True,
    )
    return ranked[offset % len(ranked)]


def _score_item(
    item: dict[str, Any],
    slot: str,
    context: dict[str, Any],
    preference_weights: dict[str, float],
) -> float:
    score = 10 if normalize_category(item) == slot else 0
    temperature = float(context.get("temperature", 24))
    weather = str(context.get("weather", "晴"))
    uv_index = float(context.get("uv_index", 0))
    sun_protection = bool(context.get("sun_protection"))
    occasion = str(context.get("occasion", "日常休闲"))
    carry_load = str(context.get("carry_load", "少量物品"))
    lucky_color = str(context.get("lucky_color") or "").strip()

    material = str(item.get("material", ""))
    color = str(item.get("color", ""))
    style = str(item.get("style", ""))
    tags = set(item.get("tags", []))

    if temperature >= 28:
        if material in HEAT_FRIENDLY:
            score += 3
        if material in COLD_FRIENDLY and slot != "bag":
            score -= 3
        if color in LIGHT_COLORS:
            score += 1.5
    elif temperature <= 12:
        if material in COLD_FRIENDLY:
            score += 3
        if slot == "outerwear":
            score += 2

    if "雨" in weather:
        if slot in {"outerwear", "shoes", "bag"}:
            score += 1.5
        if "防水" in tags or "尼龙" in material:
            score += 2

    if sun_protection or uv_index >= 7:
        if slot in {"outerwear", "accessory"}:
            score += 2
        if tags & {"防晒", "长袖", "帽子", "墨镜"}:
            score += 3
        if color in LIGHT_COLORS:
            score += 1

    score += OCCASION_STYLES.get(occasion, {}).get(style, 0)

    if slot == "bag":
        if carry_load == "需带电脑/文件":
            if tags & {"托特包", "双肩包", "可装电脑"}:
                score += 4
            if tags & {"手拿包", "小挎包"}:
                score -= 3
        elif carry_load == "少量物品":
            if tags & {"小挎包", "手拿包", "容量适中"}:
                score += 2
        elif carry_load == "运动装备" and tags & {"双肩包", "尼龙"}:
            score += 3

    if lucky_color:
        if lucky_color == color:
            score += 5
        elif lucky_color in color or color in lucky_color:
            score += 3

    for key in _item_feature_keys(item):
        score += preference_weights.get(key, 0)

    score -= min(int(item.get("wear_count", 0)), 20) * 0.04
    return score


def _item_feature_keys(item: dict[str, Any]) -> list[str]:
    keys = [
        f"category:{normalize_category(item)}",
        f"material:{item.get('material', '')}",
        f"color:{item.get('color', '')}",
        f"style:{item.get('style', '')}",
    ]
    keys.extend(f"tag:{tag}" for tag in item.get("tags", []))
    return keys


def _needs_outerwear(context: dict[str, Any]) -> bool:
    temperature = float(context.get("temperature", 24))
    weather = str(context.get("weather", "晴"))
    return temperature <= 18 or "雨" in weather or bool(context.get("sun_protection")) or float(context.get("uv_index", 0)) >= 7


def _missing_slots(outfit: dict[str, Any]) -> list[str]:
    items = outfit.get("items", {})
    missing = []
    if not items.get("onepiece") and (not items.get("top") or not items.get("bottom")):
        missing.append("衣服")
    for slot, label in [("shoes", "鞋子"), ("bag", "包包")]:
        if not items.get(slot):
            missing.append(label)
    return missing


def _explain(outfit: dict[str, Any], context: dict[str, Any]) -> str:
    parts: list[str] = []
    temperature = float(context.get("temperature", 24))
    weather = str(context.get("weather", "晴"))
    occasion = str(context.get("occasion", "日常休闲"))
    carry_load = str(context.get("carry_load", "少量物品"))
    lucky_color = str(context.get("lucky_color") or "").strip()

    if temperature >= 28:
        parts.append(f"今日 {temperature:.0f}°C 偏热，优先选择透气材质与浅色单品")
    elif temperature <= 12:
        parts.append(f"今日 {temperature:.0f}°C 偏冷，提高保暖材质与外套权重")
    else:
        parts.append(f"今日 {temperature:.0f}°C 体感适中，强调层次与舒适度")

    if "雨" in weather:
        parts.append("天气含雨，鞋包和外套更偏实用防护")
    if context.get("sun_protection") or float(context.get("uv_index", 0)) >= 7:
        parts.append("存在防晒需求，增加长袖、帽子或墨镜权重")
    if occasion:
        parts.append(f"场合为{occasion}，相应提升匹配风格")
    if carry_load == "需带电脑/文件":
        parts.append("携带电脑/文件，包袋优先托特包或双肩包")
    if lucky_color:
        parts.append(f"幸运色「{lucky_color}」在召回阶段获得加权")

    missing = _missing_slots(outfit)
    if missing:
        parts.append(f"当前衣橱缺少{','.join(missing)}，建议补录后获得完整方案")

    return "；".join(parts) + "。"


def _stable_outfit_id(outfit: dict[str, Any], context: dict[str, Any]) -> str:
    item_ids = [
        item.get("id")
        for item in outfit.get("items", {}).values()
        if item and item.get("id") is not None
    ]
    payload = {"items": item_ids, "context": context}
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"outfit_{digest[:12]}"


def _has_style(styles: list[str], target: str) -> bool:
    return any(target in style for style in styles)
