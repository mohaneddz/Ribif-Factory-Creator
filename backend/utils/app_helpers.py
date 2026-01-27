import json
import os
from typing import Any, Dict, Optional, Tuple, Union

from flask import request

from supabase_utils import (
    SUPABASE_BUCKET_FILES,
    SUPABASE_BUCKET_PUBLIC,
    build_name_timestamp_object_path,
    build_object_path,
    create_signed_url,
    get_public_url,
    insert_project,
    insert_project_file,
    upload_bytes,
    upload_file,
    upsert_project_settings,
)
from config import TEMPLATE_DIR
from utils.logger import get_logger
import math

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively replace NaN and Infinity with None to ensure JSON compliance.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj



def get_request_user_id() -> Optional[str]:
    return request.headers.get("x-user-id") or request.headers.get("X-User-Id")


def get_request_project_id(include_form: bool = False, include_json: bool = False) -> Optional[str]:
    project_id = request.headers.get("x-project-id") or request.headers.get("X-Project-Id")
    if include_form:
        project_id = project_id or request.form.get("project_id")
    if include_json and request.is_json:
        payload = request.get_json(silent=True) or {}
        project_id = project_id or payload.get("project_id") or payload.get("ribif_metadata", {}).get("project_id")
    return project_id


def get_pipeline_settings() -> dict:
    raw = None
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        raw = payload.get("pipeline_settings") or payload.get("settings")
    raw = raw or request.form.get("pipeline_settings") or request.form.get("settings")
    raw = raw or request.headers.get("x-pipeline-settings") or request.headers.get("X-Pipeline-Settings")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except Exception as e:
            logger = get_logger("app_helpers")
            logger.warning(f"Failed to parse settings JSON: {e}")
            return {}
    return {}


def ensure_project_id(client, project_id: Optional[str], owner_id: Optional[str], fallback_name: str) -> Optional[str]:
    if project_id:
        return project_id
    if not client:
        return None
    return insert_project(client, owner_id, fallback_name, metadata={"source": "module1_upload"})


def store_project_settings(client, project_id: Optional[str], settings: dict, owner_id: Optional[str]) -> None:
    if not client or not project_id or not settings:
        return
    upsert_project_settings(client, project_id, settings, updated_by=owner_id)


def upload_and_register_file(
    client,
    project_id: str,
    owner_id: Optional[str],
    local_path: str,
    category: str,
    label: Optional[str] = None,
    bucket: Optional[str] = None,
    object_path: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if not client:
        return None, None
    bucket_id = bucket or SUPABASE_BUCKET_FILES
    object_path = object_path or build_object_path(project_id, category, os.path.basename(local_path))
    upload_file(client, bucket_id, object_path, local_path)
    file_id = insert_project_file(
        client=client,
        project_id=project_id,
        owner_id=owner_id,
        bucket=bucket_id,
        object_path=object_path,
        mime_type=None,
        size_bytes=os.path.getsize(local_path),
        category=category,
        label=label,
        metadata={},
    )
    # Generate signed_url safely
    signed_url = None
    try:
        signed_url = create_signed_url(client, bucket_id, object_path)
    except Exception as e:
        logger = get_logger("app_helpers")
        logger.warning(f"Failed to create signed URL: {e}")
    
    if not signed_url:
        try:
            signed_url = get_public_url(client, bucket_id, object_path)
        except Exception as e:
            logger = get_logger("app_helpers")
            logger.warning(f"Failed to generate public URL: {e}")
    logger = get_logger("app_helpers")
    logger.info("Uploaded %s to Supabase: %s (file_id=%s) category=%s", label or os.path.basename(local_path), signed_url, file_id, category)
    return file_id, signed_url


def upload_bytes_and_register_file(
    client,
    project_id: str,
    owner_id: Optional[str],
    data: bytes,
    filename: str,
    category: str,
    content_type: str,
    label: Optional[str] = None,
    bucket: Optional[str] = None,
    object_path: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Upload bytes directly to Supabase (no local file needed)."""
    if not client:
        return None, None
    bucket_id = bucket or SUPABASE_BUCKET_FILES
    object_path = object_path or build_object_path(project_id, category, filename)
    upload_bytes(client, bucket_id, object_path, data, content_type)
    file_id = insert_project_file(
        client=client,
        project_id=project_id,
        owner_id=owner_id,
        bucket=bucket_id,
        object_path=object_path,
        mime_type=content_type,
        size_bytes=len(data),
        category=category,
        label=label,
        metadata={},
    )
    signed_url = None
    try:
        signed_url = create_signed_url(client, bucket_id, object_path)
    except Exception as e:
        logger = get_logger("app_helpers")
        logger.warning(f"Failed to create signed URL: {e}")
    if not signed_url:
        try:
            signed_url = get_public_url(client, bucket_id, object_path)
        except Exception as e:
            logger = get_logger("app_helpers")
            logger.warning(f"Failed to generate public URL: {e}")
    logger = get_logger("app_helpers")
    logger.info("Uploaded %s to Supabase: %s (file_id=%s) category=%s", label or filename, signed_url, file_id, category)
    return file_id, signed_url


def upload_with_name_timestamp(
    client,
    project_id: str,
    owner_id: Optional[str],
    local_path: str,
    category: str,
    label: Optional[str] = None,
    bucket: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not client:
        return None, None, None
    bucket_id = bucket or SUPABASE_BUCKET_FILES
    object_path = build_name_timestamp_object_path(project_id, category, os.path.basename(local_path))
    file_id, signed_url = upload_and_register_file(
        client=client,
        project_id=project_id,
        owner_id=owner_id,
        local_path=local_path,
        category=category,
        label=label,
        bucket=bucket_id,
        object_path=object_path,
    )
    return file_id, signed_url, object_path


def load_template_payload(name: str) -> Optional[Dict[str, Any]]:
    if not TEMPLATE_DIR.exists():
        return None
    template_path = TEMPLATE_DIR / f"{name}.json"
    if not template_path.exists():
        return None
    try:
        return json.loads(template_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger = get_logger("app_helpers")
        logger.warning(f"Failed to load template {name}: {e}")
        return None



def insert_machine_assets(client, machine_id: str, file_id: str, asset_type: str, label: Optional[str] = None) -> None:
    # No-op: Data is stored in JSONB columns in projects table
    pass


def insert_machines_from_stage(client, project_id: str, machines: list, image_meta: dict) -> Dict[str, str]:
    # No-op: Data is stored in projects.module1_data
    return {}


def insert_tco_details(client, tco_run_id: str, tco_data: dict) -> None:
    # No-op: Data is stored in projects.module6_data
    pass


def get_project_machines(client, project_id: str) -> Dict[str, str]:
    # No-op
    return {}


def upsert_supplier(client, name: str, website: Optional[str], region: Optional[str], metadata: Optional[dict] = None) -> Optional[str]:
    # No-op: data stored in module4_data
    return None


def insert_machine_supplier(
    client,
    machine_id: str,
    supplier_id: str,
    supplier_payload: dict,
    metadata: Optional[dict] = None,
) -> None:
    # No-op
    pass
