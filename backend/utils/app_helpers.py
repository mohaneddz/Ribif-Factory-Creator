import json
import os
from typing import Any, Dict, Optional, Tuple

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
    upload_file,
    upsert_project_settings,
)
from config import TEMPLATE_DIR
from utils.logger import get_logger


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
        except Exception:
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
    logger = get_logger("app_helpers")
    logger.info("Uploaded %s to Supabase: %s (file_id=%s) category=%s", label or os.path.basename(local_path), signed_url, file_id, category)
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
    except Exception:
        return None


def insert_machine_assets(client, machine_id: str, file_id: str, asset_type: str, label: Optional[str] = None) -> None:
    if not client or not machine_id or not file_id:
        return
    client.table("machine_assets").insert({
        "machine_id": machine_id,
        "file_id": file_id,
        "asset_type": asset_type,
        "label": label,
        "metadata": {},
    }).execute()


def insert_machines_from_stage(client, project_id: str, machines: list, image_meta: dict) -> Dict[str, str]:
    if not client or not machines:
        return {}
    rows = []
    for m in machines:
        name = m.get("nom_machine") or m.get("name") or "Machine"
        meta = image_meta.get(name, {}) if image_meta else {}
        rows.append({
            "project_id": project_id,
            "name": name,
            "machine_type": m.get("type"),
            "manufacturer": m.get("fabricant_recommande"),
            "quantity": m.get("quantite_necessaire", 1),
            "use": m.get("use"),
            "specifications": m.get("specifications", {}) or {},
            "performance": m.get("performance", {}) or {},
            "source_reference": m.get("source_reference"),
            "metadata": meta or {},
        })
    res = client.table("machines").insert(rows).execute()
    data = getattr(res, "data", None) or []
    return {row.get("name"): row.get("id") for row in data if row.get("name")}


def insert_tco_details(client, tco_run_id: str, tco_data: dict) -> None:
    if not client or not tco_run_id:
        return
    machine_rows = []
    for m in tco_data.get("machine_tco", []) or []:
        machine_rows.append({
            "tco_run_id": tco_run_id,
            "machine_name": m.get("machine_name") or m.get("name"),
            "category": m.get("category"),
            "manufacturer": m.get("manufacturer"),
            "initial_cost": m.get("initial_cost"),
            "operations_cost": m.get("operations_cost"),
            "maintenance_cost": m.get("maintenance_cost"),
            "downtime_cost": m.get("downtime_cost"),
            "resale_value": m.get("resale_value"),
            "total_tco": m.get("total_tco"),
            "annual_tco": m.get("annual_tco"),
            "lifetime_years": m.get("lifetime_years"),
            "cost_breakdown": m.get("cost_breakdown"),
            "metadata": {},
        })
    if machine_rows:
        client.table("tco_machines").insert(machine_rows).execute()

    product_rows = []
    for p in tco_data.get("product_tco", []) or []:
        product_rows.append({
            "tco_run_id": tco_run_id,
            "product_name": p.get("nom_produit") or p.get("product_name"),
            "category": p.get("categorie") or p.get("category"),
            "landing_cost": p.get("landing_cost"),
            "holding_cost": p.get("holding_cost"),
            "quality_cost": p.get("quality_cost"),
            "administrative_cost": p.get("administrative_cost"),
            "total_tco": p.get("total_tco"),
            "metadata": {},
        })
    if product_rows:
        client.table("tco_products").insert(product_rows).execute()

    raw_rows = []
    for r in tco_data.get("raw_materials_tco", []) or []:
        raw_rows.append({
            "tco_run_id": tco_run_id,
            "material_name": r.get("nom_materiau") or r.get("material_name"),
            "material_type": r.get("type_materiau") or r.get("material_type"),
            "total_tco": r.get("total_tco"),
            "annual_cost": r.get("annual_cost"),
            "transport_cost": r.get("transport_cost"),
            "storage_cost": r.get("storage_cost"),
            "wastage_cost": r.get("wastage_cost"),
            "estimation_confidence": r.get("estimation_confidence"),
            "metadata": {},
        })
    if raw_rows:
        client.table("tco_raw_materials").insert(raw_rows).execute()

    annual_rows = []
    for a in tco_data.get("annual_tco", []) or []:
        annual_rows.append({
            "tco_run_id": tco_run_id,
            "year": a.get("year"),
            "machines_tco": a.get("machines_tco"),
            "products_tco": a.get("products_tco"),
            "raw_materials_tco": a.get("raw_materials_tco"),
            "total_tco": a.get("total_tco"),
            "cumulative_tco": a.get("cumulative_tco"),
            "metadata": {},
        })
    if annual_rows:
        client.table("tco_annual").insert(annual_rows).execute()


def get_project_machines(client, project_id: str) -> Dict[str, str]:
    if not client or not project_id:
        return {}
    res = client.table("machines").select("id,name").eq("project_id", project_id).execute()
    data = getattr(res, "data", None) or []
    return {row.get("name"): row.get("id") for row in data if row.get("name")}


def upsert_supplier(client, name: str, website: Optional[str], region: Optional[str], metadata: Optional[dict] = None) -> Optional[str]:
    if not client or not name:
        return None
    query = client.table("suppliers").select("id").eq("name", name)
    if website:
        query = query.eq("website", website)
    res = query.execute()
    data = getattr(res, "data", None) or []
    if data:
        return data[0].get("id")
    payload = {
        "name": name,
        "website": website,
        "region": region,
        "metadata": metadata or {},
    }
    res = client.table("suppliers").insert(payload).execute()
    data = getattr(res, "data", None) or []
    return data[0].get("id") if data else None


def insert_machine_supplier(
    client,
    machine_id: str,
    supplier_id: str,
    supplier_payload: dict,
    metadata: Optional[dict] = None,
) -> None:
    if not client or not machine_id or not supplier_id:
        return
    payload = {
        "machine_id": machine_id,
        "supplier_id": supplier_id,
        "price_estimate": supplier_payload.get("price_estimate"),
        "price_type": supplier_payload.get("price_type"),
        "price_currency": supplier_payload.get("price_currency"),
        "lead_time_days": supplier_payload.get("lead_time_days"),
        "relevance_score": supplier_payload.get("relevance_score"),
        "notes": supplier_payload.get("notes"),
        "metadata": metadata or {},
    }
    client.table("machine_suppliers").upsert(payload, on_conflict="machine_id,supplier_id").execute()
