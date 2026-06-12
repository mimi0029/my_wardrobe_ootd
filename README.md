# 智能衣橱与 OOTD 推荐系统

这是包含智能衣橱录入、场景化三套 OOTD 生成、可解释推荐理由，以及基于用户评分的偏好权重更新的衣橱现有衣物推荐系统。

## 功能模块

- 智能衣橱录入：上传服装图片，自动生成类别、材质、颜色、风格和标签；用户可直接编辑标签。
- 场景化推荐：根据温度、天气、UV、防晒需求、场合、携带物品和幸运色生成三套并列穿搭。
- 推荐解释：每套方案输出天气、场合、防晒、包袋容量、幸运色等加权原因。
- 反馈学习：1-5 星或快捷反馈会写入反馈日志，并把 Outfit 特征转成 Reward 更新偏好权重。
- 演示数据：内置 10 件演示单品，便于快速体验推荐闭环。

## 技术栈

- 后端：Python + FastAPI
- 数据：SQLite
- 前端：原生 HTML/CSS/JavaScript
- 视觉识别：本地启发式 fallback，`app/services/vision.py` 已预留视觉大模型接入点
- 天气 Agent：支持 OpenWeather API；未配置 Key 时使用手动参数
- 推荐策略：规则召回 + 标签权重排序 + 反馈权重增量

## 目录结构

```text
app/
  main.py                  FastAPI 入口与 API 路由
  database.py              SQLite 初始化与数据访问
  schemas.py               请求模型
  seed_data.py             演示衣橱
  services/
    vision.py              图像标签提取
    weather.py             天气 Agent
    recommender.py         OOTD 推荐器
    feedback.py            Reward/偏好更新
  static/
    index.html             前端页面
    styles.css             界面样式
    app.js                 前端交互
data/
  uploads/                 用户上传图片
tests/
  test_recommender.py      推荐与反馈单元测试
```

## 本地运行

```powershell
cd E:\Codex\wardrobe_ootd_mvp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`。

也可以运行：

```powershell
.\scripts\run_dev.ps1
```

## OpenWeather 配置

复制 `.env.example` 为 `.env`，填入：

```text
OPENWEATHER_API_KEY=你的_key
```

当前 MVP 的推荐表单以手动天气参数为主；`POST /api/weather` 已支持在有 Key 时按城市拉取实时天气。

## API 摘要

- `GET /api/items`：获取衣橱单品
- `POST /api/items`：上传图片并识别标签
- `PATCH /api/items/{item_id}`：编辑标签和结构化字段
- `DELETE /api/items/{item_id}`：删除单品
- `POST /api/outfits/recommend`：生成三套 OOTD
- `POST /api/feedback`：记录评分并更新偏好权重
- `GET /api/feedback/summary`：查看反馈日志
- `POST /api/demo/seed`：载入演示衣橱

## 测试

```powershell
python -m unittest discover -s tests
```

## 后续升级路径

- 将 `vision.py` 的 fallback 替换为 GPT-4V、Claude Vision、YOLO 或细分类模型。
- 将 `recommender.py` 中的权重排序升级为 Contextual Bandits，保留当前反馈日志作为训练数据。
- 增加用户体系，把 `preference_weights` 按用户维度隔离。
- 扩展 Outfit 表，缓存用户最终选择的方案并更新 `Wear_Count`。
