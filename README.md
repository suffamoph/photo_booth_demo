# 咔咔AI照相机优化项目（PM前期构思 Demo）

## 项目背景
本项目用于前期验证「自然语言输入 -> 意图理解 -> 任务调度 -> AIGC能力调用 -> 返回结果」的核心链路。

当前定位是 PM 阶段的小型本地 Demo，不追求最终效果质量，重点验证产品流程可行性和模块边界清晰性。

## 目标与范围
目标是在一台 PC 上跑通以下流程（以证件照场景为例）：
1. 用户输入自然语言。
2. 用户上传一张照片（模拟拍照输入）。
3. 后端完成意图识别与任务创建。
4. 前端实时看到任务进度。
5. 返回处理结果（当前 Demo 先返回预览，后续接入 ComfyUI 真正生成）。

## 当前实现状态
已实现一个可运行的最小版本：
1. 前端：文本输入、图片上传、任务进度展示、结果预览。
2. 后端：
   - 意图识别占位逻辑（关键词规则版）。
   - 异步任务调度占位逻辑（队列/进度模拟）。
   - SSE 实时进度推送。
3. 数据：本地保存上传图片并回显预览。

## 技术栈
1. Python + FastAPI（后端 API 与静态页面托管）
2. HTML + JS + CSS（前端页面）
3. 本地文件存储（Demo 阶段不引入数据库）

你的已有能力可在下一阶段接入：
1. Ollama / OpenAI 兼容 API（LLM 调用）
2. ComfyUI（证件照、写真等工作流）
3. 素材库（IP 形象、写真模板、虚拟背景）

## 目录结构
```
photo_booth_project/
├─ backend/
│  ├─ app.py
│  ├─ routes/
│  │  ├─ __init__.py
│  │  └─ demo.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ intent_service.py
│  │  └─ task_service.py
│  └─ data/
│     └─ uploads/
├─ frontend/
│  ├─ index.html
│  ├─ app.js
│  └─ styles.css
├─ requirements.txt
└─ README.md
```

## 快速开始
在项目根目录执行：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

浏览器访问：
`http://127.0.0.1:8000`

## LLM 意图识别
当前已启用 LLM 优先识别（Ollama qwen3.5:9b），失败自动回退到规则识别。

**配置说明**（硬编码在 `backend/services/intent_service.py`）：
- `PROVIDER = "ollama"`
- `MODEL = "qwen3.5:9b"`
- `BASE_URL = "http://127.0.0.1:11434"`
- `TIMEOUT_SECONDS = 20`
- `TEMPERATURE = 0.0`

若需修改 LLM 接入参数或切换模型，请直接编辑 `backend/services/intent_service.py` 顶部的配置常量。

## 可用接口（Demo）
1. `POST /api/process`
   - 入参：`input_text`（文本） + `photo`（可选图片）
   - 返回：`task_id`、识别意图、置信度、来源（`source`: `llm` / `rule` / `rule_fallback`）
2. `GET /api/tasks/{task_id}`
   - 返回任务当前状态
3. `GET /api/tasks/{task_id}/stream`
   - SSE 实时进度流

## 意图维护
建议将业务意图定义维护在独立文档中，作为 PM 与研发的统一口径：
[docs/intent-taxonomy.md](docs/intent-taxonomy.md)

## 后续迭代建议
按这个顺序推进，风险最低：
1. 接入 LLM 意图识别（替换关键词规则）：
   - 统一意图枚举：chat / id_photo / portrait / ip_group / virtual_checkin / cloud_print。
2. 接入 ComfyUI 证件照工作流：
   - 你补充 workflow JSON 与参数文档后，在 `task_service.py` 增加真实调用。
3. 增加素材管理层：
   - 先文件系统 + metadata JSON，稳定后再换数据库。
4. 增加模型与接口管理：
   - 抽象 provider（ollama / openai / comfyui）。
5. 增加任务持久化：
   - 再引入 SQLite（记录任务、输入、输出、耗时、错误）。

## PM 视角验收标准（建议）
1. 用户 10 秒内看到进度变化。
2. 任意文本输入都能被归入可解释的意图。
3. 上传图片后，流程不报错且能返回可视结果。
4. 异常时前端可读到错误信息。

## 说明
当前版本是「流程验证 Demo」，不是生产架构。
完成链路验证后，再做质量、并发、权限、安全与成本优化。