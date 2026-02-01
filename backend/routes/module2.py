import json
import os
import re
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from config import BASE_URL, OUTPUT_DIRS, SKIP_MODULE_2, PIPLEINE_3D_CAP, CREATE_REALISTIC_RENDER, CREATE_3D_MODEL, TEMPLATE_DIR
from supabase_utils import get_supabase, insert_layout, insert_pipeline, update_project_current_pipeline, upload_file, insert_project_file, build_object_path, get_public_url
from utils.app_helpers import (
    get_pipeline_settings,
    get_request_project_id,
    get_request_user_id,
    load_template_payload,
    store_project_settings,
    upload_and_register_file,
)
from utils.module_2.main import run_pipeline
from utils.logger import log_skip, get_logger
from utils.module_2 import config as module2_config

logger = get_logger("module2")

def convert_dxf_to_png(dxf_path: str, png_path: str) -> bool:
    """Convert DXF file to PNG using ezdxf and matplotlib."""
    try:
        import ezdxf
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib.pyplot as plt

        doc = ezdxf.readfile(dxf_path)
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace())
        plt.savefig(png_path, dpi=300)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error converting DXF to PNG: {e}")
        return False

bp_module2 = Blueprint("module2", __name__)
PROJECT_LOCKS = {}
PROJECT_LOCKS_LOCK = threading.Lock()

def get_project_lock(project_id: str):
    with PROJECT_LOCKS_LOCK:
        if project_id not in PROJECT_LOCKS:
            PROJECT_LOCKS[project_id] = threading.Lock()
        return PROJECT_LOCKS[project_id]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        num = float(value)
    else:
        nums = re.findall(r"\d+\.?\d*", str(value))
        if not nums:
            return None
        num = float(nums[0])
    if num <= 0:
        return None
    if num > 30:
        num = num / 1000.0
    return num


def _parse_dimensions(value: Any) -> tuple[Optional[float], Optional[float]]:
    if isinstance(value, dict):
        length = value.get("longueur") or value.get("length")
        width = value.get("largeur") or value.get("width")
        height = value.get("hauteur") or value.get("height")
        return _to_number(length), _to_number(width or height)
    if isinstance(value, str):
        nums = re.findall(r"\d+\.?\d*", value)
        if len(nums) >= 2:
            return _to_number(nums[0]), _to_number(nums[1])
    return None, None


def _extract_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    product = payload.get("product")
    if isinstance(product, dict):
        return product
    product_src = payload.get("stage_3_produits_fabriques", {}).get("produits_fabriques", [])
    product_src = product_src[0] if product_src else {}
    volume = product_src.get("volume_production", {}) if isinstance(product_src, dict) else {}
    if product_src:
        return {
            "name": str(product_src.get("nom_produit", "Industrial Product")),
            "output_unit": str(volume.get("unite", "units")),
            "target_output_per_hour": volume.get("capacite", "N/A"),
        }
    return {}


def _pick_image(machine: Dict[str, Any]) -> str:
    for key in (
        "image_local_path",
        "image_download_url",
        "image_url",
        "image",
        "best_image_url",
    ):
        value = machine.get(key)
        if isinstance(value, str) and value.strip():
            return value
    assets = machine.get("assets", {}) if isinstance(machine.get("assets"), dict) else {}
    urls = assets.get("image_urls", []) if isinstance(assets.get("image_urls"), list) else []
    return urls[0] if urls else ""


def _normalize_machines(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for m in items:
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or m.get("nom_machine") or m.get("model") or "Machine")
        model = str(m.get("model") or m.get("type") or m.get("fabricant_recommande") or name)
        try:
            count = int(m.get("count") or m.get("quantite_necessaire") or m.get("quantity") or 1)
        except Exception:
            count = 1
        count = max(1, count)
        use = str(m.get("use") or m.get("usage") or m.get("type") or "")

        width = _to_number(m.get("width"))
        height = _to_number(m.get("height"))

        specs = m.get("specifications") if isinstance(m.get("specifications"), dict) else {}
        if width is None:
            width = _to_number(specs.get("width") or specs.get("largeur") or specs.get("longueur") or specs.get("length"))
        if height is None:
            height = _to_number(specs.get("height") or specs.get("hauteur") or specs.get("largeur"))
        if width is None or height is None:
            dims = specs.get("dimensions") or m.get("dimensions")
            parsed_w, parsed_h = _parse_dimensions(dims)
            width = width or parsed_w
            height = height or parsed_h

        entry = {
            "name": name,
            "model": model,
            "count": count,
            "use": use,
        }
        image = _pick_image(m)
        if image:
            entry["image"] = image
        if width is not None:
            entry["width"] = width
        if height is not None:
            entry["height"] = height
        normalized.append(entry)
    return normalized


def _unwrap_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    inner = payload.get("data")
    if isinstance(inner, dict):
        if inner.get("machines") or inner.get("enriched_machines") or inner.get("stage_4_machines_equipements"):
            return inner
    return payload


def _resolve_stop_at(settings: Dict[str, Any]) -> Optional[int]:
    raw = settings.get("stop_at") or settings.get("pipeline_stop_at") or settings.get("pipeline_3d_cap")
    if raw is None:
        raw = PIPLEINE_3D_CAP
    try:
        val = int(raw)
    except Exception:
        return None
    if val <= 0:
        return None
    return max(1, min(6, val))


def _clear_paths(paths: List[Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except Exception:
            continue


def _copy_output(src: str, dst: Path) -> Optional[str]:
    if not src:
        return None
    if not os.path.exists(src):
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if os.path.abspath(src) != os.path.abspath(str(dst)):
            shutil.copy2(src, dst)
    except Exception:
        return None
    return str(dst)


def _download_url_for(path_str: Optional[str]) -> Optional[str]:
    if not path_str:
        return None
    return f"{BASE_URL}/download/{Path(path_str).name}"


@bp_module2.route("/api/module2/layout", methods=["POST"])
def generate_layout():
    try:
        if SKIP_MODULE_2:
            log_skip("module2.generate_layout", reason="SKIP_MODULE_2")
            payload = load_template_payload("module2") or {}
            
            output_dir = OUTPUT_DIRS["module2"]
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy template PNG
            template_img = TEMPLATE_DIR / "layout_square.png"
            if template_img.exists():
                target_img = output_dir / "layout_square.png"
                shutil.copy2(template_img, target_img)
                payload["layout_2d"] = str(target_img)
                payload["layout_2d_url"] = _download_url_for(str(target_img))
            
            # Copy template GLB
            template_glb = TEMPLATE_DIR / "pipeline.glb"
            if template_glb.exists():
                target_glb = output_dir / "factory_model.glb"
                shutil.copy2(template_glb, target_glb)
                payload["layout_3d"] = str(target_glb)
                payload["layout_3d_url"] = _download_url_for(str(target_glb))

            project_id = get_request_project_id(include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
            return jsonify(payload)

        if not request.is_json:
            return jsonify({"error": "Expected JSON payload"}), 400

        payload = request.get_json() or {}
        if isinstance(payload, list):
            payload = {"machines": payload}
        else:
            payload = _unwrap_payload(payload)
        project_id = get_request_project_id(include_json=True)
        module1_id = payload.get("module1_id") or payload.get("ribif_metadata", {}).get("module1_id")

        machines_raw = (
            payload.get("machines")
            or payload.get("enriched_machines")
            or payload.get("stage_4_machines_equipements", {}).get("machines_production", [])
        )
        if not machines_raw and "data" in payload:
            machines_raw = payload["data"].get("machines") or payload["data"].get("enriched_machines") or []

        machines = _normalize_machines(machines_raw or [])
        if not machines:
            return jsonify({"error": "Missing required field: machines"}), 400

        product = _extract_product(payload)

        output_dir = OUTPUT_DIRS["module2"]
        output_dir.mkdir(parents=True, exist_ok=True)

        input_data = {"product": product, "machines": machines}
        input_path = output_dir / "module_2_input.json"
        input_path.write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")

        links_path = output_dir / "links.json"

        # Clear previous outputs to avoid stale responses.
        _clear_paths([
            Path(module2_config.OUTPUT_DXF),
            Path(module2_config.OUTPUT_PNG),
            Path(module2_config.REALISTIC_PNG),
            Path(module2_config.REALISTIC_CLEAN_PNG),
            Path(module2_config.FINAL_GLB_PATH),
            output_dir / "layout_square.dxf",
            output_dir / "layout_square.png",
            output_dir / "realistic_layout.png",
            output_dir / "realistic_clean.png",
            output_dir / "factory_model.glb",
            links_path,
        ])

        settings = get_pipeline_settings()
        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id and settings:
            try:
                store_project_settings(client, project_id, settings, owner_id)
            except Exception as e:
                logger.warning(f"Failed to store project settings: {e}")
        seed_raw = settings.get("seed") or settings.get("layout_seed") or 7
        try:
            seed = int(seed_raw)
        except Exception:
            seed = 7
        force_links = _as_bool(settings.get("force_links") or settings.get("force-links"))
        skip_images = _as_bool(settings.get("skip_images") or settings.get("skip-images"))
        stop_at = _resolve_stop_at(settings)
        create_realistic_render = _as_bool(
            settings.get("create_realistic_render")
            or settings.get("create-realistic-render")
            or CREATE_REALISTIC_RENDER
        )
        create_3d_model = _as_bool(
            settings.get("create_3d_model")
            or settings.get("create-3d-model")
            or CREATE_3D_MODEL
        )

        lock = get_project_lock(project_id or "default")
        if not lock.acquire(blocking=False):
            return jsonify({"error": "Module 2 pipeline is busy for this project. Try again shortly."}), 429
        try:
            run_pipeline(
                data_path=str(input_path),
                links_path=str(links_path),
                seed=seed,
                force_links=force_links,
                skip_images=skip_images,
                stop_at=stop_at,
                create_realistic_render=create_realistic_render,
                create_3d_model=create_3d_model,
            )
        finally:
            lock.release()

        # Convert DXF to PNG using ezdxf
        converted_png = output_dir / "layout_square.png"
        dxf_path = module2_config.OUTPUT_DXF
        if Path(dxf_path).exists():
            success = convert_dxf_to_png(dxf_path, str(converted_png))
            if success:
                layout_2d = str(converted_png)
            else:
                # Fallback removed as per user request to avoid returning "realistic/green-screen" png
                layout_2d = None 
        else:
            layout_2d = None

        layout_dxf = _copy_output(module2_config.OUTPUT_DXF, output_dir / "layout_square.dxf")
        # layout_realistic = _copy_output(module2_config.REALISTIC_PNG, output_dir / "realistic_layout.png")
        # layout_realistic_clean = _copy_output(module2_config.REALISTIC_CLEAN_PNG, output_dir / "realistic_clean.png")
        layout_3d = _copy_output(module2_config.FINAL_GLB_PATH, output_dir / "factory_model.glb")
        pipeline_links = str(links_path) if links_path.exists() else None

        if not any([layout_2d, layout_3d, layout_dxf, pipeline_links]):
            return jsonify({"error": "Pipeline completed but no outputs were generated."}), 500

        result = {
            "layout_2d": layout_2d,
            "layout_3d": layout_3d,
            "layout_dxf": layout_dxf,
            # "layout_realistic": layout_realistic,
            # "layout_realistic_clean": layout_realistic_clean,
            "product": product,
            "pipeline_stop_at": stop_at,
            "pipeline_links": pipeline_links,
        }
        if project_id:
            result["project_id"] = project_id
        if module1_id:
            result.setdefault("ribif_metadata", {})
            result["ribif_metadata"]["module1_id"] = module1_id

        for key in (
            "layout_2d",
            "layout_3d",
            "layout_dxf",
            # "layout_realistic",
            # "layout_realistic_clean",
            "pipeline_links",
        ):
            url = _download_url_for(result.get(key))
            if url:
                result[f"{key}_url"] = url

        client = client or get_supabase()
        owner_id = owner_id or get_request_user_id()
        if client and project_id:
            try:
                # Upload files to Supabase and get IDs and URLs
                layout_files_to_upload = [
                    ("layout_2d", layout_2d, "layout-2d", "image/png"),
                    ("layout_3d", layout_3d, "layout-3d", "model/gltf-binary"),
                    ("layout_dxf", layout_dxf, "layout-dxf", "application/dxf"),
                    # ("layout_realistic", layout_realistic, "layout-realistic", "image/png"),
                    # ("layout_realistic_clean", layout_realistic_clean, "layout-realistic-clean", "image/png"),
                ]

                file_ids = {}
                for key, file_path, category, mime in layout_files_to_upload:
                    if file_path and os.path.exists(file_path):
                        try:
                            object_path = build_object_path(project_id, category, Path(file_path).name)
                            upload_file(client, "project-files", object_path, file_path, content_type=mime)
                            file_id = insert_project_file(
                                client,
                                project_id,
                                owner_id,
                                "project-files",
                                object_path,
                                mime,
                                os.path.getsize(file_path),
                                category,
                                label=key,
                            )
                            file_ids[f"{key}_file_id"] = file_id
                            
                            # Get public URL and add to result
                            public_url = get_public_url(client, "project-files", object_path)
                            result[f"{key}_supabase_url"] = public_url

                            logger.info("Uploaded %s to Supabase: %s", key, public_url)
                        except Exception as e:
                            logger.error("Failed to upload %s to Supabase: %s", key, e)
                            file_ids[f"{key}_file_id"] = None
                    else:
                        file_ids[f"{key}_file_id"] = None

                layout_2d_file_id = file_ids.get("layout_2d_file_id")
                layout_3d_file_id = file_ids.get("layout_3d_file_id")
                layout_dxf_file_id = file_ids.get("layout_dxf_file_id")
                layout_realistic_file_id = file_ids.get("layout_realistic_file_id")
                layout_realistic_clean_file_id = file_ids.get("layout_realistic_clean_file_id")
                
                pipeline_links_file_id = None
                pipeline_id = None
                pipeline_payload = None
                if pipeline_links and Path(pipeline_links).exists():
                    try:
                        pipeline_payload = json.loads(Path(pipeline_links).read_text(encoding="utf-8"))
                        # Also upload links file
                        try:
                            object_path = build_object_path(project_id, "pipeline-links", Path(pipeline_links).name)
                            upload_file(client, "project-files", object_path, pipeline_links, content_type="application/json")
                            pipeline_links_file_id = insert_project_file(
                                client,
                                project_id,
                                owner_id,
                                "project-files",
                                object_path,
                                "application/json",
                                os.path.getsize(pipeline_links),
                                "pipeline-links",
                                label="pipeline_links"
                            )
                        except Exception as e:
                             logger.error("Failed to upload pipeline_links to Supabase: %s", e)

                    except Exception:
                        pipeline_payload = None
                if pipeline_payload is not None:
                    pipeline_id = insert_pipeline(
                        client=client,
                        project_id=project_id,
                        generated_by=owner_id,
                        groups=pipeline_payload.get("groups"),
                        flows=pipeline_payload.get("flows") or pipeline_payload,
                        layout_suggestion=pipeline_payload.get("layout_suggestion"),
                        metadata={"source": "module2"},
                    )
                    if pipeline_id:
                        update_project_current_pipeline(client, project_id, pipeline_id)

                insert_layout(
                    client=client,
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    layout_2d_file_id=layout_2d_file_id,
                    layout_3d_file_id=layout_3d_file_id,
                    data=result,
                )
                result["layout_dxf_file_id"] = layout_dxf_file_id
                result["layout_realistic_file_id"] = layout_realistic_file_id
                result["layout_realistic_clean_file_id"] = layout_realistic_clean_file_id
                result["pipeline_links_file_id"] = pipeline_links_file_id
            except Exception as e:
                logger.error("Supabase integration error: %s", e)
                pass

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
