const form = document.getElementById("demo-form");
const submitBtn = document.getElementById("submit-btn");
const messages = document.getElementById("messages");
const inputText = document.getElementById("input-text");
const photoInput = document.getElementById("photo");
const sizeSelect = document.getElementById("size-select");
const bgcolorSelect = document.getElementById("bgcolor-select");
const composerPreviewWrap = document.getElementById("composer-preview-wrap");
const composerPreviewButton = document.getElementById("composer-preview-button");
const composerPreviewRemove = document.getElementById("composer-preview-remove");
const composerPreviewImage = document.getElementById("composer-preview-image");
const lightbox = document.getElementById("lightbox");
const lightboxImage = document.getElementById("lightbox-image");
const lightboxClose = document.getElementById("lightbox-close");
const jsonModal = document.getElementById("json-modal");
const jsonModalClose = document.getElementById("json-modal-close");
const jsonModalContent = document.getElementById("json-modal-content");

let streamSource = null;
let activeReplyView = null;
let composerPreviewUrl = "";

const INTENT_LABELS = {
  id_photo: "证件照",
  portrait: "写真",
  ip_group: "IP合影",
  virtual_checkin: "虚拟打卡",
  cloud_print: "云打印",
  chat: "兜底聊天",
};

function setProgress(value, text) {
  if (!activeReplyView) {
    return;
  }

  activeReplyView.progressBar.style.width = `${value}%`;
  activeReplyView.progressText.textContent = `${value}% - ${text}`;
}

function renderIntent(data) {
  if (!activeReplyView) {
    return;
  }

  const code = typeof data.intent === "string" ? data.intent.trim() : "";
  if (!code) {
    activeReplyView.intentCard.style.display = "none";
    return;
  }

  const label = INTENT_LABELS[code] || "未知意图";
  const confidence =
    typeof data.confidence === "number"
      ? `${(data.confidence * 100).toFixed(1)}%`
      : "-";

  activeReplyView.intentCard.style.display = "flex";
  activeReplyView.intentMerged.textContent = `${code} ${label}`;
  activeReplyView.intentConfidence.textContent = confidence;
  activeReplyView.intentSource.textContent = data.source || "-";

  if (code === "chat") {
    activeReplyView.previewSection.hidden = true;
    activeReplyView.preview.removeAttribute("src");
    activeReplyView.preview.style.display = "none";
    activeReplyView.layoutPreview.removeAttribute("src");
    activeReplyView.layoutPreview.style.display = "none";
  }
}

function renderRawResult(data) {
  if (!activeReplyView) {
    return;
  }

  activeReplyView.rawJsonState.value = JSON.stringify(data, null, 2);
  activeReplyView.resultButton.disabled = false;
}

function closeStream() {
  if (streamSource) {
    streamSource.close();
    streamSource = null;
  }
}

function openLightbox(image) {
  if (!image || !image.src) {
    return;
  }

  lightboxImage.src = image.src;
  lightboxImage.alt = image.alt;
  lightbox.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  lightbox.hidden = true;
  lightboxImage.removeAttribute("src");
  lightboxImage.alt = "大图预览";
  document.body.style.overflow = "";
}

function openJsonModal(rawJson) {
  jsonModalContent.textContent = rawJson || "-";
  jsonModal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeJsonModal() {
  jsonModal.hidden = true;
  jsonModalContent.textContent = "-";
  document.body.style.overflow = "";
}

function clearComposerPreview() {
  if (composerPreviewUrl) {
    URL.revokeObjectURL(composerPreviewUrl);
    composerPreviewUrl = "";
  }

  composerPreviewImage.removeAttribute("src");
  composerPreviewWrap.hidden = true;
}

function updateComposerPreview(file) {
  clearComposerPreview();
  if (!file) {
    return;
  }

  composerPreviewUrl = URL.createObjectURL(file);
  composerPreviewImage.src = composerPreviewUrl;
  composerPreviewWrap.hidden = false;
}

lightboxClose.addEventListener("click", closeLightbox);
jsonModalClose.addEventListener("click", closeJsonModal);

lightbox.addEventListener("click", (event) => {
  if (event.target === lightbox) {
    closeLightbox();
  }
});

jsonModal.addEventListener("click", (event) => {
  if (event.target === jsonModal) {
    closeJsonModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !lightbox.hidden) {
    closeLightbox();
  }

  if (event.key === "Escape" && !jsonModal.hidden) {
    closeJsonModal();
  }
});

composerPreviewButton.addEventListener("click", () => openLightbox(composerPreviewImage));
composerPreviewRemove.addEventListener("click", () => {
  photoInput.value = "";
  clearComposerPreview();
});

photoInput.addEventListener("change", () => {
  updateComposerPreview(photoInput.files[0]);
});

inputText.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (!submitBtn.disabled && inputText.value.trim()) {
      form.requestSubmit();
    }
  }
});

function scrollMessagesToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function createPreviewCard(title, alt) {
  const figure = document.createElement("figure");
  figure.className = "preview-card";

  const button = document.createElement("button");
  button.className = "preview-button";
  button.type = "button";
  button.setAttribute("aria-label", `查看${title}大图`);

  const image = document.createElement("img");
  image.alt = alt;
  image.className = "preview-image";

  button.addEventListener("click", () => openLightbox(image));
  button.appendChild(image);
  figure.appendChild(button);

  return { figure, image };
}

function createUserMessage(text, photoFile) {
  const row = document.createElement("article");
  row.className = "message-row user-row";

  const bubble = document.createElement("div");
  bubble.className = "bubble user-bubble";

  const body = document.createElement("p");
  body.className = "message-text";
  body.textContent = text;
  bubble.appendChild(body);

  if (photoFile) {
    const previewButton = document.createElement("button");
    previewButton.className = "user-upload-preview";
    previewButton.type = "button";
    previewButton.setAttribute("aria-label", `查看已上传图片 ${photoFile.name}`);

    const previewImage = document.createElement("img");
    previewImage.className = "user-upload-preview-image";
    previewImage.alt = `已上传图片 ${photoFile.name}`;
    previewImage.src = URL.createObjectURL(photoFile);

    previewButton.addEventListener("click", () => openLightbox(previewImage));
    previewButton.appendChild(previewImage);
    bubble.appendChild(previewButton);

    const attachment = document.createElement("p");
    attachment.className = "message-meta";
    attachment.textContent = photoFile.name;
    bubble.appendChild(attachment);
  }

  row.appendChild(bubble);
  messages.appendChild(row);
}

function createAssistantMessage() {
  const row = document.createElement("article");
  row.className = "message-row assistant-row";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "咔";

  const bubble = document.createElement("div");
  bubble.className = "bubble assistant-bubble";

  const progressTrack = document.createElement("div");
  progressTrack.className = "progress-track";
  const progressBar = document.createElement("div");
  progressBar.className = "progress-bar";
  progressTrack.appendChild(progressBar);
  bubble.appendChild(progressTrack);

  const progressText = document.createElement("p");
  progressText.className = "message-meta";
  progressText.textContent = "0% - 等待开始";
  bubble.appendChild(progressText);

  const intentCard = document.createElement("div");
  intentCard.className = "intent-card";
  intentCard.style.display = "none";
  const rawJsonState = { value: "-" };
  intentCard.innerHTML = `
    <p class="intent-item intent-main"><strong>意图</strong><span data-role="intent-merged">-</span></p>
    <p class="intent-item"><strong>置信度</strong><span data-role="intent-confidence">-</span></p>
    <p class="intent-item"><strong>来源</strong><span data-role="intent-source">-</span></p>
  `;

  const resultButton = document.createElement("button");
  resultButton.className = "intent-item intent-action";
  resultButton.type = "button";
  resultButton.disabled = true;
  resultButton.innerHTML = "<strong>结果</strong><span>查看 JSON</span>";
  resultButton.addEventListener("click", () => openJsonModal(rawJsonState.value));
  intentCard.appendChild(resultButton);

  bubble.appendChild(intentCard);

  const previewSection = document.createElement("div");
  previewSection.hidden = true;

  const previewGrid = document.createElement("div");
  previewGrid.className = "preview-grid";
  const singlePreview = createPreviewCard("单张证件照", "单张证件照预览");
  const layoutPreview = createPreviewCard("拼版 Layout", "拼版预览");
  previewGrid.appendChild(singlePreview.figure);
  previewGrid.appendChild(layoutPreview.figure);
  previewSection.appendChild(previewGrid);
  bubble.appendChild(previewSection);

  row.appendChild(avatar);
  row.appendChild(bubble);
  messages.appendChild(row);

  return {
    progressBar,
    progressText,
    intentCard,
    intentMerged: intentCard.querySelector('[data-role="intent-merged"]'),
    intentConfidence: intentCard.querySelector('[data-role="intent-confidence"]'),
    intentSource: intentCard.querySelector('[data-role="intent-source"]'),
    resultButton,
    rawJsonState,
    previewSection,
    preview: singlePreview.image,
    layoutPreview: layoutPreview.image,
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  closeStream();
  closeLightbox();
  closeJsonModal();

  submitBtn.disabled = true;
  submitBtn.textContent = "处理中...";

  const inputValue = inputText.value;
  const photoFile = photoInput.files[0];

  createUserMessage(inputValue, photoFile);
  activeReplyView = createAssistantMessage();
  scrollMessagesToBottom();

  const body = new FormData();
  body.append("input_text", inputValue);
  body.append("size", sizeSelect.value);
  body.append("bgcolor", bgcolorSelect.value);
  if (photoFile) {
    body.append("photo", photoFile);
  }

  inputText.value = "";
  photoInput.value = "";
  clearComposerPreview();

  try {
    const resp = await fetch("/api/process", { method: "POST", body });
    if (!resp.ok) {
      throw new Error(`request failed: ${resp.status}`);
    }

    const data = await resp.json();
    renderRawResult(data);

    streamSource = new EventSource(`/api/tasks/${data.task_id}/stream`);
    streamSource.addEventListener("progress", (message) => {
      const payload = JSON.parse(message.data);
      setProgress(payload.progress, payload.message);
      renderRawResult(payload);
      renderIntent(payload);

      if (payload.result && payload.result.preview_url) {
        activeReplyView.previewSection.hidden = false;
        activeReplyView.preview.src = payload.result.preview_url;
        activeReplyView.preview.style.display = "block";
      }

      if (payload.result && payload.result.layout_preview_url) {
        activeReplyView.previewSection.hidden = false;
        activeReplyView.layoutPreview.src = payload.result.layout_preview_url;
        activeReplyView.layoutPreview.style.display = "block";
      }

      scrollMessagesToBottom();

      if (payload.status === "done" || payload.status === "failed") {
        closeStream();
      }
    });

    streamSource.addEventListener("error", () => {
      closeStream();
      setProgress(0, "流连接异常");
    });
  } catch (error) {
    setProgress(0, `请求失败: ${error.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "发送";
  }
});
