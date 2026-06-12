const state = {
  items: [],
  lastRecommendation: null,
};

const api = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `请求失败：${response.status}`);
  }
  return response.json();
};

const toast = (message) => {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 2600);
};

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
    if (button.dataset.tab === "feedback") loadFeedback();
  });
});

const renderItems = () => {
  const grid = document.getElementById("itemGrid");
  grid.innerHTML = "";

  if (!state.items.length) {
    grid.innerHTML = '<div class="empty">衣橱为空</div>';
    return;
  }

  const template = document.getElementById("itemCardTemplate");
  state.items.forEach((item) => {
    const card = template.content.firstElementChild.cloneNode(true);
    card.querySelector(".item-image").src = item.image_url;
    card.querySelector(".item-image").alt = `${item.color}${item.category}`;
    card.querySelector('[data-field="category"]').value = item.category;
    card.querySelector('[data-field="material"]').value = item.material;
    card.querySelector('[data-field="color"]').value = item.color;
    card.querySelector('[data-field="style"]').value = item.style;
    card.querySelector('[data-field="tags"]').value = (item.tags || []).join(", ");
    card.querySelector(".badge-row").innerHTML = (item.tags || [])
      .map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`)
      .join("");
    card.querySelector(".save-item").addEventListener("click", () => saveItem(card, item.id));
    card.querySelector(".delete-item").addEventListener("click", () => deleteItem(item.id));
    grid.appendChild(card);
  });
};

const loadItems = async () => {
  state.items = await api("/api/items");
  renderItems();
};

const saveItem = async (card, id) => {
  const payload = {};
  card.querySelectorAll("[data-field]").forEach((input) => {
    const field = input.dataset.field;
    payload[field] = field === "tags"
      ? input.value.split(",").map((tag) => tag.trim()).filter(Boolean)
      : input.value.trim();
  });
  await api(`/api/items/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  toast("单品已更新");
  await loadItems();
};

const deleteItem = async (id) => {
  await api(`/api/items/${id}`, { method: "DELETE" });
  toast("单品已删除");
  await loadItems();
};

document.getElementById("uploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = document.getElementById("imageFile").files[0];
  if (!file) {
    toast("请选择图片");
    return;
  }
  const formData = new FormData();
  formData.append("image", file);
  await api("/api/items", { method: "POST", body: formData });
  event.target.reset();
  toast("识别完成");
  await loadItems();
});

document.getElementById("seedDemo").addEventListener("click", async () => {
  const result = await api("/api/demo/seed", { method: "POST" });
  state.items = result.items;
  renderItems();
  toast(`已载入 ${result.created} 件演示单品`);
});

document.getElementById("recommendForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    temperature: Number(form.get("temperature")),
    weather: form.get("weather"),
    uv_index: Number(form.get("uv_index")),
    sun_protection: form.get("sun_protection") === "on",
    occasion: form.get("occasion"),
    carry_load: form.get("carry_load"),
    lucky_color: form.get("lucky_color") || null,
  };
  const data = await api("/api/outfits/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.lastRecommendation = data;
  renderOutfits(data.options, data.context);
});

const renderOutfits = (options, context) => {
  const grid = document.getElementById("outfitGrid");
  grid.innerHTML = "";

  if (!options.length) {
    grid.innerHTML = '<div class="empty">暂无方案</div>';
    return;
  }

  options.forEach((outfit) => {
    const card = document.createElement("article");
    card.className = "outfit-card";
    card.innerHTML = `
      <h3>${escapeHtml(outfit.title)}</h3>
      ${Object.entries(outfit.sections).map(([title, items]) => renderSection(title, items)).join("")}
      <p class="reason">${escapeHtml(outfit.reason)}</p>
      <div class="feedback-actions" aria-label="星级打分">
        ${[1, 2, 3, 4, 5].map((score) => `<button type="button" data-score="${score}">${"★".repeat(score)}</button>`).join("")}
      </div>
      <div class="reaction-row">
        <button type="button" data-reaction="喜欢">喜欢</button>
        <button type="button" data-reaction="一般">一般</button>
        <button type="button" data-reaction="不喜欢">不喜欢</button>
      </div>
    `;
    card.querySelectorAll("[data-score]").forEach((button) => {
      button.addEventListener("click", () => sendFeedback(outfit, context, Number(button.dataset.score), null));
    });
    card.querySelectorAll("[data-reaction]").forEach((button) => {
      const map = { "喜欢": 5, "一般": 3, "不喜欢": 1 };
      button.addEventListener("click", () => sendFeedback(outfit, context, map[button.dataset.reaction], button.dataset.reaction));
    });
    grid.appendChild(card);
  });
};

const renderSection = (title, items) => `
  <section class="outfit-section">
    <p class="section-title">${escapeHtml(title)}</p>
    ${items.length ? items.map(renderPiece).join("") : '<p class="reason">待补录</p>'}
  </section>
`;

const renderPiece = (item) => `
  <div class="piece">
    <img src="${item.image_url}" alt="${escapeHtml(item.color)}${escapeHtml(item.category)}" />
    <div>
      <strong>${escapeHtml(item.color)} ${escapeHtml(item.category)}</strong>
      <small>${escapeHtml(item.material)} · ${escapeHtml(item.style)}</small>
    </div>
  </div>
`;

const sendFeedback = async (outfit, context, score, reaction) => {
  const payload = {
    outfit_id: outfit.id,
    outfit,
    context,
    score,
    reaction,
  };
  await api("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  toast("反馈已记录，偏好权重已更新");
};

const loadFeedback = async () => {
  const rows = await api("/api/feedback/summary");
  const list = document.getElementById("feedbackList");
  list.innerHTML = rows.length
    ? rows.map((row) => `
      <div class="feedback-entry">
        <strong>${escapeHtml(row.outfit_id)}</strong>
        <span>${row.user_score} 星</span>
        <span>${escapeHtml(row.reaction || "星级反馈")}</span>
      </div>
    `).join("")
    : '<div class="empty">暂无反馈</div>';
};

document.getElementById("refreshFeedback").addEventListener("click", loadFeedback);

const escapeHtml = (value) => String(value ?? "")
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#039;");

loadItems().catch((error) => toast(error.message));
