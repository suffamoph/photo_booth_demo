from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib import parse, request
from uuid import uuid4


COMFY_BASE_URL = "http://127.0.0.1:8188"
BACKEND_BASE_URL = "http://127.0.0.1:8000"
WORKFLOW_FILE = Path(__file__).resolve().parents[1] / "workflows" / "idphoto_workflow_demo_api.json"
IP_GROUP_WORKFLOW_FILE = Path(__file__).resolve().parents[1] / "workflows" / "IP_group_workflow_demo.json"
UPLOAD_IMAGE_NODE_ID = "52"
PARAMS_NODE_ID = "46"
SINGLE_IMAGE_OUTPUT_NODE_ID = "54"
LAYOUT_IMAGE_OUTPUT_NODE_ID = "55"
IP_GROUP_USER_IMAGE_NODE_ID = "1"
IP_GROUP_ASSET_IMAGE_NODE_ID = "13"
IP_GROUP_OUTPUT_NODE_ID = "21"
REQUEST_TIMEOUT_SECONDS = 30

DEFAULT_SIZE = "One inch\t\t(413, 295)"
DEFAULT_BGCOLOR = "White"
ALLOWED_SIZES = {
	"One inch\t\t(413, 295)",
	"Two inches\t\t(626, 413)",
}
ALLOWED_BGCOLORS = {
	"White",
	"Blue",
	"Red",
	"Dark Blue",
	"Light Grey",
}


def _http_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
	req = request.Request(
		url,
		data=json.dumps(payload).encode("utf-8"),
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:  # nosec B310
		body = resp.read().decode("utf-8")
	parsed = json.loads(body)
	if not isinstance(parsed, dict):
		raise ValueError("ComfyUI response is not JSON object")
	return parsed


def _http_get_json(url: str) -> dict[str, Any]:
	with request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:  # nosec B310
		body = resp.read().decode("utf-8")
	parsed = json.loads(body)
	if not isinstance(parsed, dict):
		raise ValueError("ComfyUI response is not JSON object")
	return parsed


def _load_workflow_template() -> dict[str, Any]:
	with open(WORKFLOW_FILE, encoding="utf-8") as f:
		data = json.load(f)
	if not isinstance(data, dict):
		raise ValueError("Workflow template is not a JSON object")
	return data


def _load_ip_group_workflow_template() -> dict[str, Any]:
	with open(IP_GROUP_WORKFLOW_FILE, encoding="utf-8") as f:
		data = json.load(f)
	if not isinstance(data, dict):
		raise ValueError("IP group workflow template is not a JSON object")
	return data


def build_id_photo_workflow(uploaded_filename: str, size: str = DEFAULT_SIZE, bgcolor: str = DEFAULT_BGCOLOR) -> dict[str, Any]:
	workflow = deepcopy(_load_workflow_template())
	image_url = f"{BACKEND_BASE_URL}/uploads/{uploaded_filename}"
	normalized_size = size if size in ALLOWED_SIZES else DEFAULT_SIZE
	normalized_bgcolor = bgcolor if bgcolor in ALLOWED_BGCOLORS else DEFAULT_BGCOLOR

	# Node 52 in the current workflow is "Load Image From Url (mtb)".
	if UPLOAD_IMAGE_NODE_ID not in workflow or "inputs" not in workflow[UPLOAD_IMAGE_NODE_ID]:
		raise ValueError(f"Workflow node '{UPLOAD_IMAGE_NODE_ID}' with inputs is missing")
	if PARAMS_NODE_ID not in workflow or "inputs" not in workflow[PARAMS_NODE_ID]:
		raise ValueError(f"Workflow node '{PARAMS_NODE_ID}' with inputs is missing")

	workflow[UPLOAD_IMAGE_NODE_ID]["inputs"]["url"] = image_url
	workflow[PARAMS_NODE_ID]["inputs"]["size"] = normalized_size
	workflow[PARAMS_NODE_ID]["inputs"]["bgcolor"] = normalized_bgcolor
	return workflow


def queue_prompt(workflow: dict[str, Any]) -> str:
	payload = {
		"prompt": workflow,
		"client_id": str(uuid4()),
	}
	url = f"{COMFY_BASE_URL}/prompt"
	resp = _http_post_json(url, payload)
	prompt_id = str(resp.get("prompt_id", "")).strip()
	if not prompt_id:
		raise ValueError("ComfyUI did not return prompt_id")
	return prompt_id


def _extract_image_meta(history_item: dict[str, Any], node_id: str) -> dict[str, str] | None:
	outputs = history_item.get("outputs", {})
	if not isinstance(outputs, dict):
		return None

	node_output = outputs.get(node_id)
	if not isinstance(node_output, dict):
		return None

	images = node_output.get("images")
	if not isinstance(images, list) or not images:
		return None

	first = images[0]
	if not isinstance(first, dict):
		return None

	filename = str(first.get("filename", "")).strip()
	subfolder = str(first.get("subfolder", "")).strip()
	file_type = str(first.get("type", "output")).strip() or "output"
	if not filename:
		return None

	return {
		"filename": filename,
		"subfolder": subfolder,
		"type": file_type,
	}


def _build_view_url(image_meta: dict[str, str]) -> str:
	query = parse.urlencode(
		{
			"filename": image_meta["filename"],
			"subfolder": image_meta["subfolder"],
			"type": image_meta["type"],
		}
	)
	return f"{COMFY_BASE_URL}/view?{query}"


def run_id_photo_workflow(
	uploaded_filename: str,
	size: str = DEFAULT_SIZE,
	bgcolor: str = DEFAULT_BGCOLOR,
	timeout_seconds: int = 180,
) -> dict[str, str]:
	workflow = build_id_photo_workflow(uploaded_filename, size=size, bgcolor=bgcolor)
	prompt_id = queue_prompt(workflow)

	deadline = time.time() + timeout_seconds
	history_url = f"{COMFY_BASE_URL}/history/{prompt_id}"

	while time.time() < deadline:
		history = _http_get_json(history_url)
		history_item = history.get(prompt_id)
		if isinstance(history_item, dict):
			single_image_meta = _extract_image_meta(history_item, SINGLE_IMAGE_OUTPUT_NODE_ID)
			layout_image_meta = _extract_image_meta(history_item, LAYOUT_IMAGE_OUTPUT_NODE_ID)
			if single_image_meta and layout_image_meta:
				return {
					"prompt_id": prompt_id,
					"size": size if size in ALLOWED_SIZES else DEFAULT_SIZE,
					"bgcolor": bgcolor if bgcolor in ALLOWED_BGCOLORS else DEFAULT_BGCOLOR,
					"preview_url": _build_view_url(single_image_meta),
					"single_preview_url": _build_view_url(single_image_meta),
					"single_filename": single_image_meta["filename"],
					"layout_preview_url": _build_view_url(layout_image_meta),
					"layout_filename": layout_image_meta["filename"],
				}
		time.sleep(1.0)

	raise TimeoutError("ComfyUI generation timeout")


def build_ip_group_workflow(uploaded_filename: str, ip_asset_filename: str) -> dict[str, Any]:
	workflow = deepcopy(_load_ip_group_workflow_template())
	user_image_url = f"{BACKEND_BASE_URL}/uploads/{uploaded_filename}"
	ip_asset_url = f"{BACKEND_BASE_URL}/ip_assets/{ip_asset_filename}"

	if IP_GROUP_USER_IMAGE_NODE_ID not in workflow or "inputs" not in workflow[IP_GROUP_USER_IMAGE_NODE_ID]:
		raise ValueError(f"Workflow node '{IP_GROUP_USER_IMAGE_NODE_ID}' with inputs is missing")
	if IP_GROUP_ASSET_IMAGE_NODE_ID not in workflow or "inputs" not in workflow[IP_GROUP_ASSET_IMAGE_NODE_ID]:
		raise ValueError(f"Workflow node '{IP_GROUP_ASSET_IMAGE_NODE_ID}' with inputs is missing")

	workflow[IP_GROUP_USER_IMAGE_NODE_ID]["inputs"]["url"] = user_image_url
	workflow[IP_GROUP_ASSET_IMAGE_NODE_ID]["inputs"]["url"] = ip_asset_url
	return workflow


def run_ip_group_workflow(
	uploaded_filename: str,
	ip_asset_filename: str,
	timeout_seconds: int = 180,
) -> dict[str, str]:
	workflow = build_ip_group_workflow(uploaded_filename, ip_asset_filename)
	prompt_id = queue_prompt(workflow)

	deadline = time.time() + timeout_seconds
	history_url = f"{COMFY_BASE_URL}/history/{prompt_id}"

	while time.time() < deadline:
		history = _http_get_json(history_url)
		history_item = history.get(prompt_id)
		if isinstance(history_item, dict):
			group_image_meta = _extract_image_meta(history_item, IP_GROUP_OUTPUT_NODE_ID)
			if group_image_meta:
				return {
					"prompt_id": prompt_id,
					"preview_url": _build_view_url(group_image_meta),
					"group_filename": group_image_meta["filename"],
					"ip_asset_filename": ip_asset_filename,
				}
		time.sleep(1.0)

	raise TimeoutError("ComfyUI ip-group generation timeout")
