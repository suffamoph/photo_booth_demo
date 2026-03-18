from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.services.task_service import create_task, get_task, run_task

router = APIRouter(tags=["demo"])

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"


@router.post("/process")
async def process_request(
    background_tasks: BackgroundTasks,
    input_text: str = Form(...),
    size: str = Form("One inch\t\t(413, 295)"),
    bgcolor: str = Form("White"),
    photo: UploadFile = File(...),
) -> dict:
    saved_path: Path | None = None

    suffix = Path(photo.filename or "upload.jpg").suffix or ".jpg"
    filename = f"{uuid4()}{suffix}"
    saved_path = UPLOAD_DIR / filename
    content = await photo.read()
    saved_path.write_bytes(content)

    # Create task
    task = create_task(input_text=input_text, size=size, bgcolor=bgcolor)
    print(f"[DEBUG] Created task: {task.task_id}, input: {input_text}")
    
    # Use FastAPI BackgroundTasks (official way)
    background_tasks.add_task(run_task, task.task_id, saved_path)
    print(f"[DEBUG] Added background task for {task.task_id}")

    return {
        "task_id": task.task_id,
        "status": "queued",
        "message": "等待处理中...",
    }


@router.get("/tasks/{task_id}")
def task_detail(task_id: str) -> dict:
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "intent": task.intent,
        "confidence": task.confidence,
        "reason": task.reason,
        "response": task.response,
        "source": task.source,
        "model": task.model,
        "result": task.result,
    }


@router.get("/tasks/{task_id}/stream")
async def task_stream(task_id: str) -> StreamingResponse:
    async def event_generator():
        while True:
            task = get_task(task_id)
            if not task:
                payload = {"error": "Task not found"}
                yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break

            payload = {
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "intent": task.intent,
                "confidence": task.confidence,
                "reason": task.reason,
                "response": task.response,
                "source": task.source,
                "model": task.model,
                "result": task.result,
            }
            yield f"event: progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

            if task.status in {"done", "failed"}:
                break

            await asyncio.sleep(0.6)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
