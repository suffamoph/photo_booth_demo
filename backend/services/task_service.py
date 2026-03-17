from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .intent_service import IntentResult


@dataclass
class TaskState:
    task_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "queued"
    intent: str = ""
    input_text: str = ""
    result: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


TASKS: dict[str, TaskState] = {}


def create_task(input_text: str, intent: IntentResult) -> TaskState:
    task_id = str(uuid4())
    task = TaskState(task_id=task_id, intent=intent.intent, input_text=input_text)
    TASKS[task_id] = task
    return task


async def run_task(task_id: str, uploaded_file: Path | None = None) -> None:
    task = TASKS[task_id]

    steps = [
        (10, "已接收任务，开始排队"),
        (30, "意图识别完成，正在准备参数"),
        (55, "任务调度中，准备调用生成能力"),
        (80, "生成处理中"),
        (100, "处理完成"),
    ]

    task.status = "running"
    for progress, message in steps:
        await asyncio.sleep(1.0)
        task.progress = progress
        task.message = message

    # Demo result: return uploaded image URL directly.
    result_url = f"/uploads/{uploaded_file.name}" if uploaded_file else None
    task.result = {
        "type": "demo",
        "intent": task.intent,
        "preview_url": result_url,
        "note": "当前为本地演示流程，后续可在此接入 ComfyUI 工作流。",
    }
    task.status = "done"


def get_task(task_id: str) -> TaskState | None:
    return TASKS.get(task_id)
