from pathlib import Path
from flask import Blueprint, jsonify, request

from config import BASE_URL, OUTPUT_DIRS, SKIP_MODULE_7, SKIP_MODULE_8
from supabase_utils import get_supabase, insert_business_plan, insert_pitch_deck
from utils.module_7.business_plan import RIBIFModule7BusinessPlan, BusinessPlanInput
from utils.module_7.pitch_deck import RIBIFModule8PitchDeck, PitchDeckInput
from utils.app_helpers import get_request_user_id, load_template_payload, upload_and_register_file
from utils.logger import log_skip

bp_module7 = Blueprint("module7", __name__)


@bp_module7.route("/api/module7/business-plan", methods=["POST"])
def generate_business_plan():
    try:
        if SKIP_MODULE_7:
            log_skip("module7.generate_business_plan", reason="SKIP_MODULE_7")
            payload = load_template_payload("module7_business_plan") or {}
            project_id = request.get_json(silent=True) or {}
            pid = project_id.get("project_id") or project_id.get("ribif_metadata", {}).get("project_id")
            if isinstance(payload, dict) and pid:
                payload["project_id"] = payload.get("project_id") or pid
            return jsonify(payload)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        project_id = data.get("project_id") or data.get("ribif_metadata", {}).get("project_id")
        tco_run_id = data.get("tco_run_id")

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
            stage_6_informations_complementaires=data.get("stage_6_informations_complementaires"),
        )

        generator = RIBIFModule7BusinessPlan()
        result = generator.generate_business_plan(bp_input, output_dir=str(OUTPUT_DIRS["module7"]), base_url=BASE_URL)

        data_payload = result.model_dump()
        file_id = None
        download_url = result.download_url

        response_payload = {
            "message": "Business plan generated successfully",
            "filepath": result.filepath,
            "filename": result.filename,
            "download_url": download_url,
            "file_id": file_id,
            "data": data_payload,
            "project_id": project_id,
        }

        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                file_path = Path(result.filepath)
                if file_path.exists():
                    file_id, file_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(file_path),
                        category="business-plan",
                        label=result.filename,
                    )
                    response_payload["file_id"] = file_id
                    response_payload["download_url"] = file_url or download_url
                insert_business_plan(
                    client=client,
                    project_id=project_id,
                    tco_run_id=tco_run_id,
                    file_id=response_payload.get("file_id"),
                    filename=result.filename,
                    data=data_payload,
                )
            except Exception:
                pass

        return jsonify(response_payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_module7.route("/api/module7/pitch-deck", methods=["POST"])
def generate_pitch_deck():
    try:
        if SKIP_MODULE_8:
            log_skip("module7.generate_pitch_deck", reason="SKIP_MODULE_8")
            payload = load_template_payload("module7_pitch_deck") or {}
            project_id = request.get_json(silent=True) or {}
            pid = project_id.get("project_id") or project_id.get("ribif_metadata", {}).get("project_id")
            if isinstance(payload, dict) and pid:
                payload["project_id"] = payload.get("project_id") or pid
            return jsonify(payload)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        project_id = data.get("project_id") or data.get("ribif_metadata", {}).get("project_id")
        tco_run_id = data.get("tco_run_id")

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
            presenter_title=data.get("presenter_title", ""),
        )

        generator = RIBIFModule8PitchDeck()
        result = generator.generate_pitch_deck(pd_input, output_dir=str(OUTPUT_DIRS["module7"]), base_url=BASE_URL)

        data_payload = result.model_dump()
        file_id = None
        download_url = result.download_url
        pdf_download_url = result.pdf_download_url

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
            "project_id": project_id,
        }

        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                file_path = Path(result.filepath)
                pdf_path = Path(result.pdf_filepath) if result.pdf_filepath else None
                if file_path.exists():
                    file_id, file_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(file_path),
                        category="pitch-deck",
                        label=result.filename,
                    )
                    response_payload["file_id"] = file_id
                    response_payload["download_url"] = file_url or download_url
                if pdf_path and pdf_path.exists():
                    _, pdf_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(pdf_path),
                        category="pitch-deck-pdf",
                        label=result.pdf_filename,
                    )
                    response_payload["pdf_download_url"] = pdf_url or pdf_download_url
                insert_pitch_deck(
                    client=client,
                    project_id=project_id,
                    tco_run_id=tco_run_id,
                    file_id=response_payload.get("file_id"),
                    presentation_id=None,
                    edit_url=None,
                    data=data_payload,
                )
            except Exception:
                pass

        return jsonify(response_payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
