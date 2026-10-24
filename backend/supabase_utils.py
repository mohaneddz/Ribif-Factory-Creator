import os
import re
import mimetypes
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from supabase import create_client, Client


# Ensure trailing slash for storage endpoint
raw_url = os.getenv("SUPABASE_URL", "")
SUPABASE_URL = (raw_url.rstrip("/") + "/") if raw_url else ""
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Log normalized storage/API endpoint at startup (safe extraction of domain)
if SUPABASE_URL and SUPABASE_URL != "/":
    from utils.logger import get_logger
    _logger = get_logger("supabase_utils")
    _logger.info(f"Supabase endpoint normalized: {SUPABASE_URL}")

SUPABASE_BUCKET_FILES = os.getenv("SUPABASE_BUCKET_FILES", "project-files")
SUPABASE_BUCKET_PUBLIC = os.getenv("SUPABASE_BUCKET_PUBLIC", "public-assets")
SUPABASE_SIGNED_URL_EXPIRES = int(os.getenv("SUPABASE_SIGNED_URL_EXPIRES", "3600"))




def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_name(name: str) -> str:
    name = name or "file"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return name or "file"


def get_supabase() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or SUPABASE_URL == "/":
        return None
    
    # Suppress noisy logs from supabase dependencies
    import logging
    import warnings
    logging.getLogger("supabase").setLevel(logging.ERROR)
    logging.getLogger("storage3").setLevel(logging.ERROR)
    logging.getLogger("gotrue").setLevel(logging.ERROR)
    logging.getLogger("postgrest").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    
    # Suppress storage endpoint warning
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Storage endpoint URL should have a trailing slash")
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def is_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def guess_mime(path: str, fallback: str = "application/octet-stream") -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or fallback


def build_object_path(project_id: Optional[str], category: str, filename: str) -> str:
    safe_filename = _safe_name(filename)
    pid = project_id or "unassigned"
    cat = _safe_name(category or "misc")
    return f"{pid}/{cat}/{_now_stamp()}_{safe_filename}"


def build_name_timestamp_object_path(project_id: Optional[str], category: str, filename: str) -> str:
    safe_filename = _safe_name(filename)
    stem, ext = os.path.splitext(safe_filename)
    pid = project_id or "unassigned"
    cat = _safe_name(category or "misc")
    return f"{pid}/{cat}/{stem}_{_now_stamp()}{ext}"


def upload_bytes(
    client: Client,
    bucket: str,
    object_path: str,
    data: bytes,
    content_type: str,
    upsert: bool = True,
) -> None:
    client.storage.from_(bucket).upload(
        object_path,
        data,
        file_options={"content-type": content_type, "upsert": "true" if upsert else "false"},
    )


def upload_file(
    client: Client,
    bucket: str,
    object_path: str,
    file_path: str,
    content_type: Optional[str] = None,
    upsert: bool = True,
) -> None:
    with open(file_path, "rb") as f:
        data = f.read()
    upload_bytes(
        client=client,
        bucket=bucket,
        object_path=object_path,
        data=data,
        content_type=content_type or guess_mime(file_path),
        upsert=upsert,
    )


def get_public_url(client: Client, bucket: str, object_path: str) -> str:
    return client.storage.from_(bucket).get_public_url(object_path)


def create_signed_url(client: Client, bucket: str, object_path: str, expires_in: Optional[int] = None) -> str:
    exp = expires_in or SUPABASE_SIGNED_URL_EXPIRES
    res = client.storage.from_(bucket).create_signed_url(object_path, exp)
    return res.get("signedURL") or res.get("signed_url") or ""


def insert_project(
    client: Client,
    owner_id: Optional[str],
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    payload = {
        "owner_id": owner_id,
        "name": name,
        "metadata": metadata or {},
    }
    res = client.table("projects").insert(payload).execute()
    data = getattr(res, "data", None) or []
    return data[0]["id"] if data else None


def upsert_project_settings(
    client: Client,
    project_id: str,
    settings: Dict[str, Any],
    updated_by: Optional[str] = None,
) -> None:
    if not project_id:
        return
    
    # Merge existing settings if needed, or just overwrite. 
    # Usually settings are partial updates, but here we replace the dict or merge? 
    # The requirement says "must write to projects.settings".
    # We'll do a direct update.
    
    # Also update metadata if needed? No, just settings.
    # We should probably fetch existing to merge if we want to be safe, but 
    # typically "upsert settings" implies writing the state.
    # Let's just update the column.
    
    client.table("projects").update({
        "settings": settings or {},
        # "updated_by": updated_by # No column for this in schema provided, maybe metadata?
        # Schema has `updated_at` trigger.
    }).eq("id", project_id).execute()


def insert_project_file(
    client: Client,
    project_id: str,
    owner_id: Optional[str],
    bucket: str,
    object_path: str,
    mime_type: Optional[str],
    size_bytes: Optional[int],
    category: str,
    label: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Register a file upload. Returns None since project_files table was removed in simplified schema.
    The file is still uploaded to storage, this just skips the DB record."""
    # Note: project_files table was removed in the simplified schema.
    # Files are still uploaded to storage bucket, but we don't track them in a separate table.
    # The file references are stored directly in the module data columns (module7_business, etc.)
    return None


def insert_module1_extraction(
    client: Client,
    project_id: str,
    source_file_id: Optional[str],
    data: Dict[str, Any],
    project_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not project_id:
        return None
        
    # 1. Fetch current project to get completed_modules and metadata
    res = client.table("projects").select("completed_modules, metadata, current_module").eq("id", project_id).single().execute()
    current_data = res.data or {}
    
    completed = current_data.get("completed_modules") or []
    if "module1" not in completed:
        completed.append("module1")
        
    meta = current_data.get("metadata") or {}
    if project_metadata:
        meta.update(project_metadata)
    
    payload = {
        "module1_data": data,
        "completed_modules": completed,
        "current_module": "module1",
        "metadata": meta,
        "updated_at": _now_stamp(), # Optional but good practice
    }
    
    client.table("projects").update(payload).eq("id", project_id).execute()
    return project_id


def validate_module4_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize Module 4 output before saving to Supabase.
    
    Ensures:
    - Arrays (emails, phones, contact_pages, evidence) are proper arrays
    - Strings are strings
    - No null values inside arrays
    - Deduplication performed
    - All required fields present with defaults
    
    Args:
        data: Module 4 output dictionary
        
    Returns:
        Validated and sanitized data
    """
    from utils.logger import get_logger
    logger = get_logger("supabase_utils")
    
    def sanitize_array(value, field_name="array"):
        """Ensure value is a proper array with no nulls."""
        if value is None:
            return []
        if isinstance(value, str):
            # Shouldn't happen, but handle gracefully
            logger.warning(f"Converting string to array for {field_name}: {value}")
            return [value] if value else []
        if not isinstance(value, list):
            logger.warning(f"Converting non-list to array for {field_name}: {type(value)}")
            return [value] if value else []
        
        # Remove nulls and deduplicate
        cleaned = []
        seen = set()
        for item in value:
            if item is not None and item not in seen:
                cleaned.append(item)
                seen.add(item)
        
        return cleaned
    
    def sanitize_string(value, default=""):
        """Ensure value is a string."""
        if value is None:
            return default
        if isinstance(value, str):
            return value if value.strip() else default
        return str(value)
    
    # Validate top-level structure
    if not isinstance(data, dict):
        logger.error("Module 4 output is not a dictionary")
        return data
    
    machines_enriched = data.get("machines_enriched", [])
    if not isinstance(machines_enriched, list):
        logger.error("machines_enriched is not a list")
        return data
    
    # Validate each machine
    for i, machine in enumerate(machines_enriched):
        if not isinstance(machine, dict):
            logger.warning(f"Machine {i} is not a dictionary")
            continue
        
        # Validate suppliers array
        suppliers = machine.get("suppliers", [])
        if not isinstance(suppliers, list):
            logger.warning(f"Machine {i} suppliers is not a list")
            machine["suppliers"] = []
            suppliers = []
        
        # Validate each supplier
        for j, supplier in enumerate(suppliers):
            if not isinstance(supplier, dict):
                logger.warning(f"Machine {i} supplier {j} is not a dictionary")
                continue
            
            # Sanitize array fields
            supplier["emails"] = sanitize_array(supplier.get("emails"), f"emails[{i}][{j}]")
            supplier["phones"] = sanitize_array(supplier.get("phones"), f"phones[{i}][{j}]")
            supplier["contact_pages"] = sanitize_array(supplier.get("contact_pages"), f"contact_pages[{i}][{j}]")
            supplier["evidence"] = sanitize_array(supplier.get("evidence"), f"evidence[{i}][{j}]")
            
            # Sanitize string fields
            supplier["supplier_name"] = sanitize_string(supplier.get("supplier_name"), "Unknown")
            supplier["region"] = sanitize_string(supplier.get("region"), "Unknown")
            supplier["website"] = sanitize_string(supplier.get("website", ""))
            supplier["price_estimate"] = sanitize_string(supplier.get("price_estimate"), "Contact for quote")
            supplier["price_type"] = sanitize_string(supplier.get("price_type"), "Indicative")
            supplier["notes"] = sanitize_string(supplier.get("notes"), "")
            supplier["availability_note"] = sanitize_string(supplier.get("availability_note", ""))
            
            # Sanitize boolean
            supplier["ai_star"] = bool(supplier.get("ai_star") or supplier.get("is_ai_fallback"))
            
            # Sanitize numeric fields
            try:
                supplier["relevance_score"] = float(supplier.get("relevance_score", 0.5))
            except (TypeError, ValueError):
                supplier["relevance_score"] = 0.5
            
            try:
                supplier["quality_score"] = float(supplier.get("quality_score", 0.5))
            except (TypeError, ValueError):
                supplier["quality_score"] = 0.5
        
        # Sanitize machine-level fields
        if "no_public_suppliers_subtext" in machine:
            machine["no_public_suppliers_subtext"] = sanitize_string(
                machine.get("no_public_suppliers_subtext", "")
            )
    
    logger.info(f"Validated Module 4 output: {len(machines_enriched)} machines")
    return data


def insert_module4_sourcing(
    client: Client,
    project_id: str,
    module1_id: Optional[str],
    data: Dict[str, Any],
    project_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not project_id:
        return None

    # NEW: Validate and sanitize Module 4 output
    data = validate_module4_output(data)

    # 1. Fetch current project
    res = client.table("projects").select("completed_modules, metadata").eq("id", project_id).single().execute()
    current_data = res.data or {}
    
    completed = current_data.get("completed_modules") or []
    if "module4" not in completed:
        completed.append("module4")
        
    meta = current_data.get("metadata") or {}
    if project_metadata:
        meta.update(project_metadata)

    payload = {
        "module4_data": data,
        "completed_modules": completed,
        "current_module": "module4", 
        "metadata": meta,
        "updated_at": _now_stamp(),
    }
    
    client.table("projects").update(payload).eq("id", project_id).execute()
    return project_id



def insert_tco_run(
    client: Client,
    project_id: str,
    module4_id: Optional[str],
    data: Dict[str, Any],
) -> Optional[str]:
    if not project_id:
        return None

    import uuid
    new_run_id = str(uuid.uuid4())
    
    res = client.table("projects").select("completed_modules, module6_data").eq("id", project_id).single().execute()
    current_data = res.data or {}
    
    completed = current_data.get("completed_modules") or []
    if "module6" not in completed:
        completed.append("module6")
    
    # We can store TCO runs as a list or just the latest. 
    # Current requirement says "module6_data". 
    # Usually TCO is iterative. Let's store the latest in module6_data directly, 
    # maybe keeping history if "runs" key exists.
    # For simplicity and schema compliance: module6_data will hold the RUN DATA.
    
    payload_data = {
        "id": new_run_id,
        "project_id": project_id,
        "module4_id": module4_id,
        "currency": data.get("currency") or "DZD",
        "total_tco": data.get("total_tco"),
        "average_annual_tco": data.get("average_annual_tco"),
        "tco_per_unit_revenue": data.get("tco_per_unit_revenue"),
        "data": data, # The detailed breakdown
        "created_at": _now_stamp(),
    }
    
    client.table("projects").update({
        "module6_data": payload_data,
        "completed_modules": completed,
        "current_module": "module6",
        "updated_at": _now_stamp(),
    }).eq("id", project_id).execute()
    
    return new_run_id


def insert_business_plan(
    client: Client,
    project_id: str,
    tco_run_id: Optional[str],
    file_id: Optional[str],
    filename: Optional[str],
    data: Dict[str, Any],
) -> None:
    """Update projects table with business plan data."""
    if not project_id:
        return
    
    # Add file info to data for frontend access
    enriched_data = {
        **data,
        "file_id": file_id,
        "filename": filename,
        "tco_run_id": tco_run_id,
    }
    
    client.table("projects").update({"module7_business": enriched_data}).eq("id", project_id).execute()


def insert_pitch_deck(
    client: Client,
    project_id: str,
    tco_run_id: Optional[str],
    file_id: Optional[str],
    presentation_id: Optional[str],
    edit_url: Optional[str],
    data: Dict[str, Any],
) -> None:
    """Update projects table with pitch deck data."""
    if not project_id:
        return
    
    # Add file info to data for frontend access
    enriched_data = {
        **data,
        "file_id": file_id,
        "presentation_id": presentation_id,
        "edit_url": edit_url,
        "tco_run_id": tco_run_id,
    }
    
    client.table("projects").update({"module7_pitch": enriched_data}).eq("id", project_id).execute()


def insert_catalog(
    client: Client,
    project_id: str,
    module1_id: Optional[str],
    pdf_file_id: Optional[str],
    html_file_id: Optional[str],
    data: Dict[str, Any],
) -> None:
    """Update projects table with catalog data."""
    if not project_id:
        return
    
    # Add file info to data for frontend access
    enriched_data = {
        **data,
        "module1_id": module1_id,
        "pdf_file_id": pdf_file_id,
        "html_file_id": html_file_id,
    }
    
    client.table("projects").update({"module9_data": enriched_data}).eq("id", project_id).execute()



def insert_layout(
    client: Client,
    project_id: str,
    pipeline_id: Optional[str],
    layout_2d_file_id: Optional[str],
    layout_3d_file_id: Optional[str],
    data: Dict[str, Any],
) -> None:
    if not project_id:
        return
        
    res = client.table("projects").select("completed_modules, metadata, module2_data").eq("id", project_id).single().execute()
    current_data = res.data or {}
    
    completed = current_data.get("completed_modules") or []
    if "module2" not in completed:
        completed.append("module2")
        
    payload = {
        "module2_data": {
            **(current_data.get("module2_data") or {}),
            **data,
            "pipeline_id": pipeline_id,
            "layout_2d_file_id": layout_2d_file_id,
            "layout_3d_file_id": layout_3d_file_id,
        },
        "completed_modules": completed,
        "current_module": "module2",
        "updated_at": _now_stamp(),
    }
    client.table("projects").update(payload).eq("id", project_id).execute()


def insert_pipeline(
    client: Client,
    project_id: str,
    generated_by: Optional[str],
    groups: Optional[Dict[str, Any]],
    flows: Optional[Dict[str, Any]],
    layout_suggestion: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not project_id:
        return None

    import uuid
    new_pipeline_id = str(uuid.uuid4())
    
    res = client.table("projects").select("pipelines").eq("id", project_id).single().execute()
    current_pipelines = (res.data or {}).get("pipelines") or []
    if not isinstance(current_pipelines, list):
        current_pipelines = []

    new_pipeline = {
        "id": new_pipeline_id,
        "project_id": project_id,
        "generated_by": generated_by,
        "groups": groups,
        "flows": flows,
        "layout_suggestion": layout_suggestion,
        "metadata": metadata or {},
        "created_at": _now_stamp(),
    }
    
    current_pipelines.append(new_pipeline)
    
    client.table("projects").update({
        "pipelines": current_pipelines,
        # "current_pipeline_id": new_pipeline_id # We can store this in metadata or implicit last
    }).eq("id", project_id).execute()
    
    return new_pipeline_id


def update_project_current_pipeline(client: Client, project_id: str, pipeline_id: str) -> None:
    pass # No-op, pipeline ID is returned by insert_pipeline and stored in module2_data if needed


def insert_video(
    client: Client,
    project_id: str,
    file_id: Optional[str],
    data: Dict[str, Any],
) -> None:
    if not project_id:
        return
        
    res = client.table("projects").select("completed_modules, module3_data").eq("id", project_id).single().execute()
    current_data = res.data or {}
    
    completed = current_data.get("completed_modules") or []
    if "module3" not in completed:
        completed.append("module3")
        
    payload = {
        "module3_data": {
            **(current_data.get("module3_data") or {}),
            **data,
            "file_id": file_id,
        },
        "completed_modules": completed,
        "current_module": "module3",
        "updated_at": _now_stamp(),
    }
    client.table("projects").update(payload).eq("id", project_id).execute()


def delete_project_files(client: Client, project_id: str, bucket: str = SUPABASE_BUCKET_FILES) -> Tuple[int, Optional[str]]:
    """
    Recursively delete all files in the storage bucket for a given project.
    Returns (count_deleted, error_message).
    """
    try:
        all_file_paths = []
        
        def collect_files(path: str):
            res = client.storage.from_(bucket).list(path)
            if not res:
                return
            
            for item in res:
                item_name = item.get('name')
                if not item_name:
                    continue
                    
                full_path = f"{path}/{item_name}"
                # In Supabase storage list, items without an ID are typically folders
                # or you can check if it's a file by trying to list it or checking metadata
                # A common pattern is that files have 'metadata' or 'id'
                if item.get('id') is None:
                    # It's a folder, recurse
                    collect_files(full_path)
                else:
                    # It's a file
                    all_file_paths.append(full_path)

        # Start collection from project root
        collect_files(project_id)
        
        if not all_file_paths:
            return (0, None)
        
        # Supabase remove takes chunks of paths
        # Delete in batches of 100 to avoid request size limits if many files
        batch_size = 100
        for i in range(0, len(all_file_paths), batch_size):
            batch = all_file_paths[i:i + batch_size]
            client.storage.from_(bucket).remove(batch)
        
        return (len(all_file_paths), None)
    except Exception as e:
        return (0, str(e))


def delete_project(client: Client, project_id: str) -> Optional[str]:
    """
    Delete a project from the database.
    Returns error message if any, None on success.
    Note: This assumes CASCADE delete is configured in the database for related tables.
    """
    try:
        client.table("projects").delete().eq("id", project_id).execute()
        return None
    except Exception as e:
        return str(e)


def reset_project_data(client: Client, project_id: str) -> Optional[str]:
    """
    Reset a project's data columns to NULL, effectively restarting the process.
    Preserves the source file and project ID.
    Returns error message if any, None on success.
    """
    try:
        # Update projects table to clear module data
        payload = {
            "status": "uploaded",  # Reset status to uploaded so it picks up the file again
            "module1_data": None,
            "module2_data": None,
            "module3_data": None,
            "module4_data": None,
            "module5_data": None,
            "module6_data": None,
            "module7_business": None,
            "module7_pitch": None,
            "module9_data": None,
            # We preserve source_file_path and source_filename
        }
        client.table("projects").update(payload).eq("id", project_id).execute()
        
        # Determine files to keep (the source file)
        # We need to list files and delete everything EXCEPT the source file if possible.
        # However, finding the source file path in the bucket might be tricky if we don't know the exact path here.
        # But usually source_file_path in DB is the path.
        
        # For now, let's just clear the DB data. The files in storage (artifacts) result in "links" which we just broke by clearing the DB.
        # Deleting the actual files from storage is better for hygiene but "deleting the links" (DB columns) is sufficient to "restart" the user flow.
        # If we delete everything in the bucket, we might delete the source file if it's in the same bucket/folder which the user considers "upload".
        
        return None
    except Exception as e:
        return str(e)


# ============================================================
# NEGOTIATIONS (Module 5) - Voice-first negotiation tracking
# ============================================================

import secrets


def generate_negotiation_token() -> str:
    """Generate a secure random token for negotiation links."""
    return secrets.token_hex(32)


def create_negotiation(
    client: Client,
    project_id: str,
    supplier_name: str,
    machine_name: str,
    quantity: int = 1,
    supplier_email: Optional[str] = None,
    supplier_phone: Optional[str] = None,
    supplier_website: Optional[str] = None,
    supplier_region: Optional[str] = None,
    machine_type: Optional[str] = None,
    initial_price_estimate: Optional[float] = None,
    currency: str = "DZD",
    buyer_company: str = "RIBIF Algeria",
    buyer_email: Optional[str] = None,
    buyer_contact_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a new negotiation record in the database.
    Returns the created negotiation record or None on failure.
    """
    try:
        # Generate unique link token
        link_token = generate_negotiation_token()
        
        payload = {
            "project_id": project_id,
            "supplier_name": supplier_name,
            "supplier_email": supplier_email,
            "supplier_phone": supplier_phone,
            "supplier_website": supplier_website,
            "supplier_region": supplier_region,
            "machine_name": machine_name,
            "machine_type": machine_type,
            "quantity": quantity,
            "initial_price_estimate": initial_price_estimate,
            "currency": currency,
            "status": "pending",
            "link_token": link_token,
            "buyer_company": buyer_company,
            "buyer_email": buyer_email,
            "buyer_contact_name": buyer_contact_name,
        }
        
        res = client.table("negotiations").insert(payload).execute()
        data = getattr(res, "data", None) or []
        return data[0] if data else None
    except Exception as e:
        from utils.logger import get_logger
        get_logger("supabase_utils").error(f"Failed to create negotiation: {e}")
        return None


def get_negotiation_by_id(client: Client, negotiation_id: str) -> Optional[Dict[str, Any]]:
    """Get a negotiation by its ID."""
    try:
        res = client.table("negotiations").select("*").eq("id", negotiation_id).single().execute()
        return res.data
    except Exception:
        return None


def get_negotiation_by_token(client: Client, link_token: str) -> Optional[Dict[str, Any]]:
    """Get a negotiation by its link token (for supplier access)."""
    try:
        res = client.table("negotiations").select("*").eq("link_token", link_token).single().execute()
        return res.data
    except Exception:
        return None


def get_negotiations_by_project(client: Client, project_id: str) -> list:
    """Get all negotiations for a project."""
    try:
        res = client.table("negotiations").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        return getattr(res, "data", None) or []
    except Exception:
        return []


def update_negotiation(client: Client, negotiation_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a negotiation record."""
    try:
        res = client.table("negotiations").update(updates).eq("id", negotiation_id).execute()
        data = getattr(res, "data", None) or []
        return data[0] if data else None
    except Exception as e:
        from utils.logger import get_logger
        get_logger("supabase_utils").error(f"Failed to update negotiation: {e}")
        return None


def update_negotiation_status(client: Client, negotiation_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Update negotiation status."""
    return update_negotiation(client, negotiation_id, {"status": status})


def mark_negotiation_link_sent(client: Client, negotiation_id: str) -> Optional[Dict[str, Any]]:
    """Mark that the negotiation link has been sent to the supplier."""
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=7)  # Link valid for 7 days
    
    return update_negotiation(client, negotiation_id, {
        "status": "link_sent",
        "link_sent_at": now.isoformat(),
        "link_expires_at": expires.isoformat(),
    })


def save_voice_call_result(
    client: Client,
    negotiation_id: str,
    final_price: float,
    discount_achieved: float,
    total_value: float,
    negotiation_rounds: int,
    transcript: list,
    rounds_history: list,
    status: str = "accepted",
) -> Optional[Dict[str, Any]]:
    """Save the results of a completed voice call negotiation."""
    from datetime import datetime, timezone
    
    updates = {
        "status": status,
        "final_price": final_price,
        "discount_achieved": discount_achieved,
        "total_value": total_value,
        "negotiation_rounds": negotiation_rounds,
        "voice_call_transcript": transcript,
        "rounds_history": rounds_history,
        "voice_call_completed_at": datetime.now(timezone.utc).isoformat(),
    }
    
    return update_negotiation(client, negotiation_id, updates)


def add_email_to_negotiation(client: Client, negotiation_id: str, email_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Add an email record to the negotiation's emails_sent array."""
    try:
        # Fetch current emails
        neg = get_negotiation_by_id(client, negotiation_id)
        if not neg:
            return None
        
        emails = neg.get("emails_sent") or []
        emails.append(email_record)
        
        return update_negotiation(client, negotiation_id, {"emails_sent": emails})
    except Exception as e:
        from utils.logger import get_logger
        get_logger("supabase_utils").error(f"Failed to add email to negotiation: {e}")
        return None


def get_negotiations_summary(client: Client, project_id: str) -> Optional[Dict[str, Any]]:
    """Get negotiation summary stats for a project."""
    try:
        res = client.table("negotiations_summary").select("*").eq("project_id", project_id).single().execute()
        return res.data
    except Exception:
        return None


def update_project_module5_data(client: Client, project_id: str, module5_data: Dict[str, Any]) -> Optional[str]:
    """Update project's module5_data column with negotiation summary."""
    try:
        # Fetch current project to merge data
        res = client.table("projects").select("completed_modules, module5_data").eq("id", project_id).single().execute()
        current_data = res.data or {}
        
        # Merge with existing module5_data if present
        existing = current_data.get("module5_data") or {}
        merged = {**existing, **module5_data}
        
        # Update completed_modules
        completed = current_data.get("completed_modules") or []
        if "module5" not in completed:
            completed.append("module5")
        
        client.table("projects").update({
            "module5_data": merged,
            "completed_modules": completed,
        }).eq("id", project_id).execute()
        
        return None
    except Exception as e:
        return str(e)

