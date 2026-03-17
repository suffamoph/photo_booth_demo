const form = document.getElementById("demo-form");
const submitBtn = document.getElementById("submit-btn");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const intentBox = document.getElementById("intent-box");
const intentCode = document.getElementById("intent-code");
const intentLabel = document.getElementById("intent-label");
const intentConfidence = document.getElementById("intent-confidence");
const intentSource = document.getElementById("intent-source");
const preview = document.getElementById("preview");

let streamSource = null;

const INTENT_LABELS = {
  id_photo: "证件照",
  portrait: "写真",
  ip_group: "IP合影",
  virtual_checkin: "虚拟打卡",
  cloud_print: "云打印",
  chat: "兜底聊天",
};

function setProgress(value, text) {
  progressBar.style.width = `${value}%`;
  progressText.textContent = `${value}% - ${text}`;
}

function resetView() {
  setProgress(0, "等待开始");
  intentBox.textContent = "-";
  intentCode.textContent = "-";
  intentLabel.textContent = "-";
  intentConfidence.textContent = "-";
  intentSource.textContent = "-";
  preview.removeAttribute("src");
  preview.style.display = "none";
}

function renderIntent(data) {
  const code = data.intent || "-";
  const label = INTENT_LABELS[code] || "未知意图";
  const confidence =
    typeof data.confidence === "number"
      ? `${(data.confidence * 100).toFixed(1)}%`
      : "-";

  intentCode.textContent = code;
  intentLabel.textContent = label;
  intentConfidence.textContent = confidence;
  intentSource.textContent = data.source || "-";
}

function renderRawResult(data) {
  intentBox.textContent = JSON.stringify(data, null, 2);
}

function closeStream() {
  if (streamSource) {
    streamSource.close();
    streamSource = null;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  closeStream();
  resetView();

  submitBtn.disabled = true;
  submitBtn.textContent = "处理中...";

  const inputText = document.getElementById("input-text").value;
  const photoFile = document.getElementById("photo").files[0];

  const body = new FormData();
  body.append("input_text", inputText);
  if (photoFile) {
    body.append("photo", photoFile);
  }

  try {
    const resp = await fetch("/api/process", { method: "POST", body });
    if (!resp.ok) {
      throw new Error(`request failed: ${resp.status}`);
    }

    const data = await resp.json();
    renderRawResult(data);
    renderIntent(data);

    streamSource = new EventSource(`/api/tasks/${data.task_id}/stream`);
    streamSource.addEventListener("progress", (message) => {
      const payload = JSON.parse(message.data);
      setProgress(payload.progress, payload.message);
      renderRawResult(payload);
      renderIntent(payload);

      if (payload.result && payload.result.preview_url) {
        preview.src = payload.result.preview_url;
        preview.style.display = "block";
      }

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
    submitBtn.textContent = "开始处理";
  }
});
