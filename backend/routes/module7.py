from flask import Blueprint, jsonify, request

from config import BASE_URL, OUTPUT_DIRS
from utils.module_7.business_plan import RIBIFModule7BusinessPlan, BusinessPlanInput
from utils.module_7.pitch_deck import RIBIFModule8PitchDeck, PitchDeckInput

bp_module7 = Blueprint("module7", __name__)


@bp_module7.route("/api/module7/business-plan", methods=["POST"])
def generate_business_plan():
    try:
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

        return jsonify({
            "message": "Business plan generated successfully",
            "filepath": result.filepath,
            "filename": result.filename,
            "download_url": download_url,
            "file_id": file_id,
            "data": data_payload,
            "project_id": project_id,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_module7.route("/api/module7/pitch-deck", methods=["POST"])
def generate_pitch_deck():
    try:
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

        return jsonify({
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
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
