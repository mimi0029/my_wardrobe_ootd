import unittest

from app.services.feedback import build_preference_updates
from app.services.recommender import generate_outfit_options


ITEMS = [
    {
        "id": 1,
        "image_url": "/x/linen.svg",
        "category": "上衣",
        "material": "亚麻",
        "color": "米白色",
        "style": "极简",
        "tags": ["长袖", "透气", "防晒"],
        "wear_count": 0,
    },
    {
        "id": 2,
        "image_url": "/x/trouser.svg",
        "category": "裤装",
        "material": "羊毛",
        "color": "藏青色",
        "style": "通勤",
        "tags": ["利落"],
        "wear_count": 0,
    },
    {
        "id": 3,
        "image_url": "/x/sneaker.svg",
        "category": "鞋子",
        "material": "织物",
        "color": "白色",
        "style": "运动",
        "tags": ["运动鞋"],
        "wear_count": 0,
    },
    {
        "id": 4,
        "image_url": "/x/tote.svg",
        "category": "包包",
        "material": "帆布",
        "color": "米白色",
        "style": "通勤",
        "tags": ["托特包", "可装电脑"],
        "wear_count": 0,
    },
    {
        "id": 5,
        "image_url": "/x/sunglasses.svg",
        "category": "配饰",
        "material": "树脂",
        "color": "黑色",
        "style": "极简",
        "tags": ["墨镜", "防晒"],
        "wear_count": 0,
    },
]


class RecommenderTest(unittest.TestCase):
    def test_generates_three_explainable_options(self):
        context = {
            "temperature": 30,
            "weather": "晴",
            "uv_index": 8,
            "sun_protection": True,
            "occasion": "职场通勤",
            "carry_load": "需带电脑/文件",
            "lucky_color": "米白色",
        }

        options = generate_outfit_options(ITEMS, context, option_count=3)

        self.assertEqual(len(options), 3)
        self.assertTrue(options[0]["id"].startswith("outfit_"))
        self.assertIn("防晒", options[0]["reason"])
        self.assertEqual(options[0]["items"]["bag"]["id"], 4)

    def test_negative_feedback_decreases_feature_weights(self):
        context = {
            "temperature": 24,
            "weather": "晴",
            "uv_index": 4,
            "sun_protection": False,
            "occasion": "日常休闲",
            "carry_load": "少量物品",
            "lucky_color": None,
        }
        outfit = generate_outfit_options(ITEMS, context, option_count=1)[0]

        updates = build_preference_updates(outfit, 1)

        self.assertLess(updates["style:运动"], 0)
        self.assertLess(updates["category:shoes"], 0)


if __name__ == "__main__":
    unittest.main()
