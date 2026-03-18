from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .comfy_service import run_id_photo_workflow, run_ip_group_workflow, run_portrait_workflow
from .intent_service import detect_intent


IP_ASSET_KEYWORD_MAP: list[tuple[list[str], str, str]] = [
    (["赫敏"], "ip_01_hermione.webp", "赫敏"),
    (["特朗普", "川普"], "ip_02_trump.webp", "特朗普"),
    (["钢铁侠", "ironman"], "ip_03_ironman.webp", "钢铁侠"),
    (["小黄人", "minion"], "ip_04_minion.webp", "小黄人"),
    (["马斯克", "musk"], "ip_05_musk.webp", "马斯克"),
    (["蜘蛛侠", "spiderman", "spider-man"], "ip_06_spiderman.webp", "蜘蛛侠"),
    (["哈利波特三人组", "哈利波特", "harry potter"], "ip_07_harry_potter_trio.webp", "哈利波特三人组"),
    (["赫敏2", "赫敏 第二张", "hermione 2"], "ip_08_hermione.webp", "赫敏(2)"),
    (["擎天柱", "optimus prime"], "ip_09_optimus_prime.webp", "擎天柱"),
    (["蜘蛛侠2", "蜘蛛侠 第二张", "spiderman 2"], "ip_10_spiderman.webp", "蜘蛛侠(2)"),
]

PORTRAIT_ASSET_KEYWORD_MAP: list[tuple[list[str], int, str, str]] = [
    (["male", "男", "男性", "古风", "国风"], 2, "portrait_01_male_gufeng.webp", "male 古风"),
    (["male", "男", "男性", "现代", "职场", "形象照", "西装"], 3, "portrait_02_male_modern_office_suit_headshot.webp", "male 现代 职场 形象照 西装"),
    (["female", "女", "女性", "法式", "田园"], 3, "portrait_03_female_french_pastoral.webp", "female 法式 田园"),
    (["female", "女", "女性", "民族"], 2, "portrait_04_female_ethnic_style.webp", "female 民族"),
    (["female", "女", "女性", "古装", "唐装"], 3, "portrait_05_female_tang_dynasty_hanfu.webp", "female 古装 唐装"),
    (["female", "女", "女性", "古装", "汉服"], 3, "portrait_06_female_hanfu_classic.webp", "female 古装 汉服"),
    (["male", "男", "男性", "古装", "皇帝"], 3, "portrait_07_male_emperor_costume.webp", "male 古装 皇帝"),
    (["female", "女", "女性", "现代", "清新", "纯真"], 3, "portrait_08_female_modern_fresh_innocent.webp", "female 现代 清新 纯真"),
    (["female", "女", "女性", "古装", "清宫", "故宫"], 3, "portrait_09_female_qing_palace_forbidden_city.webp", "female 古装 清宫 故宫"),
    (["female", "女", "女性", "现代", "雪天", "氛围"], 3, "portrait_10_female_modern_snow_atmosphere.webp", "female 现代 雪天 氛围"),
    (["male", "男", "男性", "现代"], 2, "portrait_11_male_modern_style.webp", "male 现代"),
    (["female", "女", "女性", "现代", "气质", "形象照"], 3, "portrait_12_female_modern_elegant_headshot.webp", "female 现代 气质 形象照"),
]


def _match_ip_asset(input_text: str) -> tuple[str, str] | None:
    normalized = (input_text or "").strip().lower()
    if not normalized:
        return None

    for keywords, filename, label in IP_ASSET_KEYWORD_MAP:
        if any(keyword.lower() in normalized for keyword in keywords):
            return filename, label

    return None


def _match_portrait_asset(input_text: str) -> tuple[str, str] | None:
    normalized = (input_text or "").strip().lower()
    if not normalized:
        return None

    best_match: tuple[int, float, str, str] | None = None
    for keywords, min_hits, filename, label in PORTRAIT_ASSET_KEYWORD_MAP:
        hits = sum(1 for keyword in keywords if keyword.lower() in normalized)
        if hits < min_hits:
            continue

        score_ratio = hits / max(len(keywords), 1)
        candidate = (hits, score_ratio, filename, label)
        if best_match is None or candidate[:2] > best_match[:2]:
            best_match = candidate

    if best_match is None:
        return None

    return best_match[2], best_match[3]


@dataclass
class TaskState:
    task_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "queued"
    intent: str = ""
    confidence: float = 0.0
    reason: str = ""
    response: str = ""
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
        task.response = intent_result.response
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
        elif task.intent == "ip_group" and uploaded_file is not None:
            matched_asset = _match_ip_asset(task.input_text)
            if matched_asset:
                ip_asset_filename, ip_asset_label = matched_asset
                task.progress = 35
                task.message = f"IP合影工作流准备中: {ip_asset_label}"
                print(f"[DEBUG] Preparing ComfyUI ip group workflow for {task_id}, asset: {ip_asset_filename}")
                time.sleep(0.4)

                task.progress = 55
                task.message = "已提交 ComfyUI，等待生成结果..."
                comfy_result = run_ip_group_workflow(uploaded_file.name, ip_asset_filename=ip_asset_filename)
                print(f"[DEBUG] ComfyUI ip-group done for {task_id}, prompt_id: {comfy_result.get('prompt_id')}")

                task.progress = 95
                task.message = "合影生成完成，整理结果中..."
                task.result = {
                    "type": "comfyui_ip_group",
                    "intent": task.intent,
                    "confidence": task.confidence,
                    "reason": task.reason,
                    "source": task.source,
                    "model": task.model,
                    "preview_url": comfy_result.get("preview_url"),
                    "comfy_prompt_id": comfy_result.get("prompt_id"),
                    "group_filename": comfy_result.get("group_filename"),
                    "ip_asset": comfy_result.get("ip_asset_filename"),
                    "note": f"已接入 IP 合影工作流，命中素材: {ip_asset_label}",
                }
            else:
                task.progress = 95
                task.message = "未命中 IP 素材关键词，回退演示流程"
                result_url = f"/uploads/{uploaded_file.name}"
                task.result = {
                    "type": "demo",
                    "intent": task.intent,
                    "confidence": task.confidence,
                    "reason": task.reason,
                    "source": task.source,
                    "model": task.model,
                    "preview_url": result_url,
                    "note": "IP 合影意图已命中，但未识别到素材关键词。",
                }
        elif task.intent == "portrait" and uploaded_file is not None:
            matched_asset = _match_portrait_asset(task.input_text)
            if matched_asset:
                portrait_asset_filename, portrait_asset_label = matched_asset
                task.progress = 35
                task.message = f"写真工作流准备中: {portrait_asset_label}"
                print(f"[DEBUG] Preparing ComfyUI portrait workflow for {task_id}, asset: {portrait_asset_filename}")
                time.sleep(0.4)

                task.progress = 55
                task.message = "已提交 ComfyUI，等待生成结果..."
                comfy_result = run_portrait_workflow(uploaded_file.name, portrait_asset_filename=portrait_asset_filename)
                print(f"[DEBUG] ComfyUI portrait done for {task_id}, prompt_id: {comfy_result.get('prompt_id')}")

                task.progress = 95
                task.message = "写真生成完成，整理结果中..."
                task.result = {
                    "type": "comfyui_portrait",
                    "intent": task.intent,
                    "confidence": task.confidence,
                    "reason": task.reason,
                    "source": task.source,
                    "model": task.model,
                    "preview_url": comfy_result.get("preview_url"),
                    "comfy_prompt_id": comfy_result.get("prompt_id"),
                    "output_filename": comfy_result.get("output_filename"),
                    "portrait_asset": comfy_result.get("portrait_asset_filename"),
                    "note": f"已接入 ComfyUI 写真工作流，命中模板: {portrait_asset_label}",
                }
            else:
                task.progress = 35
                task.message = "未命中写真关键词，使用默认模板"
                print(f"[DEBUG] Portrait keywords not matched for {task_id}, using default template")
                time.sleep(0.4)

                task.progress = 55
                task.message = "已提交 ComfyUI，等待生成结果..."
                comfy_result = run_portrait_workflow(uploaded_file.name)
                print(f"[DEBUG] ComfyUI portrait done for {task_id}, prompt_id: {comfy_result.get('prompt_id')}")

                task.progress = 95
                task.message = "写真生成完成，整理结果中..."
                task.result = {
                    "type": "comfyui_portrait",
                    "intent": task.intent,
                    "confidence": task.confidence,
                    "reason": task.reason,
                    "source": task.source,
                    "model": task.model,
                    "preview_url": comfy_result.get("preview_url"),
                    "comfy_prompt_id": comfy_result.get("prompt_id"),
                    "output_filename": comfy_result.get("output_filename"),
                    "portrait_asset": comfy_result.get("portrait_asset_filename"),
                    "note": "已接入 ComfyUI 写真工作流，未命中关键词时使用默认模板。",
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
