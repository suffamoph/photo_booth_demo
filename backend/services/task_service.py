from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .comfy_service import run_id_photo_workflow
from .intent_service import detect_intent


@dataclass
class TaskState:
    task_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "queued"
    intent: str = ""
    confidence: float = 0.0
    reason: str = ""
    source: str = ""
    model: str = ""
    input_text: str = ""
    size: str = "One inch\t\t(413, 295)"
    bgcolor: str = "White"
    result: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


TASKS: dict[str, TaskState] = {}


def create_task(input_text: str, size: str = "One inch\t\t(413, 295)", bgcolor: str = "White") -> TaskState:
    task_id = str(uuid4())
    task = TaskState(task_id=task_id, input_text=input_text, size=size, bgcolor=bgcolor)
    TASKS[task_id] = task
    return task


def run_task(task_id: str, uploaded_file: Path | None = None) -> None:
    """Run task synchronously (executed by BackgroundTasks)."""
    import time
    try:
        print(f"[DEBUG] run_task started for {task_id}")
        task = TASKS[task_id]
        task.status = "running"
        print(f"[DEBUG] Task status set to running: {task_id}")

        # Step 1: Intent detection (streaming)
        task.progress = 5
        task.message = "意图识别中..."
        print(f"[DEBUG] Detecting intent for: {task.input_text}")
        time.sleep(0.5)

        intent_result = detect_intent(task.input_text)
        task.intent = intent_result.intent
        task.confidence = intent_result.confidence
        task.reason = intent_result.reason
        task.source = intent_result.source
        task.model = intent_result.model
        task.progress = 20
        task.message = f"意图识别完成: {task.intent} ({task.confidence:.1%}) - {task.reason}"
        print(f"[DEBUG] Intent detected: {task.intent}, confidence: {task.confidence}")
        time.sleep(0.8)

        if task.intent == "id_photo" and uploaded_file is not None:
            task.progress = 35
            task.message = "证件照工作流准备中..."
            print(f"[DEBUG] Preparing ComfyUI id photo workflow for {task_id}")
            time.sleep(0.4)

            task.progress = 55
            task.message = "已提交 ComfyUI，等待生成结果..."
            comfy_result = run_id_photo_workflow(uploaded_file.name, size=task.size, bgcolor=task.bgcolor)
            print(f"[DEBUG] ComfyUI done for {task_id}, prompt_id: {comfy_result.get('prompt_id')}")

            task.progress = 95
            task.message = "生成完成，整理结果中..."
            task.result = {
                "type": "comfyui_id_photo",
                "intent": task.intent,
                "confidence": task.confidence,
                "reason": task.reason,
                "source": task.source,
                "model": task.model,
                "size": comfy_result.get("size"),
                "bgcolor": comfy_result.get("bgcolor"),
                "preview_url": comfy_result.get("preview_url"),
                "single_preview_url": comfy_result.get("single_preview_url"),
                "layout_preview_url": comfy_result.get("layout_preview_url"),
                "comfy_prompt_id": comfy_result.get("prompt_id"),
                "single_filename": comfy_result.get("single_filename"),
                "layout_filename": comfy_result.get("layout_filename"),
                "note": "已接入本地 ComfyUI 证件照工作流。",
            }
        else:
            # Temporary fallback for non-id-photo intents.
            steps = [
                (30, "意图识别完成，正在准备参数"),
                (55, "任务调度中，准备调用生成能力"),
                (80, "生成处理中"),
            ]

            for progress, message in steps:
                time.sleep(1.0)
                task.progress = progress
                task.message = message
                print(f"[DEBUG] Progress update {task_id}: {progress}% - {message}")

            result_url = f"/uploads/{uploaded_file.name}" if uploaded_file else None
            task.result = {
                "type": "demo",
                "intent": task.intent,
                "confidence": task.confidence,
                "reason": task.reason,
                "source": task.source,
                "model": task.model,
                "preview_url": result_url,
                "note": "当前仅证件照意图已接入 ComfyUI，其它意图仍走演示流程。",
            }

        task.progress = 100
        task.message = "处理完成"
        task.status = "done"
        print(f"[DEBUG] Task completed: {task_id}")
    except Exception as e:
        print(f"[ERROR] run_task failed: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        task = TASKS.get(task_id)
        if task:
            task.status = "failed"
            task.message = f"Error: {str(e)}"


def get_task(task_id: str) -> TaskState | None:
    return TASKS.get(task_id)
