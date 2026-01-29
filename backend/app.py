import os
import json
import base64
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from module_1 import RIBIFExtractor

# Import image generation from vertex_utils
from vertex_utils import generate_image
from supabase_utils import (
    SUPABASE_BUCKET_FILES,
    SUPABASE_BUCKET_PUBLIC,
    build_object_path,
    create_signed_url,
    get_public_url,
    get_supabase,
    guess_mime,
    insert_business_plan,
    insert_catalog,
    insert_layout,
    insert_module1_extraction,
    insert_module4_sourcing,
    insert_pitch_deck,
    insert_project,
    insert_project_file,
    insert_tco_run,
    insert_video,
    upload_file,
    upload_bytes,
)

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # Allow Next.js to call this

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'data/extracted_data'
IMAGES_FOLDER = 'data/machine_images'
TEMP_OUTPUT_FOLDER = 'data/temp_outputs'
CATALOG_FOLDER = 'data/catalogs'
DOWNLOAD_FOLDERS = [
    Path('data/7_business_plan'),
    Path('data/7_pitch_deck'),
    Path(CATALOG_FOLDER),
    Path(TEMP_OUTPUT_FOLDER),
    Path(OUTPUT_FOLDER)
]
BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(TEMP_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CATALOG_FOLDER, exist_ok=True)

extractor = RIBIFExtractor()

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


def ensure_project_id(
    client,
    project_id: Optional[str],
    owner_id: Optional[str],
    fallback_name: str,
) -> Optional[str]:
    if project_id:
        return project_id
    if not client:
        return None
    return insert_project(client, owner_id, fallback_name, metadata={"source": "module1_upload"})


def insert_machines_from_stage(client, project_id: str, machines: list, image_meta: dict) -> dict:
    if not client or not machines:
        return {}
    rows = []
    for m in machines:
        name = m.get("nom_machine") or m.get("name") or "Machine"
        meta = {}
        if name in image_meta:
            meta = image_meta[name]
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
    if not rows:
        return {}
    res = client.table("machines").insert(rows).execute()
    data = getattr(res, "data", None) or []
    return {row.get("name"): row.get("id") for row in data if row.get("name")}


def upload_and_register_file(
    client,
    project_id: str,
    owner_id: Optional[str],
    local_path: str,
    category: str,
    label: Optional[str] = None,
    bucket: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if not client:
        return None, None
    bucket_id = bucket or SUPABASE_BUCKET_FILES
    object_path = build_object_path(project_id, category, os.path.basename(local_path))
    upload_file(client, bucket_id, object_path, local_path, content_type=guess_mime(local_path))
    file_id = insert_project_file(
        client=client,
        project_id=project_id,
        owner_id=owner_id,
        bucket=bucket_id,
        object_path=object_path,
        mime_type=guess_mime(local_path),
        size_bytes=os.path.getsize(local_path),
        category=category,
        label=label,
        metadata={},
    )
    signed_url = create_signed_url(client, bucket_id, object_path)
    return file_id, signed_url


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

def reset_temp_outputs() -> None:
    """Clear temp JSON outputs from previous workflow runs."""
    if os.path.exists(TEMP_OUTPUT_FOLDER):
        for filename in os.listdir(TEMP_OUTPUT_FOLDER):
            file_path = os.path.join(TEMP_OUTPUT_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
    else:
        os.makedirs(TEMP_OUTPUT_FOLDER, exist_ok=True)

def write_temp_json(module_name: str, payload: dict) -> dict:
    """Write module output to temp folder and return download metadata."""
    os.makedirs(TEMP_OUTPUT_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{module_name}_{timestamp}.json"
    filepath = os.path.join(TEMP_OUTPUT_FOLDER, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return {
        "filename": filename,
        "filepath": filepath,
        "download_url": f"{BASE_URL}/download/{filename}"
    }

def cleanup_temp_outputs() -> None:
    """Remove temp JSON outputs and any leftover temp files."""
    if os.path.exists(TEMP_OUTPUT_FOLDER):
        for filename in os.listdir(TEMP_OUTPUT_FOLDER):
            file_path = os.path.join(TEMP_OUTPUT_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

def cleanup_temp_images() -> None:
    """Remove generated images from temp folders after workflow completion."""
    # Module 4 generated images
    module4_images_dir = Path(OUTPUT_FOLDER) / "module_4_images"
    if module4_images_dir.exists() and module4_images_dir.is_dir():
        shutil.rmtree(module4_images_dir, ignore_errors=True)

    # Module 1 machine images
    if os.path.exists(IMAGES_FOLDER):
        for filename in os.listdir(IMAGES_FOLDER):
            file_path = os.path.join(IMAGES_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    safe_name = os.path.basename(filename)
    for folder in DOWNLOAD_FOLDERS:
        candidate = folder / safe_name
        if candidate.exists() and candidate.is_file():
            return send_file(candidate, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

def generate_machine_image(machine_name: str, machine_type: str, manufacturer: str = None) -> dict:
    """
    Generate a professional product image for an industrial machine using Gemini.
    
    Returns:
        dict with image_url (base64 data URI) and status
    """
    try:
        # Build a detailed prompt for industrial machine image
        manufacturer_text = f" by {manufacturer}" if manufacturer else ""
        prompt = f"""Professional product photography of an industrial {machine_type} machine called "{machine_name}"{manufacturer_text}.
        
The image should be:
- Clean white/gray studio background
- Professional industrial equipment photography style
- High-quality, sharp details
- Showing the full machine from a 3/4 angle
- Realistic, photographic quality
- No text overlays or labels
- Industrial manufacturing equipment aesthetic"""
        
        print(f"           🎨 Generating image for: {machine_name}")
        
        # Generate image using Gemini
        image_bytes_list = generate_image(prompt, candidate_count=1)
        
        if image_bytes_list and len(image_bytes_list) > 0:
            # Save image to file
            image_filename = f"{machine_name.replace(' ', '_').replace('/', '_')[:50]}.png"
            image_path = os.path.join(IMAGES_FOLDER, image_filename)
            
            with open(image_path, 'wb') as f:
                f.write(image_bytes_list[0])
            
            # Create base64 data URI for frontend
            base64_image = base64.b64encode(image_bytes_list[0]).decode('utf-8')
            data_uri = f"data:image/png;base64,{base64_image}"
            
            print(f"           ✅ Image generated and saved: {image_filename}")
            
            return {
                "image_url": data_uri,
                "image_path": image_path,
                "status": "success"
            }
        else:
            print(f"           ⚠️  No image generated")
            return {
                "image_url": None,
                "status": "no_image"
            }
            
    except Exception as e:
        print(f"           ❌ Image generation error: {str(e)[:80]}")
        return {
            "image_url": None,
            "status": "error",
            "error": str(e)
        }

@app.route('/api/module1/process', methods=['POST'])
def process_module_1():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No filename"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    settings = get_pipeline_settings()
    user_id = get_request_user_id()
    project_id = get_request_project_id(include_form=True)
    supabase_client = get_supabase()
    project_id = ensure_project_id(
        supabase_client,
        project_id,
        user_id,
        Path(filename).stem or "Untitled Project",
    )
    source_file_id = None
    source_file_url = None
    if supabase_client and project_id:
        try:
            source_path = build_object_path(project_id, "uploads", filename)
            upload_file(
                supabase_client,
                SUPABASE_BUCKET_FILES,
                source_path,
                filepath,
                content_type=guess_mime(filepath),
            )
            source_file_id = insert_project_file(
                client=supabase_client,
                project_id=project_id,
                owner_id=user_id,
                bucket=SUPABASE_BUCKET_FILES,
                object_path=source_path,
                mime_type=guess_mime(filepath),
                size_bytes=os.path.getsize(filepath),
                category="uploads",
                label="source_document",
                metadata={"original_filename": filename},
            )
            source_file_url = create_signed_url(supabase_client, SUPABASE_BUCKET_FILES, source_path)
        except Exception as e:
            print(f"⚠️  Supabase upload failed: {str(e)[:80]}")

    # Clear previous temp outputs at the start of a new workflow
    reset_temp_outputs()

    print(f"📥 Processing: {filename}...")

    try:
        # ========================================
        # STAGE 1: Extract from Document (module_1.py)
        # New parallel 6-stage Vertex extraction
        # Output: module_1.json (no nulls, all filled)
        # ========================================
        print("\n" + "="*70)
        print("📊 STAGE 1: RIBIF EXTRACTION (Vertex Gemini - Parallel)")
        print("="*70)
        
        # Use new process_document method (handles PDF and DOCX)
        extraction_result = extractor.process_document(filepath, OUTPUT_FOLDER)
        
        # The new extractor saves to module_1.json
        output_json_path = os.path.join(OUTPUT_FOLDER, "module_1.json")
        
        # ========================================
        # STAGE 2: Generate Machine Images (AI)
        # Generate professional product images for each machine
        # ========================================
        print("\n" + "="*70)
        print("🎨 STAGE 2: MACHINE IMAGE GENERATION (AI)")
        print("="*70)

        # Get machines from extraction result
        machines = extraction_result.get("stage_4_machines_equipements", {}).get("machines_production", [])

        if not machines:
            print("⚠️  No machines found")
            return jsonify({
                "message": "Success (no machines found)",
                "data": extraction_result,
                "project_id": project_id
            })

        print(f"📋 Found {len(machines)} machines")
        enable_images = settings.get("enableMachineImages", True)
        if not enable_images:
            print("⏭️  Image generation disabled by settings\n")

        enriched_machines = []
        image_meta_by_name: dict = {}

        for idx, machine_data in enumerate(machines, 1):
            nom_machine = machine_data.get('nom_machine', 'Unknown')
            machine_type = machine_data.get('type', 'industrial machine')
            manufacturer = machine_data.get('fabricant_recommande', '')

            print(f"[{idx}/{len(machines)}] Processing: {nom_machine}")
            print(f"           Type: {machine_type}")
            print(f"           Manufacturer: {manufacturer or 'N/A'}")

            image_result = {"image_url": None, "status": "skipped"}
            if enable_images:
                image_result = generate_machine_image(nom_machine, machine_type, manufacturer)

            image_public_url = None
            image_file_id = None
            if enable_images and image_result.get("image_path") and supabase_client and project_id:
                try:
                    local_image = image_result.get("image_path")
                    object_path = build_object_path(project_id, "machine-images", os.path.basename(local_image))
                    upload_file(
                        supabase_client,
                        SUPABASE_BUCKET_PUBLIC,
                        object_path,
                        local_image,
                        content_type="image/png",
                    )
                    image_public_url = get_public_url(supabase_client, SUPABASE_BUCKET_PUBLIC, object_path)
                    image_file_id = insert_project_file(
                        client=supabase_client,
                        project_id=project_id,
                        owner_id=user_id,
                        bucket=SUPABASE_BUCKET_PUBLIC,
                        object_path=object_path,
                        mime_type="image/png",
                        size_bytes=os.path.getsize(local_image),
                        category="machine_images",
                        label=nom_machine,
                        metadata={"source": "module1_generation"},
                    )
                except Exception as e:
                    print(f"⚠️  Supabase machine image upload failed: {str(e)[:80]}")

            if image_file_id or image_public_url:
                image_meta_by_name[nom_machine] = {
                    "image_file_id": image_file_id,
                    "image_public_url": image_public_url,
                }

            # Build enriched machine data with accurate specifications
            enriched_machine = {
                "nom_machine": nom_machine,
                "type": machine_type,
                "fabricant_recommande": manufacturer,
                "quantite_necessaire": machine_data.get('quantite_necessaire', 1),
                "use": machine_data.get('use', ''),
                "specifications": machine_data.get('specifications', {}),
                "performance": machine_data.get('performance', {}),
                "image_url": image_result.get('image_url'),
                "image_status": image_result.get('status'),
                "image_public_url": image_public_url,
                "image_file_id": image_file_id,
                "source": "vertex_extraction"
            }

            enriched_machines.append(enriched_machine)
            print()
        
        # ========================================
        # STAGE 3: Combine & Save Final Results
        # ========================================
        print("\n" + "="*70)
        print("💾 STAGE 3: SAVING COMPLETE PIPELINE RESULTS")
        print("="*70)
        
        # Add enriched machines with images to the result
        final_result = extraction_result.copy()
        final_result["enriched_machines"] = enriched_machines
        
        # Validation summary
        successful = sum(1 for m in enriched_machines if m.get('image_status') == 'success')
        final_result["scraping_summary"] = {
            "total_machines": len(machines),
            "successful_scrapes": successful,
            "failed_scrapes": len(machines) - successful
        }

        final_result.setdefault("ribif_metadata", {})
        final_result["ribif_metadata"].update({
            "project_id": project_id,
            "source_file_id": source_file_id,
            "source_file_url": source_file_url,
            "pipeline_settings": settings,
        })
        final_result["project_id"] = project_id
        
        # Save combined result
        pdf_stem = Path(filepath).stem
        output_file = os.path.join(OUTPUT_FOLDER, f"{pdf_stem}_complete_pipeline.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Complete pipeline saved: {output_file}")
        print(f"📊 Machines: {len(machines)} (images skipped)")
        
        print("\n" + "="*70)
        print("✅ MODULE 1 COMPLETE PIPELINE FINISHED")
        print("="*70)
        print("📦 Ready for RIBIF Modules 2-9")
        print("💡 Financial analysis: Module 6 (TCO) & Module 7 (Business Plan)\n")

        module1_file = write_temp_json("module1_extraction", final_result)

        module1_id = None
        if supabase_client and project_id:
            try:
                module1_id = insert_module1_extraction(
                    client=supabase_client,
                    project_id=project_id,
                    source_file_id=source_file_id,
                    data=final_result,
                )
                final_result["module1_id"] = module1_id

                machine_id_map = insert_machines_from_stage(
                    supabase_client,
                    project_id,
                    machines,
                    image_meta_by_name,
                )
                machine_assets_rows = []
                for m in enriched_machines:
                    file_id = m.get("image_file_id")
                    if not file_id:
                        continue
                    machine_name = m.get("nom_machine")
                    machine_id = machine_id_map.get(machine_name)
                    if not machine_id:
                        continue
                    machine_assets_rows.append({
                        "machine_id": machine_id,
                        "file_id": file_id,
                        "asset_type": "photo",
                        "label": machine_name,
                        "metadata": {"source": "module1_generation"},
                    })
                if machine_assets_rows:
                    supabase_client.table("machine_assets").insert(machine_assets_rows).execute()

                file_id, signed_url = upload_and_register_file(
                    supabase_client,
                    project_id,
                    user_id,
                    module1_file.get("filepath"),
                    "module_outputs",
                    label="module1_extraction",
                    bucket=SUPABASE_BUCKET_FILES,
                )
                if signed_url:
                    final_result["module1_download_url"] = signed_url
            except Exception as e:
                print(f"⚠️  Supabase module1 persistence failed: {str(e)[:80]}")

        return jsonify({"message": "Success", "data": final_result})
        
    except Exception as e:
        print(f"🔥 Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/module4/enrich', methods=['POST'])
def enrich_machines_module4():
    """
    Module 4: Enrich Machines with Suppliers
    
    Accepts module_1.json output and enriches each machine with:
    - Detailed specifications
    - Asset URLs (images, datasheets, CAD files)
    - 3-4 supplier leads per machine with pricing and customs info
    
    Input (JSON):
        Module 1 output containing stage_4_machines_equipements.machines_production
    
    Output (JSON):
        {
            "ribif_metadata": {...},
            "machines_enriched": [
                {
                    "machine_input": {...},
                    "suppliers": [...]
                }
            ]
        }
    """
    from module_4 import build_machines_enriched
    import tempfile
    
    try:
        print("\n" + "="*70)
        print("🔧 MODULE 4: MACHINE ENRICHMENT WITH SUPPLIERS")
        print("="*70)
        
        project_id = get_request_project_id(include_json=True)
        supabase_client = get_supabase()
        module1_id = None

        # Get input data
        if not request.is_json:
            return jsonify({"error": "Expected JSON input (module_1 output)"}), 400
        
        input_data = request.get_json()
        module1_id = input_data.get("module1_id") or input_data.get("ribif_metadata", {}).get("module1_id")
        
        # Validate input has required structure
        machines = input_data.get("stage_4_machines_equipements", {}).get("machines_production", [])
        if not machines:
            # Also check top-level data structure (from API response)
            if "data" in input_data:
                machines = input_data["data"].get("stage_4_machines_equipements", {}).get("machines_production", [])
                input_data = input_data["data"]
        
        if not machines:
            return jsonify({
                "error": "No machines found in input. Expected stage_4_machines_equipements.machines_production array.",
                "status": "error"
            }), 400
        
        print(f"📋 Found {len(machines)} machines to enrich\n")
        
        # Save input to temp file for module_4 processing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(input_data, f, ensure_ascii=False, indent=2)
            temp_input_path = f.name
        
        # Output path
        output_path = os.path.join(OUTPUT_FOLDER, "module_4.json")
        
        # Run module 4 enrichment
        result = build_machines_enriched(
            input_path=temp_input_path,
            output_path=output_path,
            max_workers=4,
            per_machine_timeout_s=75,
            domain_gap_s=1.5,
            llm_call_timeout_s=30,
            total_machine_budget_s=60,
            generated_images_dir=os.path.join(OUTPUT_FOLDER, "module_4_images")
        )
        
        # Cleanup temp file
        try:
            os.unlink(temp_input_path)
        except:
            pass
        
        print("\n" + "="*70)
        print("✅ MODULE 4 COMPLETE")
        print(f"📦 Enriched {len(result.get('machines_enriched', []))} machines with suppliers")
        print("="*70 + "\n")
        
        write_temp_json("module4_sourcing", result)

        if supabase_client and project_id:
            try:
                module4_id = insert_module4_sourcing(
                    client=supabase_client,
                    project_id=project_id,
                    module1_id=module1_id,
                    data=result,
                )
                result["module4_id"] = module4_id
                result["project_id"] = project_id
            except Exception as e:
                print(f"⚠️  Supabase module4 persistence failed: {str(e)[:80]}")

        return jsonify(result)
        
    except Exception as e:
        print(f"🔥 Module 4 Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route('/api/module6/tco-from-sourcing', methods=['POST'])
def calculate_tco_from_sourcing():
    """
    Module 6: Calculate TCO from Module 4 Sourcing Output
    
    Takes enriched machines from Module 4, selects the top supplier per machine
    (ranked by relevance_score), and calculates TCO for all machines.
    
    Input (JSON):
        Module 4 output with machines_enriched array
        
    Output (JSON):
        TCO calculation result with machine_tco, product_tco, etc.
    """
    from module_6 import RIBIFModule6TCO
    
    try:
        print("\n" + "="*70)
        print("📊 MODULE 6: TCO CALCULATION FROM SOURCING")
        print("="*70)
        project_id = get_request_project_id(include_json=True)
        supabase_client = get_supabase()
        module4_id = None
        
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        data = request.get_json()
        
        # Handle nested data structure
        if "data" in data:
            data = data["data"]

        module4_id = data.get("module4_id") or data.get("ribif_metadata", {}).get("module4_id")
        
        machines_enriched = data.get("machines_enriched", [])
        ribif_metadata = data.get("ribif_metadata", {})
        
        # Also get original RIBIF stages if available
        stage_1 = data.get("stage_1_informations_generales", {})
        stage_2 = data.get("stage_2_matieres_premieres", {})
        stage_3 = data.get("stage_3_produits_fabriques", {})
        stage_4 = data.get("stage_4_machines_equipements", {})
        stage_5 = data.get("stage_5_processus_production", {})
        stage_6 = data.get("stage_6_informations_complementaires", {})
        
        if not machines_enriched:
            return jsonify({"error": "No enriched machines found in input"}), 400
        
        print(f"📋 Processing {len(machines_enriched)} machines for TCO calculation\n")
        
        # Initialize TCO calculator
        tco_calculator = RIBIFModule6TCO()
        
        all_machine_tcos = []
        all_product_tcos = []
        
        for idx, machine_item in enumerate(machines_enriched, 1):
            machine_input_raw = machine_item.get("machine_input", {})
            suppliers_raw = machine_item.get("suppliers", [])
            
            # Select top supplier by relevance_score
            top_supplier = None
            if suppliers_raw:
                sorted_suppliers = sorted(
                    suppliers_raw, 
                    key=lambda x: x.get("relevance_score", 0), 
                    reverse=True
                )
                top_supplier = sorted_suppliers[0] if sorted_suppliers else None
            
            machine_name = machine_input_raw.get("nom_machine", f"Machine_{idx}")
            print(f"[{idx}/{len(machines_enriched)}] Processing: {machine_name}")
            if top_supplier:
                print(f"           Top Supplier: {top_supplier.get('supplier_name', 'N/A')} (score: {top_supplier.get('relevance_score', 0)})")
            
            # Transform to TCO input format
            tco_machine_input = {
                "id": f"machine_{idx}",
                "name": machine_name,
                "category": machine_input_raw.get("type", "Industrial Equipment"),
                "manufacturer": machine_input_raw.get("fabricant_recommande", "Unknown"),
                "base_model": machine_input_raw.get("type", ""),
                "original_specs": {
                    "capacite": machine_input_raw.get("specifications", {}).get("capacite", ""),
                    "puissance": machine_input_raw.get("specifications", {}).get("puissance", ""),
                    "dimensions": machine_input_raw.get("specifications", {}).get("dimensions", {}),
                    "poids": machine_input_raw.get("specifications", {}).get("poids", ""),
                    "alimentation": machine_input_raw.get("specifications", {}).get("alimentation", "")
                }
            }
            
            # Transform suppliers to TCO format - use only the TOP supplier by relevance_score
            tco_suppliers = []
            if top_supplier:
                tco_suppliers.append({
                    "supplier_name": top_supplier.get("supplier_name", "Unknown"),
                    "website": top_supplier.get("website", ""),
                    "region": top_supplier.get("region", "Global"),
                    "price_estimate": top_supplier.get("price_estimate"),  # Use supplier's price if available
                    "lead_time_days": None,
                    "source": top_supplier.get("source", "Module 4 Enrichment"),
                    "notes": top_supplier.get("notes", ""),
                    "relevance_score": top_supplier.get("relevance_score", 0)
                })
            
            # Calculate TCO for this machine
            machine_tco = tco_calculator.calculate_machine_tco(
                machine_input=tco_machine_input,
                suppliers=tco_suppliers,
                use_llm=True
            )
            all_machine_tcos.append(machine_tco)
            
            # Product TCO is handled later from stage_3 outputs to avoid missing inputs
        
        # Build product TCOs using stage_3 outputs (fallback heuristic)
        products = stage_3.get("produits_fabriques", [])
        if isinstance(products, dict):
            products = products.get("produits_fabriques", [])
        if products:
            from module_6 import ProductTCO
            avg_machine_annual = 0
            if all_machine_tcos:
                avg_machine_annual = sum(m.annual_tco for m in all_machine_tcos) / max(len(all_machine_tcos), 1)

            for product in products:
                nom_produit = product.get("nom_produit", "Unknown")
                categorie = product.get("categorie", "finished")

                landing_cost = avg_machine_annual * 0.05
                holding_cost = avg_machine_annual * 0.03
                quality_cost = avg_machine_annual * 0.02
                administrative_cost = avg_machine_annual * 0.01

                all_product_tcos.append(ProductTCO(
                    nom_produit=nom_produit,
                    categorie=categorie,
                    landing_cost=round(landing_cost, 2),
                    holding_cost=round(holding_cost, 2),
                    quality_cost=round(quality_cost, 2),
                    administrative_cost=round(administrative_cost, 2),
                    total_tco=round(landing_cost + holding_cost + quality_cost + administrative_cost, 2)
                ))
        else:
            print("⚠️ No stage_3 products found; product TCO skipped.")

        # Calculate raw material TCO if stage_2 data is available
        raw_material_tcos = []
        # Handle different data structures for matieres_premieres
        matieres = stage_2.get("matieres_premieres", [])
        if isinstance(matieres, dict):
            raw_materials = matieres.get("matieres_premieres", [])
        elif isinstance(matieres, list):
            raw_materials = matieres
        else:
            raw_materials = []
        
        if raw_materials:
            print(f"\n📦 Processing {len(raw_materials)} raw materials...")
            raw_material_results = tco_calculator.estimate_raw_material_costs(raw_materials, use_llm=True)
            from module_6 import RawMaterialTCO
            for rm in raw_material_results:
                raw_material_tcos.append(RawMaterialTCO(**rm))
        
        # Calculate annual breakdown
        annual_tco = tco_calculator.calculate_annual_tco(
            machine_tcos=all_machine_tcos,
            product_tcos=all_product_tcos,
            raw_material_tcos=raw_material_tcos,
            years=5
        )
        
        # Build final result
        total_machines_tco = sum(m.total_tco for m in all_machine_tcos)
        total_products_tco = sum(p.total_tco for p in all_product_tcos)
        total_raw_materials_tco = sum(r.total_tco for r in raw_material_tcos)
        total_tco = total_machines_tco + total_products_tco + total_raw_materials_tco
        
        # Get company/project info
        info_generales = stage_1.get("informations_generales", {})
        company_name = info_generales.get("nom_entreprise", ribif_metadata.get("company_name", "Unknown Company"))
        project_name = info_generales.get("nom_projet", ribif_metadata.get("project_name", "Unknown Project"))
        
        from datetime import date
        result = {
            "company_name": company_name,
            "project_name": project_name,
            "calculation_date": str(date.today()),
            "total_tco": round(total_tco, 2),
            "average_annual_tco": round(total_tco / 5, 2),
            "tco_per_unit_revenue": 0,
            "machine_tco": [m.model_dump() for m in all_machine_tcos],
            "total_machines_tco": round(total_machines_tco, 2),
            "product_tco": [p.model_dump() for p in all_product_tcos],
            "total_products_tco": round(total_products_tco, 2),
            "raw_materials_tco": [r.model_dump() for r in raw_material_tcos],
            "total_raw_materials_tco": round(total_raw_materials_tco, 2),
            "annual_tco": [a.model_dump() for a in annual_tco],
            "stage_1_informations_generales": stage_1,
            "stage_2_matieres_premieres": stage_2,
            "stage_3_produits_fabriques": stage_3,
            "stage_4_machines_equipements": stage_4,
            "stage_5_processus_production": stage_5,
            "stage_6_informations_complementaires": stage_6,
            "sourcing_metadata": ribif_metadata
        }

        if project_id:
            result["project_id"] = project_id
        
        # Save result
        output_file = os.path.join(OUTPUT_FOLDER, "module_6_tco.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*70)
        print("✅ MODULE 6 TCO COMPLETE")
        print(f"💰 Total TCO (5 years): {total_tco:,.0f} DZD")
        print(f"📊 Machines: {len(all_machine_tcos)} | Products: {len(all_product_tcos)} | Materials: {len(raw_material_tcos)}")
        print("="*70 + "\n")
        
        write_temp_json("module6_tco", result)
        if supabase_client and project_id:
            try:
                tco_run_id = insert_tco_run(
                    client=supabase_client,
                    project_id=project_id,
                    module4_id=module4_id,
                    data=result,
                )
                if tco_run_id:
                    result["tco_run_id"] = tco_run_id
                    insert_tco_details(supabase_client, tco_run_id, result)
            except Exception as e:
                print(f"⚠️  Supabase TCO persistence failed: {str(e)[:80]}")
        return jsonify(result)
        
    except Exception as e:
        print(f"🔥 TCO Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route('/api/module3/video', methods=['POST'])
def generate_video_from_images():
    """
    Module 3: Generate Video from 3 Images using Veo 2
    
    Input (multipart/form-data):
        - image1: First image file
        - image2: Second image file  
        - image3: Third image file
        - prompt1, prompt2, prompt3: Optional prompts for each video
    
    OR Input (JSON):
        - images: List of 3 base64 encoded images
        - prompts: Optional list of 3 prompts (one per video)
    
    Output (JSON):
        {
            "message": "Video generation completed",
            "video_url": "/path/to/merged_video.mp4",
            "individual_videos": [...],
            "status": "success"
        }
    """
    import time
    import tempfile
    import requests
    from vertex_utils import generate_video
    
    try:
        print("\n" + "="*70)
        print("🎬 MODULE 3: VIDEO GENERATION FROM IMAGES (Veo 2)")
        print("="*70)
        project_id = get_request_project_id(include_form=True, include_json=True)
        supabase_client = get_supabase()
        
        images_data = []  # Will store (image_bytes, prompt) tuples
        
        # Default prompts for industrial factory tour
        default_prompts = [
            "Cinematic slow pan across industrial manufacturing equipment, smooth camera movement, professional lighting, 4K quality",
            "Dramatic walkthrough of factory production line, machines operating, cinematic motion blur, professional industrial video",
            "Aerial-style view of manufacturing facility interior, sweeping camera movement, dramatic lighting, high production value"
        ]
        
        # Check for file uploads
        if 'image1' in request.files:
            prompts = []
            for i, key in enumerate(['image1', 'image2', 'image3']):
                if key in request.files:
                    file = request.files[key]
                    if file.filename:
                        img_bytes = file.read()
                        prompt = request.form.get(f'prompt{i+1}', default_prompts[i])
                        images_data.append((img_bytes, prompt))
                        print(f"📷 Received: {file.filename}")
                        if supabase_client and project_id:
                            try:
                                object_path = build_object_path(project_id, "video_inputs", file.filename)
                                upload_bytes(
                                    supabase_client,
                                    SUPABASE_BUCKET_FILES,
                                    object_path,
                                    img_bytes,
                                    content_type=file.mimetype or "image/jpeg",
                                )
                                insert_project_file(
                                    client=supabase_client,
                                    project_id=project_id,
                                    owner_id=get_request_user_id(),
                                    bucket=SUPABASE_BUCKET_FILES,
                                    object_path=object_path,
                                    mime_type=file.mimetype or "image/jpeg",
                                    size_bytes=len(img_bytes),
                                    category="video_inputs",
                                    label=key,
                                    metadata={"prompt": prompt},
                                )
                            except Exception as e:
                                print(f"⚠️  Supabase video input upload failed: {str(e)[:80]}")
        
        # Check for JSON input
        elif request.is_json:
            data = request.get_json()
            images = data.get('images', [])
            prompts = data.get('prompts', default_prompts)
            
            for i, img_input in enumerate(images[:3]):
                prompt = prompts[i] if i < len(prompts) else default_prompts[i]
                
                # Check if it's a URL
                if isinstance(img_input, str) and img_input.startswith(('http://', 'https://')):
                    print(f"📷 Downloading image {i+1} from URL...")
                    try:
                        response = requests.get(img_input, timeout=30, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        })
                        response.raise_for_status()
                        img_bytes = response.content
                        print(f"      ✅ Downloaded: {len(img_bytes)} bytes")
                    except Exception as e:
                        print(f"      ❌ Failed to download: {str(e)[:50]}")
                        continue
                # Check if it's base64
                elif isinstance(img_input, str):
                    try:
                        img_bytes = base64.b64decode(img_input)
                        print(f"📷 Decoded base64 image {i+1}: {len(img_bytes)} bytes")
                    except Exception as e:
                        print(f"      ❌ Failed to decode base64: {str(e)[:50]}")
                        continue
                else:
                    img_bytes = img_input
                
                images_data.append((img_bytes, prompt))
            
            print(f"📷 Received {len(images_data)} base64 images")
        
        if len(images_data) < 3:
            print(f"⚠️  Only {len(images_data)} images provided, need 3")
            return jsonify({
                "error": f"Need 3 images, got {len(images_data)}",
                "status": "error"
            }), 400
        
        print(f"\n✅ {len(images_data)} images received")
        
        # ========================================
        # STAGE 1: Generate individual videos
        # ========================================
        print("\n" + "-"*50)
        print("🎥 STAGE 1: Generating individual videos...")
        print("-"*50)
        
        video_uris = []
        for i, (img_bytes, prompt) in enumerate(images_data, 1):
            print(f"\n[{i}/3] Generating video...")
            print(f"      Prompt: {prompt[:60]}...")
            
            try:
                # Generate video using Veo 2
                video_uri = generate_video(
                    prompt=prompt,
                    image=img_bytes,
                    aspect_ratio="16:9",
                    duration_seconds=8
                )
                video_uris.append(video_uri)
                print(f"      ✅ Video generated: {video_uri}")
                
            except Exception as e:
                print(f"      ❌ Failed: {str(e)[:80]}")
                video_uris.append(None)
        
        # Check if we have at least one video
        valid_videos = [v for v in video_uris if v is not None]
        if not valid_videos:
            return jsonify({
                "error": "All video generations failed",
                "status": "error"
            }), 500
        
        # ========================================
        # STAGE 2: Download videos from GCS
        # ========================================
        print("\n" + "-"*50)
        print("📥 STAGE 2: Downloading videos from GCS...")
        print("-"*50)
        
        VIDEO_OUTPUT_DIR = 'data/videos'
        os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
        
        # Get API key for authenticated downloads
        video_api_key = os.getenv("GOOGLE_API_KEY", "")
        
        downloaded_paths = []
        for i, uri in enumerate(valid_videos, 1):
            if uri:
                try:
                    # GCS URI format: gs://bucket/path/to/video.mp4
                    # For authenticated access, we need to use the GCS client or signed URLs
                    # The Veo API should return accessible URLs
                    
                    local_path = os.path.join(VIDEO_OUTPUT_DIR, f"video_{i}_{int(time.time())}.mp4")
                    
                    # If it's a GCS URI, convert to HTTP URL for download
                    if uri.startswith("gs://"):
                        # Use google cloud storage client to download
                        from google.cloud import storage
                        
                        # Parse GCS URI
                        parts = uri.replace("gs://", "").split("/", 1)
                        bucket_name = parts[0]
                        blob_name = parts[1] if len(parts) > 1 else ""
                        
                        storage_client = storage.Client()
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(blob_name)
                        blob.download_to_filename(local_path)
                    
                    # Google API URLs require API key
                    elif "generativelanguage.googleapis.com" in uri:
                        # Append API key if not already present
                        if "key=" not in uri:
                            separator = "&" if "?" in uri else "?"
                            download_url = f"{uri}{separator}key={video_api_key}"
                        else:
                            download_url = uri
                        
                        print(f"      🔑 Using authenticated download for video {i}")
                        response = requests.get(download_url, stream=True)
                        response.raise_for_status()
                        with open(local_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                    else:
                        # Direct HTTP URL - download with requests
                        response = requests.get(uri, stream=True)
                        response.raise_for_status()
                        with open(local_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    downloaded_paths.append(local_path)
                    print(f"      ✅ Downloaded: {local_path}")
                    
                except Exception as e:
                    print(f"      ❌ Download failed for video {i}: {str(e)[:60]}")
        
        if not downloaded_paths:
            return jsonify({
                "error": "Failed to download any videos",
                "video_uris": video_uris,
                "status": "partial_error"
            }), 500
        
        # ========================================
        # STAGE 3: Merge videos with moviepy
        # ========================================
        print("\n" + "-"*50)
        print("🔗 STAGE 3: Merging videos...")
        print("-"*50)
        
        merged_path = os.path.join(VIDEO_OUTPUT_DIR, f"merged_factory_tour_{int(time.time())}.mp4")
        
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
            
            clips = []
            for path in downloaded_paths:
                clip = VideoFileClip(path)
                clips.append(clip)
            
            # Concatenate all clips
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Write the merged video
            final_clip.write_videofile(
                merged_path,
                codec='libx264',
                audio_codec='aac',
                fps=24,
                verbose=False,
                logger=None
            )
            
            # Close all clips to free resources
            for clip in clips:
                clip.close()
            final_clip.close()
            
            print(f"      ✅ Merged video: {merged_path}")
            
        except ImportError:
            print("      ⚠️  moviepy not installed, returning individual videos")
            merged_path = downloaded_paths[0]  # Return first video as fallback
        except Exception as e:
            print(f"      ❌ Merge failed: {str(e)[:60]}")
            merged_path = downloaded_paths[0]  # Return first video as fallback
        
        # Calculate total duration
        total_duration = len(downloaded_paths) * 5  # Each video is ~5 seconds
        
        result = {
            "message": "Video generation completed",
            "video_url": merged_path,
            "individual_videos": video_uris,
            "downloaded_videos": downloaded_paths,
            "duration_seconds": total_duration,
            "status": "success"
        }

        if supabase_client and project_id:
            try:
                file_id, signed_url = upload_and_register_file(
                    supabase_client,
                    project_id,
                    get_request_user_id(),
                    merged_path,
                    "videos",
                    label=os.path.basename(merged_path),
                    bucket=SUPABASE_BUCKET_FILES,
                )
                if signed_url:
                    result["video_url"] = signed_url
                result["file_id"] = file_id
                insert_video(
                    client=supabase_client,
                    project_id=project_id,
                    file_id=file_id,
                    data=result,
                )
            except Exception as e:
                print(f"⚠️  Supabase video persistence failed: {str(e)[:80]}")
        
        print("\n" + "="*70)
        print("✅ MODULE 3 COMPLETE")
        print(f"🎬 Final video: {merged_path}")
        print(f"⏱️  Duration: ~{total_duration} seconds")
        print("="*70 + "\n")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"🔥 Video Generation Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route('/api/module6/tco', methods=['POST'])
def calculate_tco():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Check required fields
        if 'machine_input' not in data:
            return jsonify({"error": "Missing required field: machine_input"}), 400
        
        # Initialize TCO calculator and process
        from module_6 import RIBIFModule6TCO
        tco_calculator = RIBIFModule6TCO()
        result = tco_calculator.process_input(data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({"message": "TCO calculated successfully", "data": result})
    
    except Exception as e:
        print(f"🔥 TCO Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/module7/business-plan', methods=['POST'])
def generate_business_plan():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        project_id = data.get("project_id") or data.get("ribif_metadata", {}).get("project_id")
        tco_run_id = data.get("tco_run_id")
        supabase_client = get_supabase()
        
        # Initialize business plan generator
        from module_7_business_model import RIBIFModule7BusinessPlan, BusinessPlanInput
        
        # Create input from TCO output structure
        bp_input = BusinessPlanInput(
            project_name=data.get("project_name", data.get("stage_1_informations_generales", {}).get("informations_generales", {}).get("nom_projet", "Untitled Project")),
            company_name=data.get("company_name", data.get("stage_1_informations_generales", {}).get("informations_generales", {}).get("nom_entreprise", "RIBIF Industries")),
            total_tco=data.get("total_tco", 0),
            average_annual_tco=data.get("average_annual_tco", 0),
            total_machines_tco=data.get("total_machines_tco", 0),
            total_products_tco=data.get("total_products_tco", 0),
            total_raw_materials_tco=data.get("total_raw_materials_tco", 0),
            machine_tco=data.get("machine_tco", []),
            product_tco=data.get("product_tco", []),
            raw_materials_tco=data.get("raw_materials_tco", []),
            annual_tco=data.get("annual_tco", []),
            stage_1_informations_generales=data.get("stage_1_informations_generales"),
            stage_2_matieres_premieres=data.get("stage_2_matieres_premieres"),
            stage_3_produits_fabriques=data.get("stage_3_produits_fabriques"),
            stage_6_informations_complementaires=data.get("stage_6_informations_complementaires")
        )
        
        generator = RIBIFModule7BusinessPlan()
        result = generator.generate_business_plan(bp_input)
        
        data_payload = result.model_dump()
        write_temp_json("module7_business_plan", data_payload)

        file_id = None
        download_url = result.download_url
        if supabase_client and project_id:
            try:
                file_id, signed_url = upload_and_register_file(
                    supabase_client,
                    project_id,
                    get_request_user_id(),
                    result.filepath,
                    "business_plans",
                    label=result.filename,
                    bucket=SUPABASE_BUCKET_FILES,
                )
                if signed_url:
                    download_url = signed_url
                insert_business_plan(
                    client=supabase_client,
                    project_id=project_id,
                    tco_run_id=tco_run_id,
                    file_id=file_id,
                    filename=result.filename,
                    data=data_payload,
                )
            except Exception as e:
                print(f"⚠️  Supabase business plan persistence failed: {str(e)[:80]}")

        return jsonify({
            "message": "Business plan generated successfully",
            "filepath": result.filepath,
            "filename": result.filename,
            "download_url": download_url,
            "file_id": file_id,
            "data": data_payload,
            "project_id": project_id
        })
    
    except Exception as e:
        print(f"🔥 Business Plan Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/module7/pitch-deck', methods=['POST'])
def generate_pitch_deck():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        project_id = data.get("project_id") or data.get("ribif_metadata", {}).get("project_id")
        tco_run_id = data.get("tco_run_id")
        supabase_client = get_supabase()
        
        # Initialize pitch deck generator
        from module_7_pitch_deck import RIBIFModule8PitchDeck, PitchDeckInput
        
        # Create input from TCO output structure (same as module 7)
        pd_input = PitchDeckInput(
            project_name=data.get("project_name", data.get("stage_1_informations_generales", {}).get("informations_generales", {}).get("nom_projet", "Untitled Project")),
            company_name=data.get("company_name", data.get("stage_1_informations_generales", {}).get("informations_generales", {}).get("nom_entreprise", "RIBIF Industries")),
            total_tco=data.get("total_tco", 0),
            average_annual_tco=data.get("average_annual_tco", 0),
            total_machines_tco=data.get("total_machines_tco", 0),
            total_products_tco=data.get("total_products_tco", 0),
            total_raw_materials_tco=data.get("total_raw_materials_tco", 0),
            machine_tco=data.get("machine_tco", []),
            product_tco=data.get("product_tco", []),
            raw_materials_tco=data.get("raw_materials_tco", []),
            annual_tco=data.get("annual_tco", []),
            stage_1_informations_generales=data.get("stage_1_informations_generales"),
            stage_2_matieres_premieres=data.get("stage_2_matieres_premieres"),
            stage_3_produits_fabriques=data.get("stage_3_produits_fabriques"),
            stage_4_machines_equipements=data.get("stage_4_machines_equipements"),
            stage_5_processus_production=data.get("stage_5_processus_production"),
            stage_6_informations_complementaires=data.get("stage_6_informations_complementaires"),
            presenter_name=data.get("presenter_name", ""),
            presenter_title=data.get("presenter_title", "")
        )
        
        generator = RIBIFModule8PitchDeck()
        result = generator.generate_pitch_deck(pd_input)

        data_payload = result.model_dump()
        write_temp_json("module7_pitch_deck", data_payload)

        file_id = None
        download_url = result.download_url
        pdf_download_url = result.pdf_download_url
        if supabase_client and project_id:
            try:
                source_path = result.pdf_filepath or result.filepath
                if source_path:
                    file_id, signed_url = upload_and_register_file(
                        supabase_client,
                        project_id,
                        get_request_user_id(),
                        source_path,
                        "pitch_decks",
                        label=result.pdf_filename or result.filename,
                        bucket=SUPABASE_BUCKET_FILES,
                    )
                    if signed_url:
                        download_url = signed_url
                        pdf_download_url = signed_url
                insert_pitch_deck(
                    client=supabase_client,
                    project_id=project_id,
                    tco_run_id=tco_run_id,
                    file_id=file_id,
                    presentation_id=result.presentation_id,
                    edit_url=result.edit_url,
                    data=data_payload,
                )
            except Exception as e:
                print(f"⚠️  Supabase pitch deck persistence failed: {str(e)[:80]}")

        response_payload = {
            "message": "Pitch deck generated successfully",
            "filepath": result.filepath,
            "filename": result.filename,
            "download_url": download_url,
            "pdf_filepath": result.pdf_filepath,
            "pdf_filename": result.pdf_filename,
            "pdf_download_url": pdf_download_url,
            "file_id": file_id,
            "data": data_payload,
            "project_id": project_id
        }

        # Cleanup temp outputs after workflow finishes
        cleanup_temp_outputs()
        cleanup_temp_images()

        return jsonify(response_payload)
    
    except ConnectionError as e:
        print(f"🔥 Presenton Connection Error: {e}")
        return jsonify({"error": str(e)}), 503
    except TimeoutError as e:
        print(f"🔥 Presenton Timeout: {e}")
        return jsonify({"error": str(e)}), 504
    except Exception as e:
        print(f"🔥 Pitch Deck Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/module9/catalog', methods=['POST'])
def generate_catalog_module9():
    """
    Module 9: Industrial Technical Catalog (PDF + HTML)

    Input (JSON):
    {
        "module1_data": { ... },
        "module4_data": { ... },
        "images_config": { ... },
        "output_format": "pdf" | "html" | "both",
        "output_dir": "data/catalogs",
        "base_filename": "optional_base_name",
        "image_base_path": "data"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        payload = data
        if "module1_data" not in payload:
            payload = {"module1_data": data}

        project_id = payload.get("project_id") or payload.get("module1_data", {}).get("project_id")
        module1_id = payload.get("module1_id") or payload.get("module1_data", {}).get("module1_id")
        supabase_client = get_supabase()

        from module_9 import RIBIFModule9Catalog, CatalogInput

        catalog_input = CatalogInput(**payload)
        generator = RIBIFModule9Catalog(image_base_path=catalog_input.image_base_path)
        result = generator.generate_catalog(catalog_input, base_url=BASE_URL)

        data_payload = result.model_dump()
        write_temp_json("module9_catalog", data_payload)

        pdf_file_id = None
        html_file_id = None
        if supabase_client and project_id:
            try:
                if result.pdf_filepath:
                    pdf_file_id, pdf_url = upload_and_register_file(
                        supabase_client,
                        project_id,
                        get_request_user_id(),
                        result.pdf_filepath,
                        "catalogs",
                        label=result.pdf_filename,
                        bucket=SUPABASE_BUCKET_FILES,
                    )
                    if pdf_url:
                        data_payload["pdf_download_url"] = pdf_url
                if result.html_filepath:
                    html_file_id, html_url = upload_and_register_file(
                        supabase_client,
                        project_id,
                        get_request_user_id(),
                        result.html_filepath,
                        "catalogs",
                        label=result.html_filename,
                        bucket=SUPABASE_BUCKET_FILES,
                    )
                    if html_url:
                        data_payload["html_download_url"] = html_url

                insert_catalog(
                    client=supabase_client,
                    project_id=project_id,
                    module1_id=module1_id,
                    pdf_file_id=pdf_file_id,
                    html_file_id=html_file_id,
                    data=data_payload,
                )
            except Exception as e:
                print(f"⚠️  Supabase catalog persistence failed: {str(e)[:80]}")

        return jsonify({
            "message": "Catalog generated successfully",
            "data": data_payload,
            "project_id": project_id,
            "pdf_file_id": pdf_file_id,
            "html_file_id": html_file_id
        })

    except Exception as e:
        print(f"🔥 Module 9 Catalog Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/module2/layout', methods=['POST'])
def generate_layout():
    """
    Module 2: Factory Layout Generation (Placeholder)
    
    Input (JSON):
    {
        "product": {
            "name": "PET Bottled Water (0.5L)",
            "output_unit": "bottles",
            "target_output_per_hour": 12000
        },
        "machines": [
            {
                "name": "Blow Molder (PET Bottle)",
                "model": "BM-12000-2C",
                "count": 1,
                "use": "Blows PET preforms into 0.5L bottles",
                "image": "https://example.com/machine.jpg",
                "width": 6.2,   // meters
                "height": 2.6  // meters
            },
            ...
        ]
    }
    
    Output (JSON):
    {
        "message": "Layout generated successfully",
        "data": {
            "layout_2d": "/path/to/layout.png",
            "layout_3d": "/path/to/factory_model.glb"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        project_id = get_request_project_id(include_json=True)
        supabase_client = get_supabase()
        
        # Extract product info and machines
        product = data.get('product', {})
        machines = data.get('machines', [])
        
        if not machines:
            return jsonify({"error": "Missing required field: machines"}), 400
        
        print(f"\n" + "="*70)
        print("🏭 MODULE 2: FACTORY LAYOUT GENERATION (Placeholder)")
        print("="*70)
        
        # Log product info
        if product:
            print(f"📦 Product: {product.get('name', 'Unknown')}")
            print(f"📊 Target Output: {product.get('target_output_per_hour', 0)} {product.get('output_unit', 'units')}/hour")
        
        print(f"📋 Received {len(machines)} machine types:")
        for i, m in enumerate(machines, 1):
            print(f"   {i}. {m.get('name', 'Unknown')} ({m.get('model', 'N/A')}) x{m.get('count', 1)}")
            print(f"      Size: {m.get('width', 0)}m x {m.get('height', 0)}m")
        
        # Calculate total machine instances
        total_instances = sum(m.get('count', 1) for m in machines)
        print(f"\n🔢 Total machine instances: {total_instances}")
        
        # Auto-generate sequential flows based on machine order (production line flow)
        auto_flows = []
        for i in range(len(machines) - 1):
            auto_flows.append({
                "from": machines[i].get('model', machines[i].get('name')),
                "to": machines[i+1].get('model', machines[i+1].get('name'))
            })
        print(f"🔗 Auto-generated {len(auto_flows)} production flows (sequential)")
        
        # Placeholder response - only return the 2 essential files
        output_dir = os.path.join(os.path.dirname(__file__), 'mohaned', 'output')
        
        result = {
            "layout_2d": os.path.join(output_dir, "layout_square.png"),
            "layout_3d": os.path.join(output_dir, "factory_model.glb")
        }
        
        print(f"\n✅ Layout generation complete (placeholder)")
        print(f"📐 2D Layout: {result['layout_2d']}")
        print(f"🎮 3D Model: {result['layout_3d']}")
        
        if supabase_client and project_id:
            try:
                layout_2d_id = None
                layout_3d_id = None
                if os.path.exists(result["layout_2d"]):
                    layout_2d_id, layout_2d_url = upload_and_register_file(
                        supabase_client,
                        project_id,
                        get_request_user_id(),
                        result["layout_2d"],
                        "layouts",
                        label="layout_2d",
                        bucket=SUPABASE_BUCKET_FILES,
                    )
                    if layout_2d_url:
                        result["layout_2d_url"] = layout_2d_url
                if os.path.exists(result["layout_3d"]):
                    layout_3d_id, layout_3d_url = upload_and_register_file(
                        supabase_client,
                        project_id,
                        get_request_user_id(),
                        result["layout_3d"],
                        "layouts",
                        label="layout_3d",
                        bucket=SUPABASE_BUCKET_FILES,
                    )
                    if layout_3d_url:
                        result["layout_3d_url"] = layout_3d_url

                insert_layout(
                    client=supabase_client,
                    project_id=project_id,
                    pipeline_id=None,
                    layout_2d_file_id=layout_2d_id,
                    layout_3d_file_id=layout_3d_id,
                    data=result,
                )
            except Exception as e:
                print(f"⚠️  Supabase layout persistence failed: {str(e)[:80]}")

        return jsonify(result)
    
    except Exception as e:
        print(f"🔥 Layout Generation Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Disable Flask's auto-reloader / file watcher to stop watching for changes (e.g. "#file:app.py")
    app.run(debug=True, port=5000, use_reloader=False)
